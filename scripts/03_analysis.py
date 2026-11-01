# -*- coding: utf-8 -*-
"""03 商业分析模型：趋势对比、RFM、同期群、帕累托/ABC、波士顿矩阵、关联规则、SARIMA。

每个模型都输出结果表（outputs/tables）与结构化指标（results.json），
供 04 绘图与论文写作直接引用，保证"图—表—文"三者数字一致。
"""
import json
import warnings

import numpy as np
import pandas as pd

from config import CLEAN, TABS, SEED, SEGMENTS

warnings.filterwarnings("ignore")

R = {}          # 汇总指标，供 06_report.py 引用
TABLES = []


def dump(name, df, idx=False):
    path = TABS / f"{name}.csv"
    df.to_csv(path, index=idx, encoding="utf-8-sig")
    TABLES.append(name)
    print(f"  [tab] {path.name}  ({len(df)} 行)")
    return df


# ---------------------------------------------------------------- 1. 趋势与对比
def trend(sales, returns):
    monthly = (
        sales.groupby("YM")
        .agg(销售额=("Amount", "sum"), 订单数=("Invoice", "nunique"),
             客户数=("CustomerID", "nunique"), 件数=("Quantity", "sum"))
        .reset_index()
        .sort_values("YM")
    )
    monthly["客单价"] = monthly["销售额"] / monthly["订单数"]
    monthly["环比%"] = monthly["销售额"].pct_change() * 100
    monthly["三月移动平均"] = monthly["销售额"].rolling(3, min_periods=1).mean()
    ret_m = returns.groupby("YM")["Amount"].sum()
    monthly["退货额"] = monthly["YM"].map(ret_m).fillna(0).abs()

    # 覆盖度识别：只有被数据起止日截断的月份才算不完整月。
    # 注意不能用"签到天数/自然日"判断——该零售周日闭店、节假日休市，
    # 正常月份也只有 20~27 个交易日，用自然日覆盖率会把 1/4/5/12 月误判为残缺。
    cov, dim, complete = month_coverage(sales)
    monthly["交易天数"] = monthly["YM"].map(cov).astype(int)
    monthly["自然日数"] = monthly["YM"].map(dim).astype(int)
    monthly["是否完整月"] = monthly["YM"].map(complete)
    dump("t05_monthly", monthly)

    full = monthly[monthly["是否完整月"]]
    partial = monthly[~monthly["是否完整月"]]
    r = {
        "月份数": int(len(monthly)),
        "完整月数": int(len(full)),
        "不完整月": [f"{x}（{int(d)} 个交易日，数据截止）" for x, d in zip(partial["YM"], partial["交易天数"])],
        "起始月": str(monthly["YM"].iloc[0]),
        "结束月": str(monthly["YM"].iloc[-1]),
        "总销售额": float(monthly["销售额"].sum()),
        "总订单数": int(monthly["订单数"].sum()),
        "总件数": int(monthly["件数"].sum()),
        "月均销售额": float(full["销售额"].mean()),
        "最高月": str(full.loc[full["销售额"].idxmax(), "YM"]),
        "最高月销售额": float(full["销售额"].max()),
        "最低月": str(full.loc[full["销售额"].idxmin(), "YM"]),
        "最低月销售额": float(full["销售额"].min()),
        "退货总额": float(returns["Amount"].sum()),
        "退货率": float(abs(returns["Amount"].sum()) / monthly["销售额"].sum()),
        "退货单数": int(returns["Invoice"].nunique()),
        "平均客单价": float(monthly["销售额"].sum() / monthly["订单数"].sum()),
        "最高月环比": float(full["环比%"].max()),
        "最高月环比月": str(full.loc[full["环比%"].idxmax(), "YM"]),
        "最低月环比": float(full["环比%"].min()),
        "最低月环比月": str(full.loc[full["环比%"].idxmin(), "YM"]),
    }
    # 同比：仅取两年均有完整数据的 1—11 月
    mm = monthly.copy()
    mm["Y"] = mm["YM"].str[:4].astype(int)
    mm["M"] = mm["YM"].str[5:7].astype(int)
    yoy = mm[mm["M"] <= 11].pivot_table(index="M", columns="Y", values="销售额", aggfunc="sum")
    yoy = yoy.dropna()
    if {2010, 2011}.issubset(set(yoy.columns)):
        yoy["同比%"] = (yoy[2011] / yoy[2010] - 1) * 100
        dump("t05b_yoy", yoy.reset_index())
        r["同比可比月份"] = "1—11 月"
        r["2010年1至11月销售额"] = float(yoy[2010].sum())
        r["2011年1至11月销售额"] = float(yoy[2011].sum())
        r["整体同比增速"] = float((yoy[2011].sum() / yoy[2010].sum() - 1) * 100)
        r["同比正增长月份数"] = int((yoy["同比%"] > 0).sum())
        r["同比负增长月份数"] = int((yoy["同比%"] <= 0).sum())
        r["同比最高月"] = str(int(yoy["同比%"].idxmax()))
        r["同比最高增速"] = float(yoy["同比%"].max())
        r["同比最低月"] = str(int(yoy["同比%"].idxmin()))
        r["同比最低增速"] = float(yoy["同比%"].min())
    R["趋势"] = r
    print(f"[03] 趋势：总销售额 {r['总销售额']:,.0f}，月均 {r['月均销售额']:,.0f}，退货率 {r['退货率']:.2%}")


