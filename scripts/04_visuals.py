# -*- coding: utf-8 -*-
"""04 数据可视化：14 张模板复现图 + 8 张业务模型图，全部由 Python 生成。

模板复现类（fig01–fig14）对照《Excel数据可视化——从图表到数据大屏》中的
折线 / 面积 / 簇状柱形 / 条形 / 环形 / 双轴组合 / 直方 / 箱线 / 热力 / 树状 /
雷达 / 瀑布 / KPI 卡片 / 散点 14 种版式，在图表类型、布局、配色、标签、
图例位置与标题设计上贴近原作；业务模型类（fig15–fig22）与第 4 章模型一一对应。
"""
import io
import json

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle
from matplotlib.ticker import FuncFormatter, PercentFormatter

from config import CLEAN, TABS, SEED, SEGMENTS
from viz_style import C, PAL, k_formatter, money_axis, save, source_note, tidy

plt.rcParams["axes.unicode_minus"] = False
OK, FAIL = [], []


def guard(name):
    def deco(fn):
        def wrapper():
            try:
                fn()
                OK.append(name)
            except Exception as e:
                FAIL.append((name, f"{type(e).__name__}: {e}"))
                print(f"  [!!] {name} 失败：{type(e).__name__}: {e}")
        return wrapper
    return deco


def T(n):
    return pd.read_csv(TABS / f"{n}.csv", encoding="utf-8-sig")


def TM():
    """月度表：剔除被数据起止日截断的不完整月，避免趋势/瀑布/双轴图出现假断崖。"""
    m = T("t05_monthly")
    return m[m["是否完整月"]].reset_index(drop=True)


# ============================================================ 模板复现类
@guard("fig01 折线图")
def fig01():
    m = TM()
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    ax.plot(m["YM"], m["销售额"], color=C["blue"], lw=2.2, marker="o", ms=4.5,
            mfc="white", mew=1.4, zorder=3, label="月度销售额")
    ax.plot(m["YM"], m["三月移动平均"], color=C["orange"], lw=1.8, ls="--", label="三月移动平均")
    ax.fill_between(range(len(m)), m["销售额"], color=C["blue3"], alpha=0.12)
    ax.set_xticks(range(len(m)))
    ax.set_xticklabels(m["YM"], rotation=45, ha="right", fontsize=7.8)
    ax.set_ylabel("销售额（英镑）")
    ax.set_title("月度销售额走势（2009年12月—2011年11月，24 个完整月）", pad=12)
    money_axis(ax)
    tidy(ax)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    i = int(m["销售额"].idxmax())
    ax.annotate(f"峰值 {m.loc[i,'销售额']/1e4:.1f} 万",
                xy=(i, m.loc[i, "销售额"]), xytext=(i - 4.5, m["销售额"].max() * 0.86),
                fontsize=8, color=C["red"],
                arrowprops=dict(arrowstyle="->", color=C["red"], lw=0.9))
    source_note(fig)
    save(fig, "fig01_月度销售额折线图.png")


@guard("fig02 面积图")
def fig02():
    m = TM()
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = range(len(m))
    ax.fill_between(x, m["销售额"], color=C["blue"], alpha=0.75, lw=0)
    ax.fill_between(x, m["销售额"] * 0.62, color=C["bg"], alpha=0, lw=0)
    ax.plot(x, m["销售额"], color=C["blue2"], lw=1.2)
    ax.plot(x, m["销售额"].cumsum() / m["销售额"].cumsum().iloc[-1] * m["销售额"].max(),
            color=C["orange"], lw=1.6, ls=":", label="累计占比（归一化）")
    ax.set_xticks(list(x))
    ax.set_xticklabels(m["YM"], rotation=45, ha="right", fontsize=7.8)
    ax.set_ylabel("销售额（英镑）")
    ax.set_title("月度销售额面积图与累计贡献曲线", pad=12)
    money_axis(ax)
    tidy(ax)
    ax.legend(loc="upper left", frameon=False)
    for k in (0, len(m) - 1):
        ax.annotate(f"{m.loc[k,'销售额']/1e4:.1f}万", (k, m.loc[k, "销售额"]),
                    textcoords="offset points", xytext=(0, 8), ha="center", fontsize=8)
    source_note(fig)
    save(fig, "fig06_月度销售额面积图.png")


