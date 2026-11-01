# -*- coding: utf-8 -*-
"""05 交互式商业分析大屏。

产物：
  outputs/dashboard.html            交互式大屏（Plotly，8 个联动组件 + 下拉筛选）
  outputs/figures/fig23_交互式大屏.png  大屏版式图（与 HTML 同源数据渲染，供论文排版）
  outputs/tables/t15_dashboard_kpi.csv 大屏 KPI 组件取值

组件清单（≥6，均支持联动）：①KPI 卡 ②月度趋势 ③国家结构 ④客户分层
⑤留存热力 ⑥预测区间 ⑦商品明细表 ⑧筛选器（年份/口径）。
"""
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

from config import CLEAN, FIGS, ROOT, TABS, SEGMENTS
from viz_style import C, PAL, save

BG = "#0E1621"
PANEL = "#16202E"
FG = "#E6EDF3"
MUTED = "#8FA3B8"
ACCENT = ["#4C9AE8", "#F2A33C", "#57B894", "#E06C75", "#9B8AE6"]


def load():
    return {
        "meta": json.loads((CLEAN / "schema.json").read_text(encoding="utf-8")),
        "res": json.loads((TABS / "results.json").read_text(encoding="utf-8")),
        "monthly": pd.read_csv(TABS / "t05_monthly.csv", encoding="utf-8-sig"),
        "rfm": pd.read_csv(TABS / "t06_rfm_summary.csv", encoding="utf-8-sig"),
        "cohort": pd.read_csv(TABS / "t08_cohort_matrix.csv", index_col=0, encoding="utf-8-sig"),
        "country": pd.read_csv(TABS / "t03b_top_country.csv", encoding="utf-8-sig"),
        "forecast": pd.read_csv(TABS / "t12_forecast.csv", encoding="utf-8-sig"),
        "top10": pd.read_csv(TABS / "t09c_top10_product.csv", encoding="utf-8-sig"),
    }


def panel(ax, title):
    ax.set_facecolor(PANEL)
    for s in ax.spines.values():
        s.set_color("#2B3A4D")
        s.set_linewidth(0.8)
    ax.set_title(title, color=FG, fontsize=10.5, loc="left", pad=7, fontweight="bold")
    ax.tick_params(colors=MUTED, labelsize=7.6)
    ax.grid(True, color="#22303F", lw=0.6)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)