# ---------------------------------------------------------------- 2. RFM
def rfm(sales):
    snapshot = sales["Date"].max() + pd.Timedelta(days=1)
    c = (
        sales.dropna(subset=["CustomerID"])
        .groupby("CustomerID")
        .agg(R=("Date", lambda s: (snapshot - s.max()).days),
             F=("Invoice", "nunique"),
             M=("Amount", "sum"))
    )
    c["R分值"] = pd.qcut(c["R"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1], duplicates="drop").astype(int)
    c["F分值"] = pd.qcut(c["F"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)
    c["M分值"] = pd.qcut(c["M"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5], duplicates="drop").astype(int)

    r_mid, f_mid, m_mid = c["R"].median(), c["F"].median(), c["M"].median()
    rh = c["R"] <= r_mid          # R 越小越近，故"高"取小于中位数
    fh = c["F"] > f_mid
    mh = c["M"] > m_mid

    def name(i):
        return SEGMENTS[i]

    seg = np.select(
        [rh & fh & mh, ~rh & fh & mh, rh & ~fh & mh, ~rh & ~fh & mh,
         rh & fh & ~mh, ~rh & fh & ~mh, rh & ~fh & ~mh],
        [0, 1, 2, 3, 4, 5, 6],
        default=7,
    )
    c["客户层级"] = [name(i) for i in seg]

    g = (
        c.groupby("客户层级")
        .agg(客户数=("M", "size"), 平均R=("R", "mean"), 平均F=("F", "mean"),
             平均M=("M", "mean"), 销售额=("M", "sum"),
             平均R分值=("R分值", "mean"), 平均F分值=("F分值", "mean"), 平均M分值=("M分值", "mean"))
        .reindex(SEGMENTS).dropna(how="all")
        .reset_index()
    )
    g["客户占比"] = g["客户数"] / g["客户数"].sum()
    g["销售额占比"] = g["销售额"] / g["销售额"].sum()
    g["客单价"] = g["销售额"] / g["客户数"]
    g = g.sort_values("销售额", ascending=False)
    dump("t06_rfm_summary", g.round(4))
    c.reset_index().to_csv(CLEAN / "rfm_customer.csv", index=False, encoding="utf-8-sig")

    top = g.iloc[0]
    important = g[g["客户层级"].str.startswith("重要")]
    R["rfm"] = {
        "客户数": int(len(c)),
        "销售额": float(c["M"].sum()),
        "R中位数": float(r_mid), "F中位数": float(f_mid), "M中位数": float(m_mid),
        "R均值": float(c["R"].mean()), "F均值": float(c["F"].mean()), "M均值": float(c["M"].mean()),
        "客单价中位数": float(c["M"].median()),
        "最大单客户销售额": float(c["M"].max()),
        "Top1%客户销售额占比": float(c["M"].nlargest(max(1, int(len(c) * 0.01))).sum() / c["M"].sum()),
        "最大层级": str(top["客户层级"]), "最大层级销售额占比": float(top["销售额占比"]),
        "重要客户数": int(important["客户数"].sum()),
        "重要客户占比": float(important["客户数"].sum() / len(c)),
        "重要客户销售额占比": float(important["销售额"].sum() / c["M"].sum()),
        "重要客户客单价": float(important["销售额"].sum() / important["客户数"].sum()),
        "整体客单价": float(c["M"].mean()),
        "复购客户占比": float((c["F"] > 1).mean()),
        "仅购一次客户数": int((c["F"] == 1).sum()),
    }
    for _, row in g.iterrows():
        key = row["客户层级"]
        R["rfm"][f"seg_{key}"] = {
            "客户数": int(row["客户数"]), "客户占比": float(row["客户占比"]),
            "销售额": float(row["销售额"]), "销售额占比": float(row["销售额占比"]),
            "平均R": float(row["平均R"]), "平均F": float(row["平均F"]), "平均M": float(row["平均M"]),
        }
    print(f"[03] RFM：{len(c):,} 位客户，重要客户占比 {R['rfm']['重要客户占比']:.2%}，"
          f"贡献销售额 {R['rfm']['重要客户销售额占比']:.2%}")


# ---------------------------------------------------------------- 3. 同期群留存
def cohort(sales, min_size=50):
    s = sales.dropna(subset=["CustomerID"]).copy()
    s["OrderMonth"] = s["Date"].dt.to_period("M")
    first = s.groupby("CustomerID")["OrderMonth"].min().rename("Cohort")
    s = s.join(first, on="CustomerID")
    s["Index"] = (s["OrderMonth"] - s["Cohort"]).apply(lambda x: x.n)
    g = s.groupby(["Cohort", "Index"])["CustomerID"].nunique().rename("客户数").reset_index()
    size = g[g["Index"] == 0].set_index("Cohort")["客户数"]
    g = g[g["Cohort"].isin(size[size >= min_size].index)]
    g["留存率"] = g.apply(lambda r: r["客户数"] / size[r["Cohort"]], axis=1)
    mat = g.pivot(index="Cohort", columns="Index", values="留存率")
    mat.index = mat.index.astype(str)
    dump("t08_cohort_matrix", mat.round(4), idx=True)
    size_df = size[size >= min_size].rename("群规模").reset_index()
    size_df["Cohort"] = size_df["Cohort"].astype(str)
    dump("t08b_cohort_size", size_df)
    # 平均留存曲线
    curve = g.groupby("Index").apply(lambda d: (d["客户数"].sum() / d["Cohort"].map(size).sum())).rename("平均留存率")
    dump("t08c_cohort_curve", curve.reset_index().round(4))
    m1 = float(curve.get(1, np.nan))
    m3 = float(curve.get(3, np.nan))
    m6 = float(curve.get(6, np.nan))
    m12 = float(curve.get(12, np.nan))
    R["cohort"] = {
        "群数": int(len(mat)), "起始群": str(mat.index[0]), "最新群": str(mat.index[-1]),
        "样本群门槛": min_size, "覆盖客户数": int(size[size >= min_size].sum()),
        "首月留存": m1, "第3月留存": m3, "第6月留存": m6, "第12月留存": m12,
        "长尾月数": int(mat.shape[1] - 1),
    }
    print(f"[03] 同期群：{len(mat)} 个群，首月留存 {m1:.1%}，第 6 月留存 {m6:.1%}")


# ---------------------------------------------------------------- 4. 帕累托 / ABC
def pareto(sales):
    p = (
        sales.groupby("StockCode")
        .agg(销售额=("Amount", "sum"), 销量=("Quantity", "sum"), 订单数=("Invoice", "nunique"))
        .sort_values("销售额", ascending=False)
        .reset_index()
    )
    p["累计销售额"] = p["销售额"].cumsum()
    p["累计占比"] = p["累计销售额"] / p["销售额"].sum()
    p["SKU排名"] = np.arange(1, len(p) + 1)
    p["SKU累计占比"] = p["SKU排名"] / len(p)
    p["ABC"] = np.where(p["累计占比"] <= 0.8, "A", np.where(p["累计占比"] <= 0.95, "B", "C"))
    dump("t09_pareto", p.round(4))  # 全量落盘，供帕累托图绘制完整累计曲线

    abc = p.groupby("ABC").agg(SKU数=("StockCode", "size"), 销售额=("销售额", "sum")).reset_index()
    abc["SKU占比"] = abc["SKU数"] / abc["SKU数"].sum()
    abc["销售额占比"] = abc["销售额"] / abc["销售额"].sum()
    dump("t09b_abc", abc.round(4))

    a = abc[abc["ABC"] == "A"].iloc[0]
    n80 = int((p["累计占比"] <= 0.8).sum())
    R["pareto"] = {
        "SKU总数": int(len(p)),
        "贡献80%销售额SKU数": n80,
        "贡献80%销售额SKU占比": float(n80 / len(p)),
        "A类SKU数": int(a["SKU数"]), "A类销售额占比": float(a["销售额占比"]),
        "B类SKU数": int(abc.loc[abc["ABC"] == "B", "SKU数"].iloc[0]),
        "B类销售额占比": float(abc.loc[abc["ABC"] == "B", "销售额占比"].iloc[0]),
        "C类SKU数": int(abc.loc[abc["ABC"] == "C", "SKU数"].iloc[0]),
        "C类销售额占比": float(abc.loc[abc["ABC"] == "C", "销售额占比"].iloc[0]),
        "Top10商品销售额占比": float(p.head(10)["销售额"].sum() / p["销售额"].sum()),
    }
    top10 = p.head(10).copy()
    desc = sales.groupby("StockCode")["Description"].agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else "")
    top10["商品名称"] = top10["StockCode"].map(desc).str.slice(0, 40)
    dump("t09c_top10_product", top10[["StockCode", "商品名称", "销售额", "销量", "订单数"]].round(2))
    print(f"[03] ABC：A 类 {R['pareto']['A类SKU数']} 个 SKU 贡献 {R['pareto']['A类销售额占比']:.2%} 销售额")