@guard("fig03 簇状柱形图")
def fig03():
    y = T("t05b_yoy")
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    w = 0.38
    x = np.arange(len(y))
    b1 = ax.bar(x - w / 2, y["2010"], width=w, color=C["blue3"], label="2010 年", edgecolor="white", lw=0.6)
    b2 = ax.bar(x + w / 2, y["2011"], width=w, color=C["blue"], label="2011 年", edgecolor="white", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{int(v)}月" for v in y["M"]], fontsize=8.5)
    ax.set_ylabel("销售额（英镑）")
    ax.set_title("2010 与 2011 年 1—11 月销售额对比", pad=12)
    money_axis(ax)
    tidy(ax)
    ax.set_ylim(0, y[["2010", "2011"]].to_numpy().max() * 1.22)   # 顶部留白，避免图例压住柱顶标签
    ax.legend(loc="upper left", frameon=False, ncol=2)
    for i, v in enumerate(y["同比%"]):
        col = C["green"] if v >= 0 else C["red"]
        ax.annotate(f"{v:+.0f}%", (x[i], max(y["2010"].iloc[i], y["2011"].iloc[i])),
                    textcoords="offset points", xytext=(0, 4), ha="center", fontsize=7.5, color=col)
    source_note(fig)
    save(fig, "fig07_年度月度对比簇状柱形图.png")


@guard("fig04 条形图")
def fig04():
    d = T("t03b_top_country").head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    colors = [C["orange"] if n == "United Kingdom" else C["blue"] for n in d["Country"]]
    ax.barh(d["Country"], d["Amount"], color=colors, height=0.62, edgecolor="white")
    for i, (n, v) in enumerate(zip(d["Country"], d["Amount"])):
        ax.text(v * 1.01, i, f"{v/1e4:.1f}万", va="center", fontsize=8, color="#333")
    ax.set_xlabel("销售额（英镑）")
    ax.set_title("销售额前 10 位国家（橙色为英国本土）", pad=12)
    money_axis(ax, "x")
    tidy(ax, "x")
    ax.set_xlim(0, d["Amount"].max() * 1.14)
    source_note(fig)
    save(fig, "fig02_国家销售额条形图.png")


@guard("fig05 环形图")
def fig05():
    """环形图：前 7 国 + 其他 36 国，口径与正文「43 国合计」一致。"""
    d = T("t03b_top_country")
    res = json.load(io.open(TABS / "results.json", encoding="utf-8"))
    total = float(res["趋势"]["总销售额"])
    top = d.head(7)
    rest_n = int(res["eda"]["国家数"]) - len(top)
    rest = total - float(top["Amount"].sum())

    vals = list(top["Amount"].values) + ([rest] if rest > 0 else [])
    labels = list(top["Country"].values) + ([f"其他 {rest_n} 国"] if rest > 0 else [])
    colors = PAL[: len(vals) - 1] + ["#B9C4CF"] if rest > 0 else PAL[: len(vals)]

    fig, ax = plt.subplots(figsize=(6.6, 4.4))
    wedges, _ = ax.pie(vals, colors=colors, startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.42, edgecolor="white", linewidth=1.4))
    ax.text(0, 0.08, f"{total/1e6:.2f}", ha="center", va="center", fontsize=19,
            fontweight="bold", color=C["dark"])
    ax.text(0, -0.17, "百万英镑（43 国合计）", ha="center", va="center", fontsize=8.4, color="#555")

    # 大占比扇区标在环外，小占比统一并入图例，避免标签重叠
    for w, lab, v in zip(wedges, labels, vals):
        share = v / total
        if share < 0.03:      # 小扇区并入图例，避免环外标签互相压盖
            continue
        ang = np.deg2rad((w.theta2 + w.theta1) / 2)
        ax.annotate(f"{lab}" + chr(10) + f"{share:.1%}",
                    xy=(np.cos(ang) * 0.79, np.sin(ang) * 0.79),
                    xytext=(np.cos(ang) * 1.20, np.sin(ang) * 1.20), ha="center", va="center",
                    fontsize=8, arrowprops=dict(arrowstyle="-", color="#999", lw=0.7))
    handles = [mpatches.Patch(color=c_, label=f"{l_[:14]} {v_/total:.1%}")
               for c_, l_, v_ in zip(colors, labels, vals) if v_ / total < 0.03]
    if handles:
        ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.0, 0.5),
                  frameon=False, fontsize=7.6, handlelength=1.0, labelspacing=0.5)
    ax.set_title("销售额国家结构（环形图，43 国）", pad=14)
    ax.set_aspect("equal")
    source_note(fig)
    save(fig, "fig08_国家结构环形图.png")