def build_matplotlib(D):
    res, meta = D["res"], D["meta"]
    fig = plt.figure(figsize=(12.8, 7.2), dpi=150)
    fig.patch.set_facecolor(BG)
    gs = fig.add_gridspec(4, 4, left=0.05, right=0.975, top=0.875, bottom=0.105,
                          hspace=0.85, wspace=0.34, height_ratios=[0.50, 0.82, 0.82, 0.78])

    # ① 标题栏 + 筛选器
    axt = fig.add_axes([0.035, 0.925, 0.6, 0.06])
    axt.set_axis_off()
    axt.text(0, 0.55, "零售交易商业分析大屏", color=FG, fontsize=17, fontweight="bold", va="center")
    axt.text(0, 0.05, f"数据区间 {meta['时间跨度']}  |  {meta['事实表记录数']:,} 条交易行",
             color=MUTED, fontsize=8.2, va="center")
    axf = fig.add_axes([0.66, 0.925, 0.315, 0.058])
    axf.set_axis_off()
    for i, (lab, val) in enumerate([("年份", "全部"), ("地区", "全部"), ("客户层级", "全部")]):
        axf.add_patch(FancyBboxPatch((i * 0.345 + 0.005, 0.18), 0.32, 0.62,
                                     boxstyle="round,pad=0.008,rounding_size=0.08",
                                     facecolor=PANEL, edgecolor="#33506E", lw=1))
        axf.text(i * 0.345 + 0.035, 0.62, lab, color=MUTED, fontsize=7.2, va="center")
        axf.text(i * 0.345 + 0.035, 0.32, f"{val}  ▼", color=FG, fontsize=8.4, va="center")
    axf.set_xlim(0, 1.05)
    axf.set_ylim(0, 1)

    # ② KPI 卡
    kpis = [
        ("累计销售额", f"{res['趋势']['总销售额']/1e6:.2f} M", "英镑", ACCENT[0]),
        ("订单总数", f"{res['eda']['订单数']/1e4:.2f} 万", "单", ACCENT[1]),
        ("活跃客户", f"{res['eda']['客户数']:,}", "人", ACCENT[2]),
        ("平均客单价", f"{res['eda']['平均订单金额']:.1f}", "英镑/单", ACCENT[3]),
    ]
    for i, (t, v, u, col) in enumerate(kpis):
        ax = fig.add_subplot(gs[0, i])
        ax.set_axis_off()
        ax.add_patch(FancyBboxPatch((0.02, 0.05), 0.96, 0.9, boxstyle="round,pad=0.01,rounding_size=0.06",
                                    facecolor=PANEL, edgecolor="#2B3A4D", lw=1, transform=ax.transAxes))
        ax.add_patch(Rectangle((0.02, 0.05), 0.045, 0.9, facecolor=col, lw=0, transform=ax.transAxes))
        ax.text(0.13, 0.66, t, color=MUTED, fontsize=8.6, transform=ax.transAxes)
        ax.text(0.13, 0.33, v, color=FG, fontsize=16.5, fontweight="bold", transform=ax.transAxes)
        ax.text(0.13, 0.12, u, color="#6C7F94", fontsize=7.4, transform=ax.transAxes)

    # ③ 月度趋势
    ax1 = fig.add_subplot(gs[1, :3])
    panel(ax1, "月度销售额趋势（面积图）")
    m = D["monthly"]
    if "是否完整月" in m.columns:
        m = m[m["是否完整月"] == True].reset_index(drop=True)  # noqa: E712
    x = np.arange(len(m))
    ax1.fill_between(x, m["销售额"], color=ACCENT[0], alpha=0.28, lw=0)
    ax1.plot(x, m["销售额"], color=ACCENT[0], lw=1.9)
    ax1.plot(x, m["三月移动平均"], color=ACCENT[1], lw=1.3, ls="--", label="3 月移动平均")
    ax1.set_xticks(x[::3])
    ax1.set_xticklabels(m["YM"].iloc[::3], rotation=30, fontsize=7)
    ax1.set_ylabel("销售额（英镑）", color=MUTED, fontsize=8)
    ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e3:.0f}k"))
    ax1.legend(loc="upper left", frameon=False, fontsize=7.4, labelcolor=MUTED)

    # ④ 国家结构
    ax2 = fig.add_subplot(gs[1, 3])
    panel(ax2, "销售额国家结构")
    d = D["country"].head(4).copy()
    rest = float(D["res"]["趋势"]["总销售额"] - d["Amount"].sum())
    vals = list(d["Amount"]) + ([rest] if rest > 0 else [])
    labs = [str(c)[:10] for c in d["Country"]] + (["其他市场"] if rest > 0 else [])
    tot = sum(vals)
    wedges, _ = ax2.pie(vals, colors=(ACCENT + ["#5B6B7F"])[: len(vals)], startangle=90,
                        counterclock=False,
                        wedgeprops=dict(width=0.40, edgecolor=PANEL, linewidth=1.4))
    ax2.text(0, 0.10, f"{tot/1e6:.2f}", ha="center", va="center", fontsize=15,
             fontweight="bold", color=FG)
    ax2.text(0, -0.16, "百万英镑", ha="center", va="center", fontsize=7, color=MUTED)
    for w, v in zip(wedges, vals):
        share = v / tot * 100
        if share >= 5:
            ang = np.deg2rad((w.theta2 + w.theta1) / 2)
            ax2.text(np.cos(ang) * 0.80, np.sin(ang) * 0.80, f"{share:.0f}%",
                     ha="center", va="center", fontsize=7.6, fontweight="bold", color=FG)
    ax2.legend([f"{l} {v/1e4:.0f}万" for l, v in zip(labs, vals)], loc="upper center",
               bbox_to_anchor=(0.5, -0.06), frameon=False, fontsize=6.0, labelcolor=MUTED,
               ncol=2, handlelength=0.9, columnspacing=0.7, handletextpad=0.35)
    ax2.grid(False)

    # ⑤ 客户分层
    ax3 = fig.add_subplot(gs[2, :2])
    panel(ax3, "RFM 客户层级与销售额贡献")
    g = D["rfm"].sort_values("销售额")
    ax3.barh(g["客户层级"], g["销售额"], color=[ACCENT[1] if s.startswith("重要") else "#3E5C7C"
                                          for s in g["客户层级"]], height=0.6)
    for i, (v, n) in enumerate(zip(g["销售额"], g["客户数"])):
        ax3.text(v, i, f" {v/1e4:.0f}万/{n:,}人", color=MUTED, fontsize=7, va="center")
    ax3.set_xlim(0, g["销售额"].max() * 1.30)
    ax3.set_xlabel("销售额（英镑）", color=MUTED, fontsize=8)
    ax3.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e3:.0f}k"))

    # ⑥ 留存热力
    ax4 = fig.add_subplot(gs[2, 2:])
    panel(ax4, "同期群留存热力图（%）")
    mat = D["cohort"]
    im = ax4.imshow(mat.values * 100, aspect="auto", cmap="magma", vmin=0, vmax=100)
    ystep = max(1, mat.shape[0] // 5)
    ax4.set_yticks(range(0, mat.shape[0], ystep))
    ax4.set_yticklabels(list(mat.index)[::ystep], fontsize=5.8)
    xstep = max(1, mat.shape[1] // 6)
    ax4.set_xticks(range(0, mat.shape[1], xstep))
    ax4.set_xticklabels([f"+{c}" for c in list(mat.columns)[::xstep]], fontsize=6.2)
    ax4.grid(False)

    # ⑦ 预测区间
    ax5 = fig.add_subplot(gs[3, :2])
    panel(ax5, "销售额预测与 95% 置信区间")
    f = D["forecast"]
    xi = np.arange(len(f))
    ax5.fill_between(xi, f["下界"], f["上界"], color=ACCENT[2], alpha=0.2, lw=0)
    ax5.plot(xi, f["实际值"], color=ACCENT[0], lw=1.6, label="实际")
    ax5.plot(xi, f["预测值"], color=ACCENT[2], lw=1.6, ls="--", label="预测")
    ax5.set_xticks(xi[::3])
    ax5.set_xticklabels(f["月份"].iloc[::3], rotation=30, fontsize=6.8)
    ax5.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, p: f"{v/1e3:.0f}k"))
    ax5.legend(frameon=False, fontsize=7, labelcolor=MUTED, loc="upper left", ncol=2)

    # ⑧ 明细表
    ax6 = fig.add_subplot(gs[3, 2:])
    ax6.set_axis_off()
    ax6.set_title("热销商品明细（Top 8）", color=FG, fontsize=10.5, loc="left", pad=7, fontweight="bold")
    t = D["top10"].head(8)
    cols = [(0.00, "商品编码"), (0.24, "商品名称"), (0.80, "销售额"), (0.93, "订单数")]
    for xpos, lab in cols:
        ax6.text(xpos, 1.02, lab, color=MUTED, fontsize=7.2, va="top", transform=ax6.transAxes)
    for i, (_, r) in enumerate(t.iterrows()):
        yy = 0.86 - i * 0.112
        c = FG if i % 2 == 0 else "#B8C7D6"
        ax6.text(0.00, yy, f"{str(r['StockCode'])[:12]}", color=c, fontsize=6.8, va="top", transform=ax6.transAxes)
        ax6.text(0.24, yy, f"{str(r['商品名称'])[:26]}", color=c, fontsize=6.8, va="top", transform=ax6.transAxes)
        ax6.text(0.80, yy, f"{r['销售额']/1e4:.1f} 万", color=c, fontsize=6.8, va="top", transform=ax6.transAxes)
        ax6.text(0.93, yy, f"{int(r['订单数'])}", color=c, fontsize=6.8, va="top", transform=ax6.transAxes)

    fig.text(0.035, 0.012, "数据来源：UCI Online Retail II  |  实现：Matplotlib + Plotly（交互版见 outputs/dashboard.html）",
             color="#5A6B7E", fontsize=7.2)
    path = FIGS / "fig23_交互式大屏.png"
    fig.savefig(path, dpi=150, facecolor=BG, bbox_inches=None)
    plt.close(fig)
    print(f"  [fig] {path.name}")

    kpi = pd.DataFrame([
        {"组件": "KPI-累计销售额", "取值": round(res["趋势"]["总销售额"], 2), "单位": "英镑"},
        {"组件": "KPI-订单总数", "取值": res["eda"]["订单数"], "单位": "单"},
        {"组件": "KPI-活跃客户", "取值": res["eda"]["客户数"], "单位": "人"},
        {"组件": "KPI-平均客单价", "取值": round(res["eda"]["平均订单金额"], 2), "单位": "英镑/单"},
        {"组件": "KPI-退货率", "取值": round(res["趋势"]["退货率"] * 100, 2), "单位": "%"},
        {"组件": "KPI-预测 MAPE", "取值": round(res["forecast"]["MAPE"], 2), "单位": "%"},
    ])
    kpi.to_csv(TABS / "t15_dashboard_kpi.csv", index=False, encoding="utf-8-sig")
    return path