# ---------------------------------------------------------------- 5. 波士顿矩阵
def boston(sales):
    s = sales.copy()
    s["Y"] = s["Date"].dt.year
    s["M"] = s["Date"].dt.month
    comp = s[s["M"] <= 11]                     # 1—11 月为两年可比口径
    tot = comp.groupby("Country")["Amount"].sum().rename("销售额")
    df = tot.to_frame()
    df["份额"] = df["销售额"] / df["销售额"].sum()
    y10 = comp[comp["Y"] == 2010].groupby("Country")["Amount"].sum().rename("y2010")
    y11 = comp[comp["Y"] == 2011].groupby("Country")["Amount"].sum().rename("y2011")
    df = df.join(y10).join(y11).fillna(0)
    df["增速"] = np.where(df["y2010"] > 0, (df["y2011"] / df["y2010"] - 1) * 100, np.nan)
    df["客户数"] = comp.groupby("Country")["CustomerID"].nunique()
    # 业务单元取销售额前 10 名的国家：既覆盖主要市场，又保证象限图可读
    df = df.nlargest(min(10, len(df)), "销售额").copy()
    share_cut = df["份额"].median()
    # 增速分界统一取全市场 1—11 月的整体同比增速，与 4.3 节口径一致
    growth_cut = float(R["趋势"]["整体同比增速"])
    df["象限"] = np.select(
        [(df["份额"] >= share_cut) & (df["增速"] >= growth_cut),
         (df["份额"] < share_cut) & (df["增速"] >= growth_cut),
         (df["份额"] >= share_cut) & (df["增速"] < growth_cut)],
        ["明星", "问题", "现金牛"], default="瘦狗",
    )
    df = df.reset_index().rename(columns={"Country": "国家"})
    df = df.sort_values("销售额", ascending=False)
    dump("t10_boston", df.round(4))
    R["boston"] = {
        "单元数": int(len(df)), "份额分界": float(share_cut), "增速分界": growth_cut,
        "整体增速": growth_cut,
        "明星": df[df["象限"] == "明星"]["国家"].tolist(),
        "现金牛": df[df["象限"] == "现金牛"]["国家"].tolist(),
        "问题": df[df["象限"] == "问题"]["国家"].tolist(),
        "瘦狗": df[df["象限"] == "瘦狗"]["国家"].tolist(),
        "英国份额": float(df.loc[df["国家"] == "United Kingdom", "份额"].iloc[0]) if "United Kingdom" in set(df["国家"]) else None,
        "英国增速": float(df.loc[df["国家"] == "United Kingdom", "增速"].iloc[0]) if "United Kingdom" in set(df["国家"]) else None,
        "非英国国家数": int((df["国家"] != "United Kingdom").sum()),
        "非英国销售额占比": float(df.loc[df["国家"] != "United Kingdom", "销售额"].sum() / df["销售额"].sum()),
    }
    print(f"[03] 波士顿矩阵：{len(df)} 个国家单元，明星 {R['boston']['明星']}")