@guard("fig06 双轴组合图")
def fig06():
    m = TM()
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    x = range(len(m))
    ax.bar(x, m["订单数"], color=C["blue3"], width=0.62, label="订单数", edgecolor="white", lw=0.5)
    ax.set_ylabel("订单数（单）")
    ax.set_xticks(list(x))
    ax.set_xticklabels(m["YM"], rotation=45, ha="right", fontsize=7.8)
    ax2 = ax.twinx()
    ax2.plot(x, m["客单价"], color=C["orange"], lw=2.0, marker="s", ms=3.5, label="客单价")
    ax2.set_ylabel("客单价（英镑/单）", color=C["orange"])
    ax2.tick_params(axis="y", colors=C["orange"])
    ax2.grid(False)
    ax.set_title("订单量与客单价双轴组合图", pad=12)
    tidy(ax)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, ncol=2)
    ax.set_ylim(0, m["订单数"].max() * 1.18)
    source_note(fig)
    save(fig, "fig09_订单量与客单价双轴图.png")


@guard("fig07 直方图")
def fig07():
    sales = pd.read_pickle(CLEAN / "sales.pkl")
    inv = sales.groupby("Invoice")["Amount"].sum()
    inv = inv[inv > 0]
    fig, ax = plt.subplots(figsize=(7.2, 3.9))
    bins = np.logspace(np.log10(max(inv.min(), 0.5)), np.log10(inv.max()), 45)
    ax.hist(inv, bins=bins, color=C["blue"], alpha=0.85, edgecolor="white", lw=0.4)
    ax.set_xscale("log")
    ax.axvline(inv.median(), color=C["orange"], lw=1.8, ls="--", label=f"中位数 {inv.median():,.0f} 英镑")
    ax.axvline(inv.mean(), color=C["red"], lw=1.5, ls=":", label=f"均值 {inv.mean():,.0f} 英镑")
    ax.set_xlabel("订单金额（英镑，对数刻度）")
    ax.set_ylabel("订单数（单）")
    ax.set_title("订单金额分布直方图（右偏显著）", pad=12)
    tidy(ax)
    ax.legend(loc="upper right", frameon=False)
    source_note(fig)
    save(fig, "fig03_订单金额分布直方图.png")


@guard("fig08 箱线图")
def fig08():
    sales = pd.read_pickle(CLEAN / "sales.pkl")
    inv = sales.groupby(["Country", "Invoice"])["Amount"].sum().reset_index()
    top = sales.groupby("Country")["Amount"].sum().nlargest(7).index.tolist()
    data = [inv.loc[inv["Country"] == c, "Amount"].values for c in top]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bp = ax.boxplot(data, showfliers=False, patch_artist=True, widths=0.55,
                    medianprops=dict(color=C["orange"], lw=1.8),
                    boxprops=dict(facecolor=C["blue3"], edgecolor=C["blue"], lw=0.9),
                    whiskerprops=dict(color=C["blue"], lw=0.9),
                    capprops=dict(color=C["blue"], lw=0.9))
    ax.set_xticks(range(1, len(top) + 1))
    ax.set_xticklabels(top, fontsize=8.2)
    for i, d in enumerate(data):
        y = np.random.default_rng(SEED + i).normal(i + 1, 0.045, min(len(d), 400))
        ax.scatter(y, np.random.default_rng(SEED).choice(d, len(y)), s=2.5, color=C["blue"], alpha=0.18, zorder=0)
    ax.set_ylabel("单笔订单金额（英镑）")
    ax.set_yscale("log")
    ax.set_title("主要国家订单金额箱线图（对数刻度）", pad=12)
    ax.tick_params(axis="x", rotation=18, labelsize=8.2)
    tidy(ax)
    source_note(fig)
    save(fig, "fig10_国家订单金额箱线图.png")


@guard("fig09 热力图")
def fig09():
    sales = pd.read_pickle(CLEAN / "sales.pkl")
    s = sales[sales["Hour"].between(6, 20)]
    piv = s.pivot_table(index="DOW", columns="Hour", values="Amount", aggfunc="sum").fillna(0)
    piv = piv.reindex(range(5))
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    im = ax.imshow(piv.values / 1e3, aspect="auto", cmap="YlGnBu")
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels(["周一", "周二", "周三", "周四", "周五"][: piv.shape[0]])
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels([f"{h}时" for h in piv.columns], fontsize=7.6, rotation=45)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j] / 1e3
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=6.4,
                    color="white" if v > np.nanpercentile(piv.values / 1e3, 65) else "#333")
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.035)
    cb.set_label("销售额（千英镑）", fontsize=8)
    ax.set_title("工作日下单时段热力图（6—20 时）", pad=12)
    source_note(fig)
    save(fig, "fig04_下单时段热力图.png")


