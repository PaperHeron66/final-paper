# -*- coding: utf-8 -*-
"""02 数据清洗与治理：去重、缺失、异常、类型统一、指标派生、星型模型整合与导出。

清洗顺序遵循"先结构后数值、先剔除后补全"的原则，每一步都记录行数变化，
最终形成 data/clean 下的 CSV / JSON / SQLite 三种可复用格式。
"""
import json
import sqlite3

import numpy as np
import pandas as pd

from config import RAW, CLEAN, TABS, SEED

# 运费、折扣、银行费用等非商品交易码（人工核对官方数据字典后整理）
NON_PRODUCT = {
    "POST", "D", "M", "DOT", "C2", "CRUK", "BANK CHARGES", "AMAZONFEE",
    "S", "B", "PADS", "TEST001", "TEST002", "GIFT", "SP1002", "DCGS0076",
    "DCGS0003", "DCGSSBOY", "DCGSSGIRL", "BANK_CHARGES",
}

EUROPE = {
    "Austria", "Belgium", "Switzerland", "Cyprus", "Czech Republic", "Germany",
    "Denmark", "Spain", "Finland", "France", "Greece", "Hungary", "Ireland",
    "Italy", "Lithuania", "Luxembourg", "Latvia", "Malta", "Netherlands",
    "Norway", "Poland", "Portugal", "Romania", "Sweden", "Slovakia", "Slovenia",
    "Iceland", "Estonia", "Bulgaria", "Croatia", "Serbia", "Ukraine",
}

LOG = []


def step(name, df, removed, note):
    LOG.append({
        "清洗步骤": name,
        "删除行数": int(removed),
        "剩余行数": int(len(df)),
        "说明": note,
    })
    print(f"[clean] {name:<18} -{removed:>7,} 行 -> 剩余 {len(df):>9,} 行  {note}")