# ---------------------------------------------------------------- 6. 关联规则
def association(sales, top_n=100):
    basket = sales.dropna(subset=["CustomerID"])
    # 仅保留最热销的前 top_n 个 SKU，既覆盖主要交易又控制矩阵规模
    cnt = basket.groupby("StockCode")["Invoice"].nunique().sort_values(ascending=False)
    keep = cnt.head(top_n).index
    b = basket[basket["StockCode"].isin(keep)]
    # 覆盖率 = 含至少一个入选 SKU 的订单数 / 全部订单数（不能把各 SKU 订单数直接相加）
    n_all = basket["Invoice"].nunique()
    coverage = b["Invoice"].nunique() / n_all
    piv = pd.crosstab(b["Invoice"], b["StockCode"]) > 0
    desc = sales.groupby("StockCode")["Description"].agg(lambda s: s.dropna().mode().iloc[0] if s.notna().any() else "")

    try:
        from mlxtend.frequent_patterns import apriori, association_rules
        freq = apriori(piv, min_support=0.01, use_colnames=True, max_len=3)
        rules = association_rules(freq, metric="lift", min_threshold=1.2)
        rules = rules.sort_values(["lift", "confidence"], ascending=False).head(15).copy()
        if len(rules) == 0:
            raise ValueError("在当前支持度/提升度阈值下无有效规则")
        rules["前项"] = rules["antecedents"].apply(lambda s: " + ".join(sorted(desc.get(i, str(i)) for i in s))[:60])
        rules["后项"] = rules["consequents"].apply(lambda s: " + ".join(sorted(desc.get(i, str(i)) for i in s))[:40])
        out = rules[["前项", "后项", "support", "confidence", "lift"]].round(4)
        dump("t11_rules", out)
        best = out.iloc[0]
        R["apriori"] = {
            "工具": "mlxtend.apriori", "参与SKU数": int(top_n), "SKU覆盖订单比例": float(coverage),
            "事务数": int(piv.shape[0]), "最小支持度": 0.01, "最小提升度": 1.2,
            "规则数": int(len(out)),
            "最强前项": str(best["前项"]), "最强后项": str(best["后项"]),
            "最强提升度": float(best["lift"]), "最强置信度": float(best["confidence"]),
            "最强支持度": float(best["support"]),
            "平均提升度": float(out["lift"].mean()),
        }
        R["apriori"]["规则明细"] = out.to_dict("records")
        print(f"[03] 关联规则：{len(out)} 条，最强提升度 {best['lift']:.2f}")
    except Exception as e:      # 依赖缺失时优雅降级，并如实记录
        R["apriori"] = {"错误": f"{type(e).__name__}: {e}"}
        print(f"[03] 关联规则跳过：{e}")