def _squarify(values, x, y, w, h):
    """简化 slice-and-dice 树状图布局，返回每个矩形的 (x, y, w, h)。"""
    rects = []
    total = sum(values)
    vals = list(values)
    while vals:
        v = vals.pop(0)
        frac = v / total
        if w >= h:
            rw = w * frac
            rects.append((x, y, rw, h))
            x += rw
            w -= rw
        else:
            rh = h * frac
            rects.append((x, y, w, rh))
            y += rh
            h -= rh
        total -= v
    return rects


@guard("fig10 树状图")
def fig10():
    d = T("t09c_top10_product").head(12)
    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    rects = _squarify(d["销售额"].tolist(), 0, 0, 1, 1)
    cmap = plt.get_cmap("Blues_r")
    for i, ((x, y, w, h), (_, row)) in enumerate(zip(rects, d.iterrows())):
        ax.add_patch(Rectangle((x, y), w, h, facecolor=cmap(0.25 + i * 0.045),
                               edgecolor="white", lw=1.6))
        name = str(row["商品名称"])[:16]
        ax.text(x + w / 2, y + h / 2, f"{name}\n{row['销售额']/1e4:.1f}万",
                ha="center", va="center", fontsize=7.2,
                color="white" if i < 5 else "#12263A")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("销售额 Top12 商品树状图（面积=销售额）", pad=10)
    source_note(fig)
    save(fig, "fig11_商品销售额树状图.png")


@guard("fig11 雷达图")
def fig11():
    g = T("t06_rfm_summary").set_index("客户层级")
    picks = [s for s in ["重要价值客户", "重要保持客户", "一般价值客户", "一般挽留客户"] if s in g.index]
    axes_lab = ["R 得分", "F 得分", "M 得分", "客单价水平"]
    cust = g.loc[picks]
    arr = []
    for s in picks:
        row = cust.loc[s]
        arr.append([row["平均R分值"], row["平均F分值"], row["平均M分值"],
                    row["客单价"] / cust["客单价"].max() * 5])
    arr = np.array(arr, dtype=float)
    ang = np.linspace(0, 2 * np.pi, len(axes_lab), endpoint=False).tolist()
    ang += ang[:1]
    fig = plt.figure(figsize=(5.6, 4.6))
    ax = plt.subplot(111, polar=True)
    for i, s in enumerate(picks):
        vals = arr[i].tolist() + [arr[i][0]]
        ax.plot(ang, vals, lw=1.8, color=PAL[i], label=s)
        ax.fill(ang, vals, color=PAL[i], alpha=0.14)
    ax.set_xticks(ang[:-1])
    ax.set_xticklabels(axes_lab, fontsize=9)
    ax.set_ylim(0, 5.2)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_yticklabels(["1", "2", "3", "4", "5"], fontsize=7, color="#666")
    ax.set_title("核心客户层级 RFM 画像雷达图", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.28, 1.12), frameon=False, fontsize=8)
    source_note(fig)
    save(fig, "fig12_客户层级雷达图.png")


@guard("fig12 瀑布图")
def fig12():
    """近 13 个月的销售额环比增量瀑布：起点为第 13 个月，逐月累加至期末水平。"""
    m = TM().tail(13).reset_index(drop=True)
    K = 1e4  # 全部换算为万英镑后绘图，避免与纵轴单位错位
    start_v = float(m.loc[0, "销售额"]) / K
    deltas = [(float(m.loc[i, "销售额"] - m.loc[i - 1, "销售额"])) / K
              for i in range(1, len(m))]
    labels = [str(m.loc[i, "YM"])[2:] for i in range(1, len(m))]

    bars = [(0.0, start_v, None)]
    cur = start_v
    for dv in deltas:
        low = cur if dv >= 0 else cur + dv
        bars.append((low, abs(dv), dv))
        cur += dv
    bars.append((0.0, cur, None))
    ymax = max(b[0] + b[1] for b in bars) * 1.18
    off = ymax * 0.022

    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    for i, (low, h, dv) in enumerate(bars):
        if dv is None:
            ax.bar(i, h, color=C["blue"] if i == 0 else C["orange"], width=0.62)
            ax.text(i, h + off, f"{h:.1f}", ha="center", va="bottom", fontsize=7.8)
        else:
            ax.bar(i, h, bottom=low, color=C["green"] if dv >= 0 else C["red"], width=0.62)
            ax.text(i, low + h + off, f"{dv:+.1f}", ha="center", va="bottom", fontsize=7.0,
                    color=C["green"] if dv >= 0 else C["red"])
        if i < len(bars) - 1:
            ax.plot([i + 0.31, i + 0.69], [low + h] * 2, color="#9AA5B1", lw=0.6, ls=":")

    first_label = "起点 " + str(m.loc[0, "YM"])[2:]
    ax.set_xticks(range(len(bars)))
    ax.set_xticklabels([first_label] + labels + ["期末"], fontsize=7.0, rotation=45, ha="right")
    ax.set_ylabel("销售额（万英镑）")
    ax.set_ylim(0, ymax)
    ax.set_title("近 13 个月销售额环比增量瀑布图", pad=12)
    tidy(ax)
    source_note(fig)
    save(fig, "fig13_环比增量分解瀑布图.png")