def main():
    df = pd.read_pickle(RAW / "raw_all.pkl")
    n0 = len(df)
    print(f"[clean] 载入原始数据 {n0:,} 行")

    # 1. 类型统一：编码类字段一律按字符串，金额按浮点，数量按整型
    for c in ("Invoice", "StockCode", "Country"):
        df[c] = df[c].astype(str).str.strip()
    df["Invoice"] = df["Invoice"].str.upper()
    df["Description"] = df["Description"].astype("string").str.strip()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce").astype("Int64")
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")

    # 2. 重复值：完全相同的行优先保留首条
    before = len(df)
    df = df.drop_duplicates(subset=[c for c in df.columns if c != "SourceSheet"], keep="first")
    step("去除完全重复行", df, before - len(df), "同一发票同一商品重复录入")

    # 3. 关键字段不可解析
    before = len(df)
    df = df.dropna(subset=["Quantity", "Price", "InvoiceDate"])
    step("剔除关键字段缺失", df, before - len(df), "数量/单价/日期无法解析")

    # 4. 非商品交易行（运费、银行费用、手工调整码）
    before = len(df)
    mask_bad = df["StockCode"].str.upper().isin(NON_PRODUCT) | df["StockCode"].str.fullmatch(r"[A-Z]{2,}")
    df = df[~mask_bad]
    step("剔除非商品交易码", df, before - len(df), "POST/BANK CHARGES 等非商品行")

    # 5. 价格异常：单价 ≤0（赠品、系统调整）不计入销售口径
    before = len(df)
    df = df[df["Price"] > 0]
    step("剔除单价≤0记录", df, before - len(df), "零价/负价行无法计算销售额")

    # 6. 退货与取消：发票号以 C 开头或数量为负 —— 单独成表，不删除
    df["IsReturn"] = df["Invoice"].str.startswith("C") | (df["Quantity"] < 0)
    returns = df[df["IsReturn"]].copy()
    sales = df[~df["IsReturn"]].copy()
    step("拆分退货与取消单", sales, len(returns), f"退货/取消 {len(returns):,} 行转入 returns 表")

    # 7. 数量异常：IQR 三倍上界识别极端批发/录入错误
    q1, q3 = sales["Quantity"].quantile([0.25, 0.75])
    upper = q3 + 3 * (q3 - q1)
    before = len(sales)
    outliers = sales[sales["Quantity"] > upper].copy()
    sales = sales[sales["Quantity"] <= upper]
    step("剔除数量极端值", sales, before - len(sales), f"IQR×3 上界 {upper:.0f} 件，剔除 {len(outliers):,} 行")

    # 8. 销售额派生
    for d in (sales, returns):
        d["Amount"] = (d["Quantity"] * d["Price"]).round(2)
    sales = sales[sales["Amount"] > 0]
    step("剔除零金额行", sales, before - len(sales) - len(outliers), "派生销售额为 0 的行")

    # 9. 日期维度派生
    def enrich(d):
        d = d.copy()
        d["Date"] = d["InvoiceDate"].dt.normalize()
        d["Year"] = d["InvoiceDate"].dt.year
        d["Month"] = d["InvoiceDate"].dt.month
        d["YM"] = d["InvoiceDate"].dt.to_period("M").astype(str)
        d["Quarter"] = d["InvoiceDate"].dt.quarter
        d["DOW"] = d["InvoiceDate"].dt.dayofweek  # 0=周一
        d["Hour"] = d["InvoiceDate"].dt.hour
        d["IsWeekend"] = d["DOW"] >= 5
        d["LineNo"] = d.groupby("Invoice").cumcount() + 1
        return d

    sales = enrich(sales)
    returns = enrich(returns)

    # 10. 星型模型：维度表 + 事实表
    dim_country = (
        sales.groupby("Country", as_index=False)
        .agg(订单数=("Invoice", "nunique"), 客户数=("CustomerID", "nunique"), 销售额=("Amount", "sum"))
    )
    dim_country["Region"] = np.where(
        dim_country["Country"] == "United Kingdom", "英国本土",
        np.where(dim_country["Country"].isin(EUROPE), "欧洲大陆", "其他地区"),
    )
    dim_country = dim_country.rename(columns={"Country": "CountryKey"})

    dim_date = (
        sales.groupby("Date", as_index=False)
        .agg(销售额=("Amount", "sum"), 订单数=("Invoice", "nunique"), 件数=("Quantity", "sum"))
    )
    dim_date["Year"] = dim_date["Date"].dt.year
    dim_date["Month"] = dim_date["Date"].dt.month
    dim_date["YM"] = dim_date["Date"].dt.to_period("M").astype(str)
    dim_date["DOW"] = dim_date["Date"].dt.dayofweek
    dim_date["IsWeekend"] = dim_date["DOW"] >= 5

    dim_product = (
        sales.groupby("StockCode", as_index=False)
        .agg(
            商品名称=("Description", lambda s: s.dropna().mode().iloc[0] if s.notna().any() else ""),
            销量=("Quantity", "sum"),
            销售额=("Amount", "sum"),
            订单数=("Invoice", "nunique"),
            首售日期=("Date", "min"),
            末售日期=("Date", "max"),
        )
    )

    dim_customer = (
        sales.dropna(subset=["CustomerID"])
        .groupby("CustomerID", as_index=False)
        .agg(
            最近购买日=("Date", "max"),
            首次购买日=("Date", "min"),
            订单数=("Invoice", "nunique"),
            购买件数=("Quantity", "sum"),
            累计销售额=("Amount", "sum"),
            国家=("Country", lambda s: s.mode().iloc[0] if len(s.mode()) else ""),
        )
    )
    snapshot = sales["Date"].max()
    dim_customer["R天数"] = (snapshot - dim_customer["最近购买日"]).dt.days
    dim_customer["F订单数"] = dim_customer["订单数"]
    dim_customer["M金额"] = dim_customer["累计销售额"]

    fact = sales[[
        "Invoice", "LineNo", "Date", "Year", "Month", "YM", "DOW", "Hour", "IsWeekend",
        "StockCode", "CustomerID", "Country", "Quantity", "Price", "Amount", "SourceSheet",
    ]].rename(columns={"Date": "DateKey", "StockCode": "ProductKey",
                       "CustomerID": "CustomerKey", "Country": "CountryKey"})

    # 11. 主外键完整性校验
    fk = []
    checks = [
        ("fact_sales.ProductKey -> dim_product.StockCode", fact["ProductKey"], set(dim_product["StockCode"])),
        ("fact_sales.CountryKey -> dim_country.CountryKey", fact["CountryKey"], set(dim_country["CountryKey"])),
        ("fact_sales.DateKey -> dim_date.Date", fact["DateKey"], set(dim_date["Date"])),
        ("dim_customer.国家 -> dim_country.CountryKey", dim_customer["国家"], set(dim_country["CountryKey"])),
    ]
    for name, series, universe in checks:
        orphan = int((~series.isin(universe)).sum())
        fk.append({"外键关系": name, "孤立键数量": orphan, "结论": "通过" if orphan == 0 else "存在孤立键"})
    fk.append({
        "外键关系": "fact_sales.CustomerKey -> dim_customer.CustomerID",
        "孤立键数量": int(fact["CustomerKey"].notna().sum() - fact["CustomerKey"].dropna().isin(set(dim_customer["CustomerID"])).sum()),
        "结论": "匿名交易（CustomerID 缺失）不参与客户级分析，已在事实表中标记",
    })
    pd.DataFrame(fk).to_csv(TABS / "t04_fk_check.csv", index=False, encoding="utf-8-sig")
    print("[clean] 外键校验：", {r["外键关系"][:24]: r["孤立键数量"] for r in fk})

    # 12. 导出 CSV / JSON / SQLite
    fact.to_csv(CLEAN / "fact_sales.csv", index=False, encoding="utf-8-sig")
    for name, d in (("dim_customer", dim_customer), ("dim_product", dim_product),
                    ("dim_date", dim_date), ("dim_country", dim_country)):
        d.to_csv(CLEAN / f"{name}.csv", index=False, encoding="utf-8-sig")
    returns.drop(columns=["SourceSheet"]).to_csv(CLEAN / "returns.csv", index=False, encoding="utf-8-sig")

    db = CLEAN / "retail.db"
    if db.exists():
        db.unlink()
    with sqlite3.connect(db) as con:
        fact.to_sql("fact_sales", con, index=False)
        dim_customer.to_sql("dim_customer", con, index=False)
        dim_product.to_sql("dim_product", con, index=False)
        dim_date.to_sql("dim_date", con, index=False)
        dim_country.to_sql("dim_country", con, index=False)
        con.execute("CREATE INDEX idx_fact_cust ON fact_sales(CustomerKey)")
        con.execute("CREATE INDEX idx_fact_date ON fact_sales(DateKey)")

    meta = {
        "随机种子": SEED,
        "抽样说明": "全量数据参与计算，未对事实表抽样；仅在客户气泡图等展示环节按固定种子抽取样本，"
                    f"随机种子 seed={SEED}，保证图表可复现。",
        "事实表记录数": int(len(fact)),
        "退货表记录数": int(len(returns)),
        "客户维度记录数": int(len(dim_customer)),
        "商品维度记录数": int(len(dim_product)),
        "日期维度记录数": int(len(dim_date)),
        "国家维度记录数": int(len(dim_country)),
        "数据快照日": str(snapshot.date()),
        "时间跨度": f"{fact['DateKey'].min().date()} 至 {fact['DateKey'].max().date()}",
        "订单数": int(fact["Invoice"].nunique()),
        "匿名交易行数": int(fact["CustomerKey"].isna().sum()),
        "匿名交易占比": round(float(fact["CustomerKey"].isna().mean()), 4),
    }
    (CLEAN / "schema.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.DataFrame(LOG).to_csv(TABS / "t02_clean_log.csv", index=False, encoding="utf-8-sig")
    print(f"[clean] 导出完成：{CLEAN}")
    print(f"[clean] 事实表 {len(fact):,} 行 | 订单 {meta['订单数']:,} | 客户 {len(dim_customer):,} | 商品 {len(dim_product):,}")

    # 供后续脚本复用
    sales.to_pickle(CLEAN / "sales.pkl")
    returns.to_pickle(CLEAN / "returns.pkl")


if __name__ == "__main__":
    main()
