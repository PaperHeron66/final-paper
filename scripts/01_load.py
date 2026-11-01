# -*- coding: utf-8 -*-
"""01 数据加载：解压官方下载文件 -> 读取两张年度工作表 -> 规范化字段名。

获取方式（白名单）：UCI Machine Learning Repository 官方 ZIP 一次性下载，
https://archive.ics.uci.edu/dataset/502/online+retail+ii 。全程无网页抓取。
"""
import json
import zipfile

import pandas as pd

from config import RAW, TABS, DS_NAME, DS_URL

# 官方文件中的字段名 -> 项目统一字段名
COLMAP = {
    "invoice": "Invoice",
    "stockcode": "StockCode",
    "description": "Description",
    "quantity": "Quantity",
    "invoicedate": "InvoiceDate",
    "price": "Price",
    "customer id": "CustomerID",
    "customerid": "CustomerID",
    "country": "Country",
}


def locate_source():
    """返回官方 Excel 路径；若只有 ZIP 则先解压。"""
    xlsx = sorted(RAW.glob("*.xlsx")) + sorted(RAW.glob("*.xls"))
    if xlsx:
        return xlsx[0]
    zips = sorted(RAW.glob("*.zip"))
    if not zips:
        raise FileNotFoundError(
            f"{RAW} 下未找到数据文件。请将 UCI 官方 online+retail+ii.zip "
            f"（或解压后的 online_retail_II.xlsx）放入 data/raw/。下载地址：{DS_URL}"
        )
    z = zips[0]
    with zipfile.ZipFile(z) as zf:
        for info in zf.infolist():
            if info.filename.lower().endswith((".xlsx", ".xls", ".csv")):
                zf.extract(info, RAW)
                path = RAW / info.filename
                print(f"[load] 已解压 {z.name} -> {path.name}")
                return path
    raise FileNotFoundError(f"{z} 中未找到 Excel/CSV 文件")


def read_sheets(path):
    """按工作表分表读取，保留来源工作表标记（用于追溯）。"""
    frames = []
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path, encoding="utf-8-sig")
        frames.append(("single", df))
    else:
        xls = pd.ExcelFile(path)
        print(f"[load] 工作表：{xls.sheet_names}")
        for sn in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sn)
            frames.append((sn, df))

    out = []
    for sn, df in frames:
        df = df.rename(columns=lambda c: COLMAP.get(str(c).strip().lower(), str(c).strip()))
        df["SourceSheet"] = sn
        out.append(df)
        print(f"[load]   {sn}: {df.shape[0]:,} 行 × {df.shape[1]} 列")
    return pd.concat(out, ignore_index=True)


def main():
    path = locate_source()
    print(f"[load] 数据源：{DS_NAME}\n[load] 来源：{DS_URL}\n[load] 文件：{path.name}")
    df = read_sheets(path)

    need = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "CustomerID", "Country"]
    missing = [c for c in need if c not in df.columns]
    if missing:
        raise KeyError(f"缺少必需字段 {missing}，实际字段：{list(df.columns)}")

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df.to_pickle(RAW / "raw_all.pkl")

    overview = {
        "数据源": DS_NAME,
        "数据集主页": DS_URL,
        "原始记录数": int(len(df)),
        "字段数": int(df.shape[1] - 1),
        "工作表数": int(df["SourceSheet"].nunique()),
        "时间起": str(df["InvoiceDate"].min().date()),
        "时间止": str(df["InvoiceDate"].max().date()),
        "客户数（去重，含空）": int(df["CustomerID"].nunique(dropna=True)),
        "国家数": int(df["Country"].nunique()),
        "商品编码数": int(df["StockCode"].nunique()),
        "CustomerID缺失行数": int(df["CustomerID"].isna().sum()),
        "Description缺失行数": int(df["Description"].isna().sum()),
    }
    pd.DataFrame([overview]).T.rename(columns={0: "值"}).to_csv(TABS / "t01_raw_overview.csv", encoding="utf-8-sig")
    (TABS / "t01_raw_overview.json").write_text(json.dumps(overview, ensure_ascii=False, indent=2), encoding="utf-8")
    print("[load] 原始数据概览：")
    for k, v in overview.items():
        print(f"        {k}: {v}")
    print(f"[load] 已缓存 {RAW / 'raw_all.pkl'}")


if __name__ == "__main__":
    main()