@guard("fig13 KPI 卡片")
def fig13():
    from config import CLEAN as _C
    meta = json.loads((_C / "schema.json").read_text(encoding="utf-8"))
    res = json.loads((TABS / "results.json").read_text(encoding="utf-8"))
    cards = [
        ("累计销售额", f"{res['趋势']['总销售额']/1e6:.2f}M", "英镑"),
        ("订单总数", f"{res['eda']['订单数']/1e4:.1f}万", "单"),
        ("活跃客户", f"{res['eda']['客户数']/1e3:.1f}k", "人"),
        ("客单价", f"{res['eda']['平均订单金额']:.1f}", "英镑/单"),
        ("退货率", f"{res['趋势']['退货率']:.1%}", "金额口径"),
        ("商品 SKU", f"{res['eda']['商品数']/1e3:.1f}k", "个"),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    ax.set_xlim(0, 3)
    ax.set_ylim(0, 2)
    ax.axis("off")
    for i, (t, v, u) in enumerate(cards):
        r, c = divmod(i, 3)
        x, y = c * 1.0, (1 - r) * 1.0
        ax.add_patch(FancyBboxPatch((x + 0.03, y + 0.06), 0.94, 0.88,
                                    boxstyle="round,pad=0.012,rounding_size=0.05",
                                    facecolor=C["bg"], edgecolor="#D6DEE7", lw=1))
        ax.add_patch(Rectangle((x + 0.03, y + 0.06), 0.055, 0.88, facecolor=PAL[i % len(PAL)], lw=0))
        ax.text(x + 0.13, y + 0.70, t, fontsize=9, color="#5A6672")
        ax.text(x + 0.13, y + 0.33, v, fontsize=17.5, fontweight="bold", color=C["dark"])
        ax.text(x + 0.13, y + 0.16, u, fontsize=7.6, color="#8A94A0")
    ax.set_title("核心经营指标 KPI 卡片", pad=6)
    source_note(fig)
    save(fig, "fig14_核心指标KPI卡片.png")


@guard("fig14 散点图")
def fig14():
    p = T("t09_pareto").head(200)
    sales = pd.read_pickle(CLEAN / "sales.pkl")
    agg = sales.groupby("StockCode").agg(销量=("Quantity", "sum"), 销售额=("Amount", "sum")).reset_index()
    agg = agg[agg["销量"] > 0]
    price = agg["销售额"] / agg["销量"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    sc = ax.scatter(agg["销量"], price, s=np.clip(agg["销售额"] / 260, 3, 240),
                    c=np.log10(agg["销售额"]), cmap="viridis", alpha=0.55, edgecolor="none")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("单品累计销量（件，对数刻度）")
    ax.set_ylabel("平均成交单价（英镑，对数刻度）")
    ax.set_title("销量—单价—销售额三维散点图（气泡=销售额）", pad=12)
    cb = fig.colorbar(sc, ax=ax, pad=0.015, fraction=0.035)
    cb.set_label("log10(销售额)", fontsize=8)
    tidy(ax, "both")
    med_x, med_y = agg["销量"].median(), price.median()
    ax.axvline(med_x, color=C["grey"], lw=0.8, ls="--")
    ax.axhline(med_y, color=C["grey"], lw=0.8, ls="--")
    ax.text(med_x * 1.1, price.max() * 0.55, "高频高价", fontsize=8, color="#666")
    ax.text(med_x * 0.12, price.max() * 0.55, "低频高价", fontsize=8, color="#666")
    source_note(fig)
    save(fig, "fig05_销量单价散点图.png")


# ============================================================ 业务模型类
@guard("fig15 RFM 分层条形图")
def fig15():
    g = T("t06_rfm_summary")
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    g = g.sort_values("客户数")
    colors = [C["orange"] if s.startswith("重要") else C["blue3"] for s in g["客户层级"]]
    ax.barh(g["客户层级"], g["客户数"], color=colors, height=0.6, edgecolor="white", label="客户数（左轴）")
    for i, (v, share) in enumerate(zip(g["客户数"], g["销售额占比"])):
        ax.text(v + 12, i, f"{v:,} 人 / 销售 {share:.1%}", va="center", fontsize=8, color="#333")
    ax.set_xlabel("客户数（人）")
    ax.set_title("RFM 八分类客户规模与销售额贡献", pad=12)
    ax.set_xlim(0, g["客户数"].max() * 1.45)
    tidy(ax, "x")
    source_note(fig)
    save(fig, "fig15_RFM分层客户规模.png")


@guard("fig16 RFM 气泡散点")
def fig16():
    c = pd.read_csv(CLEAN / "rfm_customer.csv", encoding="utf-8-sig")
    rng = np.random.default_rng(SEED)
    c = c.sample(min(4000, len(c)), random_state=SEED)
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    order = [s for s in SEGMENTS if s in set(c["客户层级"])]
    for i, s in enumerate(order):
        d = c[c["客户层级"] == s]
        ax.scatter(d["F"], d["R"], s=np.clip(d["M"] / 55, 4, 210), alpha=0.42,
                   color=PAL[i % len(PAL)], label=s, edgecolor="none")
    ax.set_xscale("symlog", linthresh=2)
    ax.set_xlabel("购买频次 F（订单数，对称对数刻度）")
    ax.set_ylabel("最近购买间隔 R（天）")
    ax.set_title("客户价值气泡图：频次 × 最近购买 × 金额（随机抽样 4,000 人，seed=42）", pad=12)
    ax.invert_yaxis()
    tidy(ax, "both")
    ax.legend(loc="lower right", frameon=False, fontsize=7.4, ncol=2, markerscale=0.9)
    source_note(fig)
    save(fig, "fig16_客户价值气泡图.png")


@guard("fig17 同期群热力图")
def fig17():
    mat = pd.read_csv(TABS / "t08_cohort_matrix.csv", index_col=0, encoding="utf-8-sig")
    mat.columns = [int(c) for c in mat.columns]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    data = mat.values * 100
    im = ax.imshow(data, aspect="auto", cmap="YlOrRd", vmin=0, vmax=100)
    ax.set_xticks(range(mat.shape[1]))
    ax.set_xticklabels([f"+{c}" for c in mat.columns], fontsize=7.8)
    ax.set_yticks(range(mat.shape[0]))
    ax.set_yticklabels(mat.index, fontsize=7.8)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if not np.isnan(data[i, j]) and j <= mat.shape[1] - 1:
                ax.text(j, i, f"{data[i,j]:.0f}", ha="center", va="center", fontsize=6.2,
                        color="white" if data[i, j] > 60 else "#3A3A3A")
    cb = fig.colorbar(im, ax=ax, pad=0.015, fraction=0.03)
    cb.set_label("留存率（%）", fontsize=8)
    ax.set_xlabel("首购后月序（+0 为首购当月）")
    ax.set_ylabel("同期群（首购月份）")
    ax.set_title("同期群月度留存热力图", pad=12)
    source_note(fig)
    save(fig, "fig17_同期群留存热力图.png")


@guard("fig18 帕累托图")
def fig18():
    p = T("t09_pareto").sort_values("SKU排名").reset_index(drop=True)
    n = len(p)
    head_n = min(300, n)
    fig, ax = plt.subplots(figsize=(7.4, 4.2))
    ax.bar(p["SKU排名"], p["销售额"], color="#C3D6E8", width=1.0, linewidth=0, label="单品销售额")
    ax.bar(p["SKU排名"].head(head_n), p["销售额"].head(head_n), color=C["blue3"],
           width=1.0, linewidth=0, label=f"销售额前 {head_n} 名")
    ax.set_ylabel("单品销售额（英镑）")
    ax.set_xlabel(f"商品按销售额排名（全部 {n:,} 个 SKU）")
    money_axis(ax)
    tidy(ax)
    ax2 = ax.twinx()
    ax2.plot(p["SKU排名"], p["累计占比"] * 100, color=C["orange"], lw=2.0, label="累计销售额占比")
    ax2.axhline(80, color=C["red"], ls="--", lw=1.1)
    ax2.axhline(95, color=C["green"], ls=":", lw=1.1)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("累计占比（%）")
    ax2.grid(False)
    na = int((p["ABC"] == "A").sum())
    nb = int((p["ABC"] == "B").sum())
    ax2.axvline(na, color=C["red"], ls="--", lw=0.9, alpha=0.85)
    ax2.axvline(na + nb, color=C["green"], ls=":", lw=0.9, alpha=0.85)
    ax2.annotate(f"A 类 {na:,} 个（{na / n:.1%}）贡献 80% 销售额", xy=(na, 80),
                 xytext=(na + n * 0.05, 58), fontsize=8, color=C["red"],
                 arrowprops=dict(arrowstyle="->", color=C["red"], lw=0.9))
    ax2.annotate(f"B 类止于第 {na + nb:,} 名（{(na + nb) / n:.1%}），累计达 95%",
                 xy=(na + nb, 95), xytext=(na + nb + n * 0.02, 88),
                 fontsize=8, color=C["green"],
                 arrowprops=dict(arrowstyle="->", color=C["green"], lw=0.9))
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="center right", bbox_to_anchor=(1.0, 0.62),
              frameon=False, fontsize=8.5)
    ax.set_title("商品销售额帕累托图与 ABC 分类", pad=12)
    source_note(fig)
    save(fig, "fig18_商品销售额帕累托图.png")


@guard("fig19 波士顿矩阵")
def fig19():
    d = T("t10_boston")
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    color_map = {"明星": C["green"], "问题": C["orange"], "现金牛": C["blue"], "瘦狗": C["grey"]}
    for q, g in d.groupby("象限"):
        ax.scatter(g["份额"] * 100, g["增速"], s=np.clip(g["客户数"] * 3.4, 40, 900),
                   color=color_map.get(q, C["grey"]), alpha=0.72, edgecolor="white", lw=1.2, label=q)
    res = json.loads((TABS / "results.json").read_text(encoding="utf-8"))
    cut_x = float(d["份额"].median() * 100)
    cut_y = float(res["boston"]["增速分界"])   # 与 4.2 节一致：取全量整体同比增速
    ax.axvline(cut_x, color=C["grey"], ls="--", lw=1)
    ax.axhline(cut_y, color=C["grey"], ls="--", lw=1)
    for _, r in d.iterrows():
        ax.annotate(str(r["国家"])[:14], (r["份额"] * 100, r["增速"]),
                    textcoords="offset points", xytext=(5, 5), fontsize=7.4, color="#333")
    ax.set_xlabel("市场相对份额（销售额占比 %）")
    ax.set_ylabel("同比增速（%）")
    ax.set_title(f"波士顿矩阵：份额 × 增速（分界 {cut_x:.1f}% / {cut_y:.1f}%）", pad=12)
    tidy(ax, "both")
    ax.legend(loc="upper right", frameon=False, fontsize=8, title="象限", title_fontsize=8)
    source_note(fig)
    save(fig, "fig19_波士顿矩阵四象限.png")


@guard("fig20 关联规则图")
def fig20():
    d = T("t11_rules").head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7.6, 4.3))
    colors = [C["orange"] if v == d["lift"].max() else C["blue"] for v in d["lift"]]
    ax.barh(range(len(d)), d["lift"], color=colors, height=0.62, edgecolor="white")
    ax.set_yticks(range(len(d)))
    ax.set_yticklabels([f"{a[:18]} → {b[:12]}" for a, b in zip(d["前项"], d["后项"])], fontsize=7.2)
    for i, (v, c, s) in enumerate(zip(d["lift"], d["confidence"], d["support"])):
        ax.text(v + 0.03, i, f"提升 {v:.2f} | 置信 {c:.0%} | 支持 {s:.1%}", va="center", fontsize=7.2)
    ax.axvline(1.0, color=C["grey"], ls="--", lw=0.9)
    ax.set_xlabel("提升度（Lift）")
    ax.set_xlim(0, d["lift"].max() * 1.42)
    ax.set_title("购物篮关联规则 Top10（提升度排序）", pad=12)
    tidy(ax, "x")
    source_note(fig)
    save(fig, "fig20_关联规则提升度.png")