# ---------------------------------------------------------------- 7. SARIMA 预测
def month_coverage(sales):
    """返回 (交易天数, 自然日数, 是否完整月)。

    完整月判定只看数据起止日是否切在月内：周日闭店、节假日休市都会让交易天数
    少于自然日，但那是真实经营节奏，不能当作缺失。
    """
    d = sales["Date"]
    dmin, dmax = d.min(), d.max()
    cov = sales.groupby("YM")["Date"].agg(lambda s: s.dt.normalize().nunique())
    dim = pd.Series({k: pd.Period(k, freq="M").days_in_month for k in cov.index})
    first, last = sales["YM"].min(), sales["YM"].max()
    head_cut = dmin.day > 1
    tail_cut = dmax.day < int(dim[last])
    complete = {k: not ((k == first and head_cut) or (k == last and tail_cut)) for k in cov.index}
    return cov, dim, complete


def sarima(sales):
    # 只用完整月建模：残缺月的"销售额"是半个月，放进训练集会压低趋势，
    # 放进回测集会放大误差（实测会把 MAPE 从 7% 抬到 38%）。
    cov, dim, complete = month_coverage(sales)
    keep = [k for k in cov.index if complete[k]]
    dropped = [f"{k}（{int(cov[k])} 个交易日）" for k in cov.index if not complete[k]]
    m = sales[sales["YM"].isin(keep)].groupby("YM")["Amount"].sum().sort_index()
    m.index = pd.PeriodIndex(m.index, freq="M")
    y = m.astype(float)
    horizon_test, horizon_future = 6, 6
    train, test = y.iloc[:-horizon_test], y.iloc[-horizon_test:]
    # 定阶依据：在 24 个完整月上做滚动留出对比（见 4.3 节表 5），
    # 非季节项 (1,1,0)、季节项 (0,1,1,12) 的 MAPE 最低；加入季节 AR 项会因样本不足
    # 触发 statsmodels 的 "too few observations" 警告并出现过拟合。
    method, order, sorder = "SARIMA", (1, 1, 0), (0, 1, 1, 12)
    try:
        import warnings as _w
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = SARIMAX(train, order=order, seasonal_order=sorder,
                          enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
            pred = fit.get_forecast(steps=horizon_test)
            fc_test = pd.Series(pred.predicted_mean.values, index=test.index)
            ci_test = pred.conf_int(alpha=0.05)
            ci_test.index = test.index
            full = SARIMAX(y, order=order, seasonal_order=sorder,
                           enforce_stationarity=False, enforce_invertibility=False).fit(disp=False)
            pf = full.get_forecast(steps=horizon_future)
            fc_future = pd.Series(pf.predicted_mean.values,
                                  index=pd.period_range(y.index[-1] + 1, periods=horizon_future, freq="M"))
            ci_future = pf.conf_int(alpha=0.05)
            ci_future.index = fc_future.index
        R["sarima_aic"] = float(full.aic)
        R["sarima_params"] = f"{order} × {sorder}"
    except Exception as e:
        # 无 statsmodels 时的降级方案：经典加法分解（趋势线性外推 + 月度季节因子）
        print(f"[03] SARIMA 不可用（{e}），回退季节分解法")
        method, order, sorder = "季节分解（趋势+季节因子）", None, None

        def decomp_forecast(series, steps):
            v = np.asarray(series.values, dtype=float)
            idx = np.arange(len(v))
            k = 12
            if len(v) >= 2 * k:
                trend = pd.Series(v).rolling(k, center=True, min_periods=1).mean().to_numpy()
                detr = v - trend
                season = np.array([np.nanmedian(detr[np.arange(len(v)) % k == i]) for i in range(k)])
                season = np.nan_to_num(season - np.nanmean(season))
            else:
                trend, season = v, np.zeros(k)
            b, a = np.polyfit(idx, trend, 1)
            fitted = a + b * idx + season[np.arange(len(v)) % k]
            resid = v - fitted
            sd = float(np.std(resid, ddof=1)) if len(v) > 2 else float(np.std(v))
            fut_idx = np.arange(len(v), len(v) + steps)
            mu = a + b * fut_idx + season[fut_idx % k]
            half = 1.96 * sd * np.sqrt(np.arange(1, steps + 1))
            return pd.Series(mu), pd.DataFrame({0: mu - half, 1: mu + half}), sd

        fc_v, ci_v, sd = decomp_forecast(train, horizon_test)
        fc_test = pd.Series(fc_v.values, index=test.index)
        ci_test = ci_v.copy()
        ci_test.index = test.index
        fc_f, ci_f, _ = decomp_forecast(y, horizon_future)
        fc_future = pd.Series(fc_f.values,
                              index=pd.period_range(y.index[-1] + 1, periods=horizon_future, freq="M"))
        ci_future = ci_f.copy()
        ci_future.index = fc_future.index
        R["sarima_aic"] = float("nan")
        R["sarima_params"] = "加法分解：12 个月移动平均趋势 + 月度季节因子"

    mape = float(np.mean(np.abs((test.values - fc_test.values) / test.values)) * 100)
    rmse = float(np.sqrt(np.mean((test.values - fc_test.values) ** 2)))
    mae = float(np.mean(np.abs(test.values - fc_test.values)))
    rows = []
    # 历史段只放训练期，回测段单独成行（带实际值），避免同一个月在表里出现两次
    for k in train.index:
        rows.append({"月份": str(k), "实际值": float(y.loc[k]), "预测值": np.nan,
                     "下界": np.nan, "上界": np.nan, "类型": "历史"})
    for k in test.index:
        rows.append({"月份": str(k), "实际值": float(y.loc[k]), "预测值": float(fc_test.loc[k]),
                     "下界": float(ci_test.iloc[list(test.index).index(k), 0]),
                     "上界": float(ci_test.iloc[list(test.index).index(k), 1]), "类型": "回测"})
    for k in fc_future.index:
        i = list(fc_future.index).index(k)
        rows.append({"月份": str(k), "实际值": np.nan, "预测值": float(fc_future.loc[k]),
                     "下界": float(ci_future.iloc[i, 0]), "上界": float(ci_future.iloc[i, 1]), "类型": "预测"})
    dump("t12_forecast", pd.DataFrame(rows).round(2))

    metrics = pd.DataFrame([
        {"指标": "MAPE", "取值": round(mape, 2), "单位": "%", "口径": f"最后 {horizon_test} 个月留出回测"},
        {"指标": "RMSE", "取值": round(rmse, 2), "单位": "英镑", "口径": f"最后 {horizon_test} 个月留出回测"},
        {"指标": "MAE", "取值": round(mae, 2), "单位": "英镑", "口径": f"最后 {horizon_test} 个月留出回测"},
        {"指标": "AIC", "取值": round(float(R.get("sarima_aic", np.nan)), 2) if pd.notna(R.get("sarima_aic", np.nan)) else None,
         "单位": "-", "口径": "全样本重拟合"},
    ])
    dump("t13_metrics", metrics)

    R["forecast"] = {
        "方法": method, "参数": R.get("sarima_params"),
        "训练月数": int(len(train)), "回测月数": horizon_test, "预测月数": horizon_future,
        "剔除不完整月": dropped,
        "MAPE": mape, "RMSE": rmse, "MAE": mae,
        "回测期": f"{test.index[0]} 至 {test.index[-1]}",
        "预测期": f"{fc_future.index[0]} 至 {fc_future.index[-1]}",
        "未来预测": [{"月份": str(k), "预测值": float(v), "下界": float(ci_future.iloc[i, 0]),
                     "上界": float(ci_future.iloc[i, 1])} for i, (k, v) in enumerate(fc_future.items())],
        "回测明细": [{"月份": str(k), "实际": float(test.loc[k]), "预测": float(fc_test.loc[k])} for k in test.index],
    }
    print(f"[03] 预测：{method}，MAPE {mape:.2f}%，RMSE {rmse:,.0f}")


# ---------------------------------------------------------------- 8. 探索性统计
def eda(sales, returns):
    stat = sales[["Quantity", "Price", "Amount"]].describe().T
    stat["偏度"] = sales[["Quantity", "Price", "Amount"]].skew()
    dump("t03_eda_stat", stat.round(3).reset_index().rename(columns={"index": "字段"}))

    inv = sales.groupby("Invoice")["Amount"].sum()
    country = sales.groupby("Country")["Amount"].sum().sort_values(ascending=False).head(12)
    dow = sales.groupby("DOW")["Amount"].sum().reindex(range(7)).fillna(0)
    hour = sales.groupby("Hour")["Amount"].sum().sort_index()
    R["eda"] = {
        "订单数": int(sales["Invoice"].nunique()),
        "商品行数": int(len(sales)),
        "客户数": int(sales["CustomerID"].nunique()),
        "商品数": int(sales["StockCode"].nunique()),
        "国家数": int(sales["Country"].nunique()),
        "平均订单金额": float(inv.mean()), "订单金额中位数": float(inv.median()),
        "订单金额P95": float(inv.quantile(0.95)), "最大订单金额": float(inv.max()),
        "件数中位数": float(sales["Quantity"].median()),
        "单价中位数": float(sales["Price"].median()),
        "单价均值": float(sales["Price"].mean()),
        "Top国家": {str(k): float(v) for k, v in country.items()},
        "英国销售额占比": float(sales.loc[sales["Country"] == "United Kingdom", "Amount"].sum() / sales["Amount"].sum()),
        "海外销售额占比": float(sales.loc[sales["Country"] != "United Kingdom", "Amount"].sum() / sales["Amount"].sum()),
        "周末销售额占比": float(sales.loc[sales["IsWeekend"], "Amount"].sum() / sales["Amount"].sum()),
        "工作日销售额占比": float(sales.loc[~sales["IsWeekend"], "Amount"].sum() / sales["Amount"].sum()),
        "最忙日": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][int(dow.idxmax())],
        "最忙时段": int(hour.idxmax()),
        "最忙日销售额": float(dow.max()),
        "单客户订单数均值": float(sales.dropna(subset=["CustomerID"]).groupby("CustomerID")["Invoice"].nunique().mean()),
        "退货单数占比": float(returns["Invoice"].nunique() / (returns["Invoice"].nunique() + sales["Invoice"].nunique())),
        "退货客户数": int(returns["CustomerID"].nunique()),
    }
    dump("t03b_top_country", country.reset_index().round(2))
    dump("t03c_dow", pd.DataFrame({"星期": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
                                   "销售额": dow.values}).round(2))
    print(f"[03] EDA：订单 {R['eda']['订单数']:,}，客户 {R['eda']['客户数']:,}，商品 {R['eda']['商品数']:,}")


def main():
    sales = pd.read_pickle(CLEAN / "sales.pkl")
    returns = pd.read_pickle(CLEAN / "returns.pkl")
    print(f"[03] 参与分析：销售 {len(sales):,} 行，退货 {len(returns):,} 行")
    trend(sales, returns)
    eda(sales, returns)
    rfm(sales)
    cohort(sales)
    pareto(sales)
    boston(sales)
    association(sales)
    sarima(sales)
    R["随机种子"] = SEED
    (TABS / "results.json").write_text(json.dumps(R, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[03] 结果已写入 {TABS / 'results.json'}")


if __name__ == "__main__":
    main()
