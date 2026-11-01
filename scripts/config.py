# -*- coding: utf-8 -*-
"""全局配置：路径、随机种子、配色与术语约定。

本项目所有脚本共享该模块，保证目录结构、配色与随机种子一致。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
FIGS = ROOT / "outputs" / "figures"
TABS = ROOT / "outputs" / "tables"
DOCS = ROOT / "docs"
for _d in (RAW, CLEAN, FIGS, TABS, DOCS):
    _d.mkdir(parents=True, exist_ok=True)

# 全局随机种子：所有抽样 / 聚类 / 交叉验证均固定为该值，保证结果可复现
SEED = 42

# 数据源
DS_NAME = "UCI Online Retail II"
DS_URL = "https://archive.ics.uci.edu/dataset/502/online+retail+ii"

# 配色：主色板借鉴《Excel数据可视化——从图表到数据大屏》中的商务蓝—橙对比方案
COLORS = {
    "blue": "#2E5C8A",
    "blue2": "#4A7FB5",
    "blue3": "#8FB3D9",
    "orange": "#E8A33D",
    "orange2": "#F2C879",
    "red": "#C0504D",
    "green": "#5B9279",
    "grey": "#8C8C8C",
    "dark": "#1F2933",
    "bg": "#F5F7FA",
}
SEQ = ["#2E5C8A", "#E8A33D", "#5B9279", "#C0504D", "#8FB3D9", "#F2C879", "#7A6FA8", "#8C8C8C"]
SEGMENTS = [
    "重要价值客户", "重要保持客户", "重要发展客户", "重要挽留客户",
    "一般价值客户", "一般保持客户", "一般发展客户", "一般挽留客户",
]


def fmt_int(x):
    """整数千分位。"""
    return f"{int(round(x)):,}"


def fmt_money(x, unit="英镑"):
    if abs(x) >= 1e6:
        return f"{x/1e6:.2f} 百万{unit}"
    if abs(x) >= 1e4:
        return f"{x/1e4:.2f} 万{unit}"
    return f"{x:,.0f} {unit}"