@guard("fig21 预测与置信区间")
def fig21():
    d = T("t12_forecast").reset_index(drop=True)
    n = len(d)
    x = np.arange(n)
    hist = d["类型"] == "历史"
    bt = d["类型"] == "回测"
    fc = d["类型"] == "预测"

    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    # 置信区间分两段着色：回测段浅橙（用于检验区间覆盖率），预测段浅红（交付给业务）
    ax.fill_between(x[bt], d.loc[bt, "下界"], d.loc[bt, "上界"],
                    color=C["orange"], alpha=0.18, lw=0, label="回测段 95% 区间")
    ax.fill_between(x[fc], d.loc[fc, "下界"], d.loc[fc, "上界"],
                    color=C["red"], alpha=0.16, lw=0, label="预测段 95% 区间")
    ax.plot(x[hist], d.loc[hist, "实际值"], color=C["blue"], lw=2.0, marker="o", ms=3.2, label="实际销售额")
    # 回测段的实际值继续用同一根线画出，便于目视比对拟合优度
    ax.plot(x[bt], d.loc[bt, "实际值"], color=C["blue"], lw=2.0, marker="o", ms=3.2, ls=":", alpha=0.85)
    ax.plot(x[bt], d.loc[bt, "预测值"], color=C["orange"], lw=1.8, marker="s", ms=3.6,
            ls="--", label="回测预测")
    ax.plot(x[fc], d.loc[fc, "预测值"], color=C["red"], lw=2.0, marker="D", ms=3.8, label="未来预测")

    i_bt = int(np.argmax(bt.to_numpy()))
    i_fc = int(np.argmax(fc.to_numpy()))
    for i, txt in ((i_bt, "回测起点"), (i_fc, "预测起点")):
        ax.axvline(i - 0.5, color=C["grey"], ls=":", lw=1.1)
        ax.text(i - 0.42, ax.get_ylim()[1] * 0.97, txt, fontsize=7.6, color=C["grey"],
                va="top", ha="left", rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels([v if i % 2 == 0 else "" for i, v in enumerate(d["月份"])],
                       rotation=45, ha="right", fontsize=7.4)
    ax.set_xlim(-0.8, n - 0.2)
    ax.set_ylabel("销售额（英镑）")
    money_axis(ax)
    tidy(ax)
    ax.legend(loc="upper left", frameon=False, fontsize=7.8, ncol=2)
    ax.set_title("月度销售额 SARIMA 预测与 95% 置信区间", pad=12)
    source_note(fig)
    save(fig, "fig21_预测与置信区间.png")


@guard("fig22 回测误差图")
def fig22():
    res = json.loads((TABS / "results.json").read_text(encoding="utf-8"))
    d = pd.DataFrame(res["forecast"]["回测明细"])
    fig, ax = plt.subplots(figsize=(6.8, 3.7))
    x = np.arange(len(d))
    ax.bar(x - 0.19, d["实际"], width=0.38, color=C["blue"], label="实际值")
    ax.bar(x + 0.19, d["预测"], width=0.38, color=C["orange"], label="预测值")
    for i in range(len(d)):
        ax.text(x[i] - 0.19, d["实际"].iloc[i] * 1.01, f"{d['实际'].iloc[i]/1e4:.1f}", ha="center", fontsize=8)
        ax.text(x[i] + 0.19, d["预测"].iloc[i] * 1.01, f"{d['预测'].iloc[i]/1e4:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(d["月份"], fontsize=8.5)
    ax.set_ylabel("销售额（柱顶数字为万英镑）")
    ax.set_yticks([])
    tidy(ax, None)
    ax.legend(loc="upper left", frameon=False, ncol=2)
    ax.set_title(f"回测期拟合效果：MAPE {res['forecast']['MAPE']:.2f}%，RMSE {res['forecast']['RMSE']:,.0f} 英镑", pad=12)
    source_note(fig)
    save(fig, "fig22_回测误差对比.png")


def main():
    print("[04] 绘制模板复现类图表")
    for f in (fig01, fig02, fig03, fig04, fig05, fig06, fig07):
        f()
    for f in (fig08, fig09, fig10, fig11, fig12, fig13, fig14):
        f()
    print("[04] 绘制业务模型类图表")
    for f in (fig15, fig16, fig17, fig18, fig19, fig20, fig21, fig22):
        f()
    print(f"[04] 完成 {len(OK)} 张，失败 {len(FAIL)} 张")
    for n, e in FAIL:
        print(f"      !! {n}: {e}")


if __name__ == "__main__":
    main()
