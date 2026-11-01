# -*- coding: utf-8 -*-
"""绘图公共样式：中文字体、配色、保存规范。

规范要求（见作业要求 2.3-4）：中文字体正常显示、坐标轴与单位标注完整、
配色协调统一、图片分辨率 ≥150dpi、统一命名 figNN_名称.png。
"""
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from config import COLORS, FIGS, SEQ

# ---------- 中文字体：Windows 自带黑体/雅黑，缺失时自动降级 ----------
_CJK = []
for name in ("Microsoft YaHei", "SimHei", "DengXian", "SimSun"):
    try:
        from matplotlib.font_manager import findfont, FontProperties

        path = findfont(FontProperties(family=name), fallback_to_default=False)
        _CJK.append(name)
    except Exception:
        continue

plt.rcParams["font.sans-serif"] = _CJK + ["DejaVu Sans"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 150
plt.rcParams["savefig.dpi"] = 150
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["savefig.facecolor"] = "white"
plt.rcParams["axes.edgecolor"] = "#9AA5B1"
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["axes.grid"] = False
plt.rcParams["grid.color"] = "#DCE3EA"
plt.rcParams["grid.linewidth"] = 0.7
plt.rcParams["font.size"] = 9.5
plt.rcParams["axes.titlesize"] = 12
plt.rcParams["axes.titleweight"] = "bold"
plt.rcParams["axes.labelsize"] = 9.5
plt.rcParams["xtick.labelsize"] = 9
plt.rcParams["ytick.labelsize"] = 9
plt.rcParams["legend.fontsize"] = 9
plt.rcParams["figure.facecolor"] = "white"

C = COLORS
PAL = SEQ


def k_formatter(x, pos=None):
    """纵轴用 k/M 缩写，避免刻度过长。"""
    if abs(x) >= 1e6:
        return f"{x/1e6:.1f}M"
    if abs(x) >= 1e3:
        return f"{x/1e3:.0f}k"
    return f"{x:.0f}"


def money_axis(ax, axis="y"):
    fmt = FuncFormatter(k_formatter)
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(fmt)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(fmt)


def tidy(ax, grid_axis="y", despine=True):
    """统一坐标轴外观：浅色网格 + 去掉多余边框。"""
    if grid_axis:
        ax.grid(True, axis=grid_axis, linestyle="-", linewidth=0.7, color="#DCE3EA", zorder=0)
        ax.set_axisbelow(True)
    if despine:
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)


def source_note(fig, text="数据来源：UCI Online Retail II（2009-12 至 2011-12）"):
    """统一在图表左下角标注数据来源，符合学术规范。"""
    fig.text(0.005, -0.02, text, fontsize=7.5, color="#6B7785", ha="left", va="top")


def save(fig, name):
    """按 figNN_名称.png 规范保存，返回路径。"""
    path = FIGS / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [fig] {path.name}")
    return path