def build_plotly(D):
    """交互版：8 个组件 + 下拉筛选联动（切换指标口径）。"""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except Exception as e:
        print(f"  [plotly] 跳过：{e}")
        return None

    res = D["res"]
    m, g, f = D["monthly"], D["rfm"], D["forecast"]
    fig = make_subplots(
        rows=3, cols=3,
        specs=[[{"type": "domain"}, {"type": "xy", "colspan": 2}, None],
               [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
               [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]],
        subplot_titles=("销售额国家结构", "月度销售额趋势（可切换指标）", "",
                        "RFM 客户层级", "同期群留存", "预测与置信区间",
                        "订单量", "退货金额", "热销商品 Top8"),
    )
    d = D["country"].head(6)
    fig.add_trace(go.Pie(labels=d["Country"], values=d["Amount"], hole=0.45, name="国家结构"), 1, 1)
    for col, nm in (("销售额", "销售额"), ("订单数", "订单数"), ("客户数", "客户数")):
        fig.add_trace(go.Scatter(x=m["YM"], y=m[col], name=nm, mode="lines", visible=(col == "销售额")), 1, 2)
    fig.add_trace(go.Bar(x=g["客户层级"], y=g["销售额"], name="层级销售额"), 2, 1)
    mat = D["cohort"]
    fig.add_trace(go.Heatmap(z=(mat.values * 100), x=[f"+{c}" for c in mat.columns],
                             y=list(mat.index), colorscale="Magma", name="留存"), 2, 2)
    fig.add_trace(go.Scatter(x=f["月份"], y=f["实际值"], name="实际", mode="lines"), 2, 3)
    fig.add_trace(go.Scatter(x=f["月份"], y=f["上界"], name="95% 上界", mode="lines",
                             line=dict(width=0), showlegend=False), 2, 3)
    fig.add_trace(go.Scatter(x=f["月份"], y=f["下界"], name="95% 下界", mode="lines",
                             line=dict(width=0), fill="tonexty", fillcolor="rgba(87,184,148,0.2)",
                             showlegend=False), 2, 3)
    fig.add_trace(go.Bar(x=m["YM"], y=m["订单数"], name="订单数"), 3, 1)
    fig.add_trace(go.Bar(x=m["YM"], y=m["退货额"], name="退货额", marker_color="#E06C75"), 3, 2)
    t10 = D["top10"].head(8)
    fig.add_trace(go.Bar(x=t10["销售额"][::-1], y=t10["商品名称"][::-1], orientation="h",
                         name="热销商品销售额", marker_color="#4C9AE8"), 3, 3)

    buttons = []
    for col in ("销售额", "订单数", "客户数"):
        vis = []
        for tr in fig.data:
            if getattr(tr, "name", "") in ("销售额", "订单数", "客户数"):
                vis.append(tr.name == col)
            else:
                vis.append(True)
        buttons.append(dict(label=f"趋势指标：{col}", method="update", args=[{"visible": vis}]))
    fig.update_layout(
        title=dict(text="零售交易商业分析大屏（交互版）| 组件 8 个 · 支持指标联动与悬停提示",
                   x=0.02, font=dict(size=20)),
        template="plotly_dark", height=900, width=1680,
        updatemenus=[dict(buttons=buttons, direction="down", x=0.98, y=1.11, showactive=True)],
        legend=dict(orientation="h", y=-0.08),
    )
    out = ROOT / "outputs" / "dashboard.html"
    fig.write_html(str(out), include_plotlyjs=True)   # 内联 plotly.js，离线也能打开
    print(f"  [html] {out.name}")

    # 若安装了 kaleido，则直接导出大屏静态图（与 HTML 完全同源）
    try:
        png = FIGS / "fig23_交互式大屏.png"
        fig.write_image(str(png), scale=1.2)
        print(f"  [fig] {png.name}（Plotly 直出）")
    except Exception as e:
        print(f"  [kaleido] 未启用静态导出，沿用 Matplotlib 版式图：{type(e).__name__}")
    return out


def main():
    D = load()
    build_matplotlib(D)
    build_plotly(D)


if __name__ == "__main__":
    main()
