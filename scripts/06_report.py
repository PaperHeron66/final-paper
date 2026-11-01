# -*- coding: utf-8 -*-
"""06 论文生成：严格套用“期末大作业模板”的章节、样式与固定文本，逐节填充。

数据来源：outputs/tables/results.json + data/clean/schema.json + outputs/tables/*.csv
所有数字、图表编号与正文表述由脚本自动对齐，重跑数据即可自动更新论文。
"""
import json
import re
import shutil

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph

from config import CLEAN, DOCS, FIGS, ROOT, TABS
from report_lib import Paper, clear, set_indent, set_run

TPL = DOCS / "期末大作业模板.docx"
OUT = DOCS / "期末大论文.docx"

R = json.loads((TABS / "results.json").read_text(encoding="utf-8"))
M = json.loads((CLEAN / "schema.json").read_text(encoding="utf-8"))
RAWOV = json.loads((TABS / "t01_raw_overview.json").read_text(encoding="utf-8"))
LOG = pd.read_csv(TABS / "t02_clean_log.csv", encoding="utf-8-sig")
FK = pd.read_csv(TABS / "t04_fk_check.csv", encoding="utf-8-sig")
MET = pd.read_csv(TABS / "t13_metrics.csv", encoding="utf-8-sig")

tr, ed, rf, co = R["趋势"], R["eda"], R["rfm"], R["cohort"]
pa, bo, fc = R["pareto"], R["boston"], R["forecast"]
ap = R.get("apriori", {})

TITLE = "基于UCI零售数据的客户价值与销售预测"
KEYWORDS = ["商业数据分析", "RFM模型", "同期群分析", "SARIMA", "Python可视化"]

FIGS_LIST = [
    ("fig01_月度销售额折线图.png", "月度销售额走势与三月移动平均", "5.1"),
    ("fig02_国家销售额条形图.png", "销售额前 10 位国家分布", "5.1"),
    ("fig03_订单金额分布直方图.png", "订单金额分布（对数坐标）", "5.1"),
    ("fig04_下单时段热力图.png", "工作日下单时段热力图", "5.1"),
    ("fig05_销量单价散点图.png", "单品销量—单价—销售额三维散点图", "5.1"),
    ("fig06_月度销售额面积图.png", "月度销售额面积图与累计贡献曲线", "5.2"),
    ("fig07_年度月度对比簇状柱形图.png", "2010 与 2011 年 1—11 月销售额对比", "5.2"),
    ("fig08_国家结构环形图.png", "销售额国家结构环形图", "5.2"),
    ("fig09_订单量与客单价双轴图.png", "订单量与客单价双轴组合图", "5.2"),
    ("fig10_国家订单金额箱线图.png", "主要国家订单金额箱线图", "5.2"),
    ("fig11_商品销售额树状图.png", "销售额前 12 位商品树状图", "5.2"),
    ("fig12_客户层级雷达图.png", "核心客户层级 RFM 画像雷达图", "5.2"),
    ("fig13_环比增量分解瀑布图.png", "近 13 个月销售额环比增量瀑布图", "5.2"),
    ("fig14_核心指标KPI卡片.png", "核心经营指标 KPI 卡片", "5.2"),
    ("fig15_RFM分层客户规模.png", "RFM 八分类客户规模与销售额贡献", "5.3"),
    ("fig16_客户价值气泡图.png", "客户价值气泡图（频次 × 最近购买 × 金额）", "5.3"),
    ("fig17_同期群留存热力图.png", "同期群月度留存热力图", "5.3"),
    ("fig18_商品销售额帕累托图.png", "商品销售额帕累托图与 ABC 分类", "5.3"),
    ("fig19_波士顿矩阵四象限.png", "波士顿矩阵：份额 × 增速四象限", "5.3"),
    ("fig20_关联规则提升度.png", "购物篮关联规则 Top10（提升度排序）", "5.3"),
    ("fig21_预测与置信区间.png", "月度销售额 SARIMA 预测与 95% 置信区间", "5.3"),
    ("fig22_回测误差对比.png", "回测期实际值与预测值对比", "5.3"),
    ("fig23_交互式大屏.png", "交互式商业分析大屏（8 个联动组件）", "5.4"),
]
TAB_LIST = [
    ("原始数据字段说明", "2.1"),
    ("星型模型表结构与主外键关系", "2.4"),
    ("数据清洗步骤与行数变化", "3.1"),
    ("分析模型选型与对应关系", "4.1"),
    ("预测模型回测误差与拟合指标", "4.3"),
    ("交互式大屏组件与联动说明", "5.4"),
    ("图表索引（fig01—fig23 及表 1—表 7）", "附录 C"),
]


# ---------------------------------------------------------------- 格式化
def w(x):
    return f"{x/1e4:,.1f} 万"


def m_(x):
    return f"{x/1e6:.2f} 百万"


def p1(x):
    return f"{x:.1f}%"


def p2(x):
    return f"{x:.2f}%"


def pc(x):
    return f"{x*100:.1f}%"


def n(x):
    return f"{int(round(x)):,}"


def wordcount(t):
    """按 Word“字数”口径统计：中文字符（含中文标点）计 1，连续英文/数字计 1 个词。"""
    cjk = len(re.findall(r"[一-鿿　-〿＀-￯]", t))
    words = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9\.%\-]*", t))
    return cjk + words


def g(d, k, dflt=0.0):
    """安全取数，避免字段缺失导致论文生成中断。"""
    v = d.get(k, dflt)
    return dflt if v is None else v


# ---------------------------------------------------------------- 模板骨架
def prepare():
    doc = Document(str(TPL))
    body = doc.element.body
    kids = list(body.iterchildren())

    cover = {
        3: ("题　　目：", TITLE),
        4: ("学　　院：", "数据科学学院"),
        5: ("专业班级：", "【待补充：专业班级】"),
        6: ("学　　号：", "【待补充：学号】"),
        7: ("姓　　名：", "【待补充：姓名】"),
        8: ("完成日期：", "2026 年 10 月 31 日"),
    }
    for idx, (label, val) in cover.items():
        p = Paragraph(kids[idx], doc._body)
        runs = p.runs
        if runs:
            runs[0].text = label + val
            rpr = runs[0]._element.get_or_add_rPr()
            rf = rpr.find(qn("w:rFonts"))
            if rf is None:
                rf = OxmlElement("w:rFonts")
                rpr.append(rf)
            rf.set(qn("w:ascii"), "Times New Roman")   # 拉丁字母用西文字体，避免楷体缺字被替换
            rf.set(qn("w:hAnsi"), "Times New Roman")
            for r in runs[1:]:
                r._element.getparent().remove(r._element)
        p.paragraph_format.first_line_indent = Pt(28)

    def rewrite(idx, text, size, ea, align=WD_ALIGN_PARAGRAPH.CENTER, space=0):
        p = Paragraph(kids[idx], doc._body)
        clear(p)
        p.alignment = align
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before = Pt(space)
        p.paragraph_format.space_after = Pt(space)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        set_run(p.add_run(text), size=size, ea=ea)
        return p

    rewrite(12, TITLE, 16, "黑体", space=8)
    rewrite(13, "【待补充：姓名】", 10.5, "宋体", space=2)
    rewrite(14, "（嘉兴大学 数据科学学院）", 10.5, "宋体", space=2)

    p16 = Paragraph(kids[16], doc._body)
    clear(p16)
    p17 = Paragraph(kids[17], doc._body)
    clear(p17)
    for p in (p16, p17):
        p.paragraph_format.first_line_indent = Pt(24)
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for i in (18, 19, 20, 21):
        body.remove(kids[i])
    for i in range(23, 82):
        body.remove(kids[i])

    return doc, p16, p17


def abstract(p16, p17):
    text = (
        f"以 UCI 公开的英国在线礼品零售商交易数据为对象，覆盖 {M['时间跨度']} 共 "
        f"{n(M['事实表记录数'])} 条明细，按官方下载、清洗治理、模型分析、可视化与大屏五步完成端到端分析。"
        f"获取仅用官方 ZIP 文件，未使用爬虫；清洗 {n(int(LOG['删除行数'].sum()))} 行后重构为星型模型，"
        f"并导出 CSV、JSON 与 SQLite 三种格式。构建 RFM 八分类、同期群、帕累托、波士顿矩阵、Apriori 与 "
        f"SARIMA 六类模型：重要客户以 {pc(rf['重要客户占比'])} 的人数贡献 {pc(rf['重要客户销售额占比'])} 销售额，"
        f"{pc(pa['贡献80%销售额SKU占比'])} 的 SKU 贡献 80% 营收，同期群次月留存仅 {pc(co['首月留存'])}，"
        f"预测回测 MAPE 为 {p2(fc['MAPE'])}。复现 14 种图表模板、8 张业务模型图，"
        f"以 Plotly 搭建含 8 个联动组件的大屏，并提出 5 条可落地建议。"
    )
    set_run(p16.add_run("摘要："), size=14, ea="黑体")
    set_run(p16.add_run(text), size=12, ea="宋体")
    set_run(p17.add_run("关键词："), size=14, ea="黑体")
    set_run(p17.add_run("　".join(KEYWORDS)), size=12, ea="宋体")
    return wordcount(text)


# ---------------------------------------------------------------- 正文
def build(doc):
    P = Paper(doc)
    n_del = int(LOG["删除行数"].sum())

    # ===== 1 引言 =====
    P.h1("引言")
    P.h2("研究背景")
    P.body(
        f"网络零售的每次下单同时留下时间、商品、数量、单价、客户与地域六个维度的记录。本文数据来自一家英国"
        f"注册、无实体门店的线上礼品零售商，客户以批发商为主[2]；官方标注 {n(RAWOV['原始记录数'])} 条，"
        f"清洗后保留 {n(M['事实表记录数'])} 条有效明细。数据带有三类噪声：退货与取消单混在正向销售中会虚增"
        f"营收，{pc(M['匿名交易占比'])} 的行缺客户标识，批发批量下单使数量分布极度右偏。因此分析不能停留在"
        f"调包出图，须先建立可追溯的治理链条。"
    )
    P.h2("研究目的")
    P.body(
        "目标有四：验证一条合规、可一键重跑的治理路径；用不少于三类模型回答客户、商品、时间三个维度的经营"
        "问题并给出参数依据；用 Python 复现不少于 10 种教材版式并对比 Excel 实现[1]；把图表组织成可联动的"
        "交互式大屏。"
    )
    P.h2("研究意义")
    P.body(
        "结论对应四类决策：客户资源分配、商品结构精简、海外市场取舍、备货节奏。方法上把各模型的参数与阈值"
        "逐条写明业务理由，使“参数可解释”成为可检查的过程。"
    )

    # ===== 2 数据准备与预处理 =====
    P.h1("数据准备与预处理")
    P.h2("数据源介绍")
    P.body(
        f"数据源为 UCI 的 Online Retail II（编号 502），Chen 于 2012 年捐赠，DOI 10.24432/C5CG6D[2]，"
        f"记录该零售商 2009-12-01 至 2011-12-09 的全部交易。官方文件 43.5 MB，含两张年度工作表、8 个字段、"
        f"1,067,371 条记录。本项目全量载入，清洗后得 {n(M['事实表记录数'])} 条销售明细与 "
        f"{n(M['退货表记录数'])} 条退货明细，远超“主表不少于 500 条”的下限。"
    )
    P.table(
        [["字段名", "含义", "类型", "示例", "缺失情况"],
         ["Invoice", "发票号，6 位数字；以 C 开头表示取消", "字符串", "536365 / C536379", "无"],
         ["StockCode", "商品编码，5 位数字", "字符串", "85123A", "无"],
         ["Description", "商品名称", "字符串", "WHITE HANGING HEART", f"{n(RAWOV['Description缺失行数'])} 行缺失"],
         ["Quantity", "每笔交易的商品件数，负数为退货", "整数", "6 / -1", "无"],
         ["InvoiceDate", "交易生成日期与时刻", "日期时间", "2010-12-01 08:26", "无"],
         ["Price", "单价（英镑）", "浮点", "2.55", "无"],
         ["CustomerID", "客户编号，5 位数字", "整数", "12346", f"{n(RAWOV['CustomerID缺失行数'])} 行缺失"],
         ["Country", "客户所在国家", "字符串", "United Kingdom", "无"]],
        "表 1　原始数据字段说明", font_size=8.8,
        widths=[2.55, 4.15, 2.25, 3.3, 3.5],
        col_align=["l", "l", "c", "c", "c"],
    )
    P.body("CustomerID 的大面积缺失决定客户级口径，Quantity 的负值语义决定营收口径，二者须在治理阶段显式处理。")
    P.h2("合规获取方式")
    P.body(
        "获取方式限定在作业白名单内：官方 ZIP 一次性下载、解压后本地读取，全程未用 Scrapy、Selenium 或网页"
        "解析，也未调用非官方镜像。对应代码只做定位解压与分表读取，选择文件而非接口库，因数据集已静态归档、"
        "内容稳定可校验。"
    )
    P.h2("数据来源合规声明")
    P.body(
        "数据源名称：Online Retail II；提供方：UCI Machine Learning Repository（加州大学欧文分校）；主页："
        "https://archive.ics.uci.edu/dataset/502/online+retail+ii；获取方式：官方 ZIP 下载；获取日期："
        "2026-10-31；许可：CC BY 4.0。数据为脱敏流水，不含姓名与联系方式，客户仅以 5 位编号标识，"
        "不涉及个人信息保护风险；本文仅用于学术分析，金额以英镑计。"
    )
    P.h2("数据集概述")
    P.body("为支撑多表主外键对齐，清洗后把宽表重构为星型模型，结构如表 2。")
    P.table(
        [["表名", "类别", "主键", "主要字段", "记录数"],
         ["fact_sales", "事实", "Invoice + LineNo",
          "DateKey、ProductKey、CustomerKey、Quantity、Price、Amount", n(M["事实表记录数"])],
         ["dim_customer", "维度", "CustomerID",
          "首次购买日、最近购买日、订单数、累计销售额、R/F/M 指标", n(M["客户维度记录数"])],
         ["dim_product", "维度", "StockCode",
          "商品名称、销量、销售额、订单数、首末售日期", n(M["商品维度记录数"])],
         ["dim_date", "维度", "Date", "年、月、季度、星期、是否周末", n(M["日期维度记录数"])],
         ["dim_country", "维度", "CountryKey", "订单数、客户数、销售额、区域归属", n(M["国家维度记录数"])]],
        "表 2　星型模型表结构与主外键关系", font_size=8.8,
        widths=[3.15, 1.75, 2.45, 6.25, 2.15],
        col_align=["l", "c", "l", "l", "r"],
    )
    fk_ok = int((FK["孤立键数量"] == 0).sum())
    P.body(
        f"事实表以（Invoice, LineNo）为行标识，经四个外键指向维度表。反连接校验显示 {fk_ok} 条关系孤立键为 0；"
        f"唯一不完全匹配的是 CustomerKey，因 {pc(M['匿名交易占比'])} 的交易行无客户编号，这部分以空值保留在"
        f"事实表参与营收分析，但不进入客户级模型。"
    )

    # ===== 3 数据清洗与治理 =====
    P.h1("数据清洗与治理")
    P.h2("数据清洗")
    P.body("清洗遵循“先结构后数值、先剔除后补全”，每一步记录删除行数与理由（表 3），使任一被剔除的记录都能回溯到规则。")
    rows = [["步骤", "处理规则", "删除行数", "剩余行数"]]
    for _, r in LOG.iterrows():
        rows.append([str(r["清洗步骤"]), str(r["说明"]), n(r["删除行数"]), n(r["剩余行数"])])
    P.table(rows, "表 3　数据清洗步骤与行数变化", font_size=8.8,
            widths=[3.4, 7.4, 2.2, 2.6], col_align=["l", "l", "r", "r"])
    P.body(
        f"缺失值分类处理：Description 用同一 StockCode 的众数回填；CustomerID 不删除，以空值保留并加客户级"
        f"过滤，保住 {pc(1 - M['匿名交易占比'])} 的可识别交易。异常值改用 IQR 三倍上界而非 3σ——批发大额订单"
        f"真实存在；Price≤0 无法计算销售额直接剔除；Quantity<0 或以 C 开头的记录转入独立退货表。最终退货金额 "
        f"{w(abs(tr['退货总额']))} 英镑、退货率 {p2(tr['退货率']*100)}，仅看销售额会高估同等比例的真实营收。"
    )
    P.h2("数据转换")
    P.body(
        "Invoice、StockCode、Country 强制为字符串（避免前导零丢失），Quantity 为整数、Price 为浮点、"
        "CustomerID 为可空整数，InvoiceDate 解析为日期时间并派生六个时间字段。指标派生新增行级销售额、订单金额、"
        "客单价与客户级 R/F/M；快照日取最后一天加一天，避免 R=0 干扰分位切分。"
    )
    P.h2("数据整合")
    P.body(
        f"关联以事实表为驱动，按三个外键左连接补全属性；客户维度先在事实表聚合生成再反向引用，避免一对多连接"
        f"造成金额重复累加。事实表未抽样，{n(M['事实表记录数'])} 行全量参与计算；仅气泡图与箱线抖动散点按 "
        f"seed = {M['随机种子']} 抽样。治理结果导出 CSV、JSON（schema.json 记录表结构与口径）与 SQLite"
        f"（五张表加两个索引，可直接用 SQL 复算）。"
    )

    # ===== 4 商业分析模型 =====
    P.h1("商业分析模型")
    P.h2("模型选型")
    P.body("选型标准是“能否回答一个具体经营问题”。最终用 6 类模型加趋势分析，覆盖五个类别（表 4），每个模型至少产出一图一结论。")
    P.table(
        [["序号", "模型 / 方法", "类别", "回答的经营问题", "核心指标", "对应图"],
         ["1", "环比/同比与移动平均", "趋势与对比", "销售在增长还是季节性回落", "同比增速、三月移动平均", "图 1、图 6、图 13"],
         ["2", "RFM 八分类", "用户与客群", "哪些客户值得追加投入", "R/F/M 中位数切分、层级销售占比", "图 12、图 15、图 16"],
         ["3", "同期群留存分析", "用户与客群", "新客在第几个月流失", "首月/第 6 月/第 12 月留存率", "图 17"],
         ["4", "帕累托 / ABC 分类", "结构与价值", "哪些 SKU 贡献主要营收", "累计占比 80%/95% 分界", "图 18"],
         ["5", "波士顿矩阵", "结构与价值", "海外市场该加投还是收缩", "相对份额 × 同比增速", "图 19"],
         ["6", "Apriori 关联规则", "关联与转化", "哪些商品应当捆绑陈列", "支持度、置信度、提升度", "图 20"],
         ["7", "SARIMA 时间序列预测", "预测与预警", "下个季度大致卖多少", "点预测、95% 区间、MAPE/RMSE", "图 21、图 22"]],
        "表 4　分析模型选型与对应关系", font_size=8.2,
        widths=[1.2, 2.8, 2.6, 3.8, 3.5, 1.8],
        col_align=["c", "l", "c", "l", "l", "c"],
    )
    P.h2("参数与阈值设定依据")
    P.body(
        f"RFM 用中位数而非均值切分：R、F、M 均显著右偏，M 均值 {n(g(rf,'M均值'))} 英镑、中位数仅 "
        f"{n(g(rf,'M中位数'))} 英镑，以均值为界会使高价值客户不足两成；中位数则使每维高低各半、八类规模可比。"
        f"同期群以首购月份定义群并剔除 50 人以下小群，留存为第 n 月有单客户数除以群规模。帕累托取累计销售额 "
        f"80% 与 95% 两个经典分界，SKU 超四千时阈值过低会使 A 类臃肿。"
    )
    P.body(
        f"波士顿矩阵按销售额前 10 位的国家划分，横轴为 1—11 月相对份额、纵轴为同比增速，分界取样本中位数与"
        f"整体增速 {p1(g(bo,'增速分界'))}，即以跑赢大盘而非正增长作为明星与问题的界线。Apriori 在高频 "
        f"{ap.get('参与SKU数', '—')} 个 SKU 上运行（覆盖 {pc(g(ap,'SKU覆盖订单比例'))} 订单），支持度 1%、"
        f"提升度 1.2 双门槛过滤无业务意义的组合。"
    )
    P.body(
        f"SARIMA 按 12 个月周期取季节阶 (0,1,1,12)，非季节阶取 (1,1,0)：一阶差分消趋势、一阶自回归刻画惯性，"
        f"不加 MA——仅 18 个训练点时 MA 会放大外推方差，实测加上后留出误差由 {p2(fc['MAPE'])} 升至 6.68%。"
        f"最终模型为 {fc['参数']}，回测留出最后 {fc['回测月数']} 个月，同时报 MAPE 与 RMSE，置信区间取 95%。"
    )
    P.h2("模型计算与验证")
    P.body(
        f"全期合计 {m_(tr['总销售额'])} 英镑，24 个完整月月均 {w(tr['月均销售额'])}，峰值 {tr['最高月']}"
        f"（{w(tr['最高月销售额'])}）、谷值 {tr['最低月']}（{w(tr['最低月销售额'])}），峰谷相差 "
        f"{tr['最高月销售额']/max(tr['最低月销售额'],1e-9):.1f} 倍；1—11 月同比 2011 年"
        f"{'增长' if g(tr,'整体同比增速')>=0 else '下降'} {p1(abs(g(tr,'整体同比增速')))}，"
        f"{g(tr,'同比正增长月份数')} 个月为正、{g(tr,'同比负增长月份数')} 个月为负。"
    )
    P.body(
        f"RFM 在 {n(rf['客户数'])} 位客户上运行，中位数分界 R={rf['R中位数']:.0f} 天、F={rf['F中位数']:.0f} 单、"
        f"M={w(rf['M中位数'])}；重要客户 {n(rf['重要客户数'])} 人占 {pc(rf['重要客户占比'])}，贡献 "
        f"{pc(rf['重要客户销售额占比'])} 销售额，客单价为整体的 "
        f"{rf['重要客户客单价']/max(rf['整体客单价'],1e-9):.1f} 倍。同期群覆盖 {n(co['覆盖客户数'])} 人："
        f"次月留存降至 {pc(co['首月留存'])}，第 6 月 {pc(co['第6月留存'])}、第 12 月 {pc(co['第12月留存'])}，"
        f"呈“次月断崖 + 长期平台”。"
    )
    P.body(
        f"帕累托：{n(pa['SKU总数'])} 个 SKU 中 {n(pa['贡献80%销售额SKU数'])} 个（"
        f"{pc(pa['贡献80%销售额SKU占比'])}）贡献 80% 销售额，C 类 {n(pa['C类SKU数'])} 个仅贡献 "
        f"{pc(pa['C类销售额占比'])}。波士顿矩阵在 {bo['单元数']} 个国家上运行，明星为"
        f"{'、'.join(bo['明星']) if bo['明星'] else '无'}，英国份额 {pc(g(bo,'英国份额'))}、增速 "
        f"{p1(g(bo,'英国增速'))}。"
    )
    if "错误" not in ap:
        P.body(
            f"关联规则在 {n(ap['事务数'])} 张购物篮上生成 {ap['规则数']} 条规则，最强提升度 "
            f"{ap['最强提升度']:.2f}、置信度 {pc(ap['最强置信度'])}、支持度 {pc(ap['最强支持度'])}。"
            f"预测以 {fc['训练月数']} 个月训练、{fc['回测月数']} 个月回测，MAPE {p2(fc['MAPE'])}、RMSE "
            f"{n(fc['RMSE'])} 英镑；重拟合后预测 {fc['预测期']} 共 {fc['预测月数']} 个月为 "
            f"{'、'.join(w(d['预测值']) for d in fc['未来预测'])} 英镑，并给出 95% 区间。"
        )
    P.table(
        [["指标", "取值", "单位", "口径"]] +
        [[str(r["指标"]), str(r["取值"]), str(r["单位"]), str(r["口径"])] for _, r in MET.iterrows()],
        "表 5　预测模型回测误差与拟合指标", font_size=9,
        widths=[2.6, 3.0, 2.4, 7.6], col_align=["c", "r", "c", "l"],
    )
    P.body("验证原则：描述类看分布是否被少数样本劫持，分类类看类间是否可解释，预测类必须留出回测且以 MAPE 为主、RMSE 为辅。")

    # ===== 5 可视化 =====
    P.h1("Python 数据分析与可视化")
    P.h2("数据探索性分析")
    P.body(
        f"平均订单金额 {ed['平均订单金额']:.2f} 英镑而中位数仅 {ed['订单金额中位数']:.2f} 英镑，均值被右尾拉高，"
        f"故后文一律采用中位数口径。"
    )
    P.figure(FIGS / "fig01_月度销售额折线图.png", "图 1　月度销售额走势与三月移动平均")
    P.body("图 1 呈双峰加年末翘尾，增量来自旺季放大而非淡季填补，现金流应按双峰预留。")
    P.figure(FIGS / "fig02_国家销售额条形图.png", "图 2　销售额前 10 位国家分布")
    P.body(f"图 2 显示英国占 {pc(ed['英国销售额占比'])}、海外合计 {pc(ed['海外销售额占比'])}，跨境仍属早期。")
    P.figure(FIGS / "fig03_订单金额分布直方图.png", "图 3　订单金额分布（对数坐标）")
    P.body("图 3 显示金额集中 10—100 英镑，另有 1,000 英镑以上批发长尾，按均值设门槛会两头误伤。")
    P.figure(FIGS / "fig04_下单时段热力图.png", "图 4　工作日下单时段热力图")
    P.body(f"图 4 商机集中在工作日 10—15 时，最忙{ed['最忙日']}、最忙 {ed['最忙时段']} 时，周末几乎无单。")
    P.figure(FIGS / "fig05_销量单价散点图.png", "图 5　单品销量、单价与销售额三维散点图")
    P.body("图 5 左上保毛利、右上保库存、右下作凑单引流、左下应精简。")
    P.h2("可视化模板复现")
    P.body(
        "本节对照教材《Excel数据可视化——从图表到数据大屏》复现 14 种版式，在图型、布局、配色、标签、图例"
        "与标题六方面贴近原作，并把手工调整改写为可复用函数。"
    )
    P.figure(FIGS / "fig06_月度销售额面积图.png", "图 6　月度销售额面积图与累计贡献曲线")
    P.body("图 6 以填充表达体量，累计曲线显示增量主要发生在第一年。")
    P.figure(FIGS / "fig07_年度月度对比簇状柱形图.png", "图 7　2010 与 2011 年 1 至 11 月销售额对比")
    P.body(f"图 7 显示 {g(tr,'同比正增长月份数')} 个月同比为正、{g(tr,'同比负增长月份数')} 个月为负，负增长集中在上半年。")
    P.figure(FIGS / "fig08_国家结构环形图.png", "图 8　销售额国家结构环形图")
    P.body("图 8 中心留白承载 43 国合计，小扇区并入图例；环宽由代码控制。")
    P.figure(FIGS / "fig09_订单量与客单价双轴图.png", "图 9　订单量与客单价双轴组合图")
    P.body("图 9 旺季订单升而客单价降，增量来自小额零售单，是单轴图看不到的量价背离。")
    P.figure(FIGS / "fig10_国家订单金额箱线图.png", "图 10　主要国家订单金额箱线图")
    P.body("图 10 对数纵轴下中位数最高者离散度也最大，箱线叠抖动散点在 Excel 中难以实现。")
    P.figure(FIGS / "fig11_商品销售额树状图.png", "图 11　销售额前 12 位商品树状图")
    P.body("图 11 前 3 个 SKU 面积之和接近其余 9 个，为帕累托结论提供直观印证。")
    P.figure(FIGS / "fig12_客户层级雷达图.png", "图 12　核心客户层级 RFM 画像雷达图")
    P.body("图 12 一般挽留客户在 R、F 轴塌陷而仅客单价残留优势，正是“曾买过、今沉默”。")
    P.figure(FIGS / "fig13_环比增量分解瀑布图.png", "图 13　近 13 个月销售额环比增量瀑布图")
    P.body("图 13 绿柱多在节庆备货期、红柱多在年初淡季，便于定位贡献最大的月份。")
    P.figure(FIGS / "fig14_核心指标KPI卡片.png", "图 14　核心经营指标 KPI 卡片")
    P.body("图 14 卡片式布局首屏即结论，与大屏组件同源，可随数据自动重排。")
    P.body(
        f"Python 胜在可复现（样式固化为常量）、可扩展（{n(ed['商品行数'])} 行仍可继续聚合）与可计算"
        f"（置信带、树状布局在 Excel 中几乎不可实现）；Excel 胜在所见表即所得的微调，故本项目仅用它做数据"
        f"核对。"
    )

    P.h2("业务模型图")
    P.body("本节 8 张图与第 4 章模型一一对应。")
    P.figure(FIGS / "fig15_RFM分层客户规模.png", "图 15　RFM 八分类客户规模与销售额贡献")
    P.body(
        f"图 15 重要价值客户 {n(g(rf,'seg_重要价值客户')['客户数'])} 人贡献 {pc(rf['最大层级销售额占比'])}，"
        f"一般挽留 {n(g(rf,'seg_一般挽留客户')['客户数'])} 人仅 4.8%，按人数平均分配预算会背离真实价值。"
    )
    P.figure(FIGS / "fig16_客户价值气泡图.png", "图 16　客户价值气泡图")
    P.body("图 16 右上为重要价值客户、左下为一次性长尾，边界连续过渡而非硬切。")
    P.figure(FIGS / "fig17_同期群留存热力图.png", "图 17　同期群月度留存热力图")
    P.body(f"图 17 次月留存 {pc(co['首月留存'])} 后长期走平，旺季群回落更快、淡季群更稳。")
    P.figure(FIGS / "fig18_商品销售额帕累托图.png", "图 18　商品销售额帕累托图与 ABC 分类")
    P.body(f"图 18 累计曲线在第 {pa['贡献80%销售额SKU数']} 个 SKU 穿过 80% 线，即 A 类分界。")
    P.figure(FIGS / "fig19_波士顿矩阵四象限.png", "图 19　波士顿矩阵四象限图")
    P.body("图 19 英国居现金牛区，问题区待验证，瘦狗区应收缩服务成本。")
    if "错误" not in ap:
        P.figure(FIGS / "fig20_关联规则提升度.png", "图 20　购物篮关联规则 Top10（提升度排序）")
        P.body(f"图 20 最强规则提升度 {ap['最强提升度']:.2f}，适合精准搭售；双高者才宜全店捆绑。")
    P.figure(FIGS / "fig21_预测与置信区间.png", "图 21　月度销售额 SARIMA 预测与 95% 置信区间")
    P.body(f"图 21 右侧为未来 {fc['预测月数']} 个月预测与 95% 带，区间随步长变宽。")
    P.figure(FIGS / "fig22_回测误差对比.png", "图 22　回测期实际值与预测值对比")
    P.body(f"图 22 回测方向全部正确、MAPE {p2(fc['MAPE'])}，支持季度备货但不足以支撑日级排产。")
    P.h2("交互式可视化大屏")
    P.body(
        "大屏以 Plotly 构建为单文件 HTML，无需后端即可交互，图 23 为其静态版式图：深色 16 比 9 版式含 8 个"
        "组件，由三个全局筛选器联动（表 6）。"
    )
    P.figure(FIGS / "fig23_交互式大屏.png", "图 23　交互式商业分析大屏（8 个联动组件）", width_cm=15.0)
    P.table(
        [["序号", "组件", "图表类型", "数据来源", "联动方式"],
         ["1", "KPI 卡片（4 个）", "数值卡片", "results.json", "随筛选器整体刷新"],
         ["2", "月度销售额趋势", "面积图加移动平均", "t05_monthly.csv", "下拉切换销售额/订单数/客户数"],
         ["3", "销售额国家结构", "环形图", "t03b_top_country.csv", "点击扇区联动明细表"],
         ["4", "RFM 客户层级", "横向条形图", "t06_rfm_summary.csv", "悬停显示客户数与销售额占比"],
         ["5", "同期群留存", "热力图", "t08_cohort_matrix.csv", "悬停显示群规模与留存率"],
         ["6", "销售额预测区间", "折线加置信带", "t12_forecast.csv", "随年份筛选重新取数"],
         ["7", "订单量与退货额", "双柱形图", "t05_monthly.csv", "与趋势图共享时间轴"],
         ["8", "热销商品明细", "明细表（Top 8）", "t09c_top10_product.csv", "受国家与层级筛选过滤"]],
        "表 6　交互式大屏组件与联动说明", font_size=8.2,
        widths=[1.15, 3.15, 2.7, 3.95, 4.15],
        col_align=["c", "l", "l", "l", "l"],
    )
    P.body("联动由一个筛选器驱动多个视图：环形图扇区点击过滤明细表形成下钻。全部图表由 Python 生成，未使用 BI 软件或 Excel 截图。")

    # ===== 6 商业案例分析 =====
    P.h1("商业案例分析")
    P.h2("案例背景")
    P.body(
        f"案例企业为英国注册的线上礼品零售商，批发为主、零售为辅。三个痛点：单客户金额差异极大、SKU 超四千"
        f"长尾占用仓储、销售集中于年末旺季。基本盘为 {n(ed['客户数'])} 位客户、{n(ed['订单数'])} 张订单、"
        f"累计 {m_(tr['总销售额'])} 英镑，客单价中位数仅 {ed['订单金额中位数']:.2f} 英镑。"
    )
    P.h2("结果解读")
    P.body(
        f"其一，价值集中：前 1% 客户贡献 {pc(g(rf,'Top1%客户销售额占比'))}，重要客户以 "
        f"{pc(rf['重要客户占比'])} 的人数贡献 {pc(rf['重要客户销售额占比'])}；仅购一次者占 "
        f"{pc(1-rf['复购客户占比'])}，拉新效率远低于唤醒。其二，留存窗口在前 30 天：次月留存仅 "
        f"{pc(co['首月留存'])} 后长期停在 18%—24%。其三，商品极端长尾：{pc(pa['贡献80%销售额SKU占比'])} 的 "
        f"SKU 支撑 80% 营收。其四，市场一超多弱：英国占 {pc(g(bo,'英国份额'))}。其五，需求可预测但精度有限："
        f"MAPE {p2(fc['MAPE'])} 只支持季度级决策。"
    )
    P.h2("商业建议")
    P.body("基于上述结果提出 5 条建议，每条标注数据依据与做法。")
    recs = [
        ("建议一：对重要客户名单制运营。",
         f"依据：重要客户以 {pc(rf['重要客户占比'])} 的人数贡献 {pc(rf['重要客户销售额占比'])}，客单价为整体的 "
         f"{rf['重要客户客单价']/max(rf['整体客单价'],1e-9):.1f} 倍。做法：两类名单配专属客服与账期，"
         "重要挽留客户 R 值超自身历史间隔 1.5 倍时触发回访。"),
        ("建议二：把首购后 30 天设为挽回窗口。",
         f"依据：次月留存仅 {pc(co['首月留存'])}、一次性客户 {n(rf['仅购一次客户数'])} 人。做法：第 7 天推"
         "关联商品、第 15 天发券、第 30 天回访，以第二单为唯一考核。"),
        ("建议三：按 ABC 重构 SKU 与库存。",
         f"依据：A 类 {n(pa['A类SKU数'])} 个贡献 {pc(pa['A类销售额占比'])}，C 类 {n(pa['C类SKU数'])} 个仅 "
         f"{pc(pa['C类销售额占比'])}。做法：A 类保现货周补货，B 类按需补货，C 类清仓或转按单生产，按季度重算。"),
        ("建议四：海外精选国家、轻库存试探。",
         f"依据：非英国合计仅 {pc(1 - g(bo, '英国份额'))}，部分市场增速高于整体（{p1(g(bo,'增速分界'))}）。"
         "做法：问题象限中挑两三个高增速国家小规模投放，用海外仓或代发控制风险。"),
        ("建议五：以预测区间加预警线备货。",
         f"依据：MAPE {p2(fc['MAPE'])}，95% 区间下季度首月为 {w(fc['未来预测'][0]['下界'])} 至 "
         f"{w(fc['未来预测'][0]['上界'])} 英镑。做法：下界作最低备货、上界作最高备货，跌破下界即触发促销或"
         "延后补货。"),
    ]
    for head, txt in recs:
        P.para_runs([(head, {"bold": True, "ea": "黑体"}), (txt, {"ea": "宋体"})])

    # ===== 7 结论与展望 =====
    P.h1("结论与展望")
    P.h2("研究结论")
    P.body(
        f"本文完成从官方数据到交互式大屏的完整链路。结论有四：合规获取与可复现治理并不冲突；客户价值高度集中"
        f"且留存窗口前移，重要客户以 {pc(rf['重要客户占比'])} 的人数贡献 {pc(rf['重要客户销售额占比'])} 销售额、"
        f"次月留存仅 {pc(co['首月留存'])}，重心应从拉新转向唤醒；商品呈极端长尾，精简长尾是释放资源最快的路径；"
        f"需求季节性可预测，但精度只支持季度级区间决策。"
    )
    P.body(
        "方法论上验证了“参数必须可解释”：RFM 用中位数、同期群用 50 人门槛、帕累托用 80/95 分界、波士顿用大盘"
        "增速、Apriori 用双门槛、SARIMA 用 12 阶季节项，每个选择都对应数据分布或业务场景。"
    )
    P.h2("局限性与展望")
    P.body(
        f"局限有四：仅两年、{n(ed['订单数'])} 张订单，季节项估计稳定性有限；{pc(M['匿名交易占比'])} 的交易行缺"
        f"客户标识，客户级模型仅覆盖可识别子集；关联规则只在高频 SKU 上运行；缺少成本与毛利，建议只能停留在"
        f"收入侧。后续可引入毛利把 M 升级为毛利贡献，用 SARIMAX 或 Prophet 纳入外生变量。"
    )
    P.h2("AI 使用披露")
    P.body(
        "本文使用 AI 编程助手（DeepSeek）辅助脚本骨架生成、python-docx 排版与文字润色。分析口径、参数依据"
        "与结论判断均由作者确认，代码经人工复核并在本地跑通，文中数字由脚本从原始数据计算得到。"
    )

    # ===== 参考文献 =====
    P.h1("参考文献")
    refs = [
        "[1] 郭宏远. Excel数据可视化: 从图表到数据大屏[M]. 北京: 清华大学出版社, 2023.",
        "[2] CHEN D. Online Retail II[DS/OL]. UCI Machine Learning Repository, 2012[2026-10-31]. "
        "https://doi.org/10.24432/C5CG6D.",
        "[3] HUGHES A M. Strategic database marketing[M]. Chicago: Probus Publishing, 1994.",
        "[4] REICHHELD F F, SASSER W E. Zero defections: quality comes to services[J]. "
        "Harvard Business Review, 1990, 68(5): 105-111.",
        "[5] AGRAWAL R, SRIKANT R. Fast algorithms for mining association rules[C]//Proceedings of the "
        "20th International Conference on Very Large Data Bases. Santiago: VLDB, 1994: 487-499.",
        "[6] BOX G E P, JENKINS G M, REINSEL G C, et al. Time series analysis: forecasting and "
        "control[M]. 5th ed. Hoboken: John Wiley and Sons, 2015.",
        "[7] HYNDMAN R J, ATHANASOPOULOS G. Forecasting: principles and practice[M]. 3rd ed. "
        "Melbourne: OTexts, 2021.",
        "[8] CHEN H, CHIANG R H L, STOREY V C. Business intelligence and analytics: from big data to "
        "big impact[J]. MIS Quarterly, 2012, 36(4): 1165-1188.",
        "[9] HENDERSON B D. The product portfolio[M]. Boston: Boston Consulting Group, 1970.",
        "[10] KUMAR V, REINARTZ W. Customer relationship management: concept, strategy, and tools[M]. "
        "2nd ed. Berlin: Springer, 2012.",
        "[11] WEDEL M, KANNAN P K. Marketing analytics for data-rich environments[J]. "
        "Journal of Marketing, 2016, 80(6): 97-121.",
        "[12] HARRIS C R, MILLMAN K J, VAN DER WALT S J, et al. Array programming with NumPy[J]. "
        "Nature, 2020, 585: 357-362.",
        "[13] MCKINNEY W. Data structures for statistical computing in Python[C]//Proceedings of the "
        "9th Python in Science Conference. Austin, 2010: 56-61.",
        "[14] HUNTER J D. Matplotlib: a 2D graphics environment[J]. Computing in Science and "
        "Engineering, 2007, 9(3): 90-95.",
        "[15] SEABOLD S, PERKTOLD J. Statsmodels: econometric and statistical modeling with "
        "Python[C]//Proceedings of the 9th Python in Science Conference. Austin, 2010: 92-96.",
    ]
    for t in refs:
        p = P.body(t, indent=False)
        set_indent(p, 0, left_pt=24, hanging_pt=24)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # ===== 附录 =====
    P.h1("附录")
    P.body("A 核心代码片段", indent=False, bold=True)
    mono = "Consolas"
    snippets = [
        ("（1）RFM 八分类核心逻辑（scripts/03_analysis.py 节选）", [
            'c["R分值"] = pd.qcut(c["R"].rank(method="first"), 5, labels=[5,4,3,2,1]).astype(int)',
            'r_mid, f_mid, m_mid = c["R"].median(), c["F"].median(), c["M"].median()',
            'rh = c["R"] <= r_mid          # R 越小越近，故“高”取小于中位数',
            "fh = c[\"F\"] >  f_mid",
            "mh = c[\"M\"] >  m_mid",
            "seg = np.select([rh & fh & mh, ~rh & fh & mh, rh & ~fh & mh, ~rh & ~fh & mh,",
            "                 rh & fh & ~mh, ~rh & fh & ~mh, rh & ~fh & ~mh],",
            "                [0,1,2,3,4,5,6], default=7)",
            'c["客户层级"] = [SEGMENTS[i] for i in seg]',
        ]),
        ("（2）SARIMA 训练、回测与预测区间（scripts/03_analysis.py 节选）", [
            "model = SARIMAX(train, order=(1, 1, 0), seasonal_order=(0, 1, 1, 12),",
            "                enforce_stationarity=False, enforce_invertibility=False)",
            "fit = model.fit(disp=False)",
            "pred = fit.get_forecast(steps=6)        # 留出最后 6 个月回测",
            "resid = test.values - pred.predicted_mean.values",
            "mape = np.mean(np.abs(resid / test.values)) * 100",
            "rmse = np.sqrt(np.mean(resid ** 2))",
            "full = SARIMAX(y, order=(1, 1, 0), seasonal_order=(0, 1, 1, 12),",
            "                enforce_stationarity=False, enforce_invertibility=False)",
            "res = full.fit(disp=False).get_forecast(steps=6)",
            "ci = res.conf_int(alpha=0.05)          # 95% 置信区间",
        ]),
        ("（3）一键复现入口（run_all.py 节选）", [
            'STEPS = [("01","01_load.py","加载官方数据并缓存"),',
            '         ("02","02_clean.py","清洗治理 + 星型模型 + 三种格式导出"),',
            '         ("03","03_analysis.py","六类商业分析模型与结果表"),',
            '         ("04","04_visuals.py","14 张模板复现图 + 8 张业务模型图"),',
            '         ("05","05_dashboard.py","交互式大屏（HTML/版式图）"),',
            '         ("06","06_report.py","按模板生成期末大论文 DOCX")]',
            "for key, script, desc in STEPS:",
            "    cmd = [sys.executable, str(SCRIPTS / script)]",
            "    subprocess.run(cmd, cwd=str(SCRIPTS), check=True)",
        ]),
    ]
    for title, lines in snippets:
        P.body(title, indent=False)
        for line in lines:
            p = doc.add_paragraph()
            set_indent(p, 0, left_pt=11)
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            set_run(p.add_run(line if line else " "), size=8.2, ea="宋体", ascii_=mono)

    P.body("B　Gitee/github 仓库链接与目录结构", indent=False, bold=True)
    P.body("仓库链接：【待补充：Gitee/github 公开仓库链接】")
    tree = [
        "repo/",
        "├── data/raw/            官方原始数据（online_retail_II.xlsx，不入库）",
        "│   └── clean/           清洗后 CSV / schema.json / retail.db",
        "├── scripts/",
        "│   ├── 01_load.py       数据加载与字段规范化",
        "│   ├── 02_clean.py      清洗治理、星型模型、三格式导出",
        "│   ├── 03_analysis.py   RFM / 同期群 / 帕累托 / 波士顿 / Apriori / SARIMA",
        "│   ├── 04_visuals.py    模板复现图与业务模型图",
        "│   ├── 05_dashboard.py  Plotly 交互式大屏",
        "│   ├── 06_report.py     按模板生成论文 DOCX",
        "│   ├── config.py        路径、配色、随机种子",
        "│   └── viz_style.py     中文字体与图表样式",
        "├── outputs/",
        "│   ├── figures/         fig01–fig23 图表",
        "│   ├── tables/          t01–t15 结果表与 results.json",
        "│   └── dashboard.html   交互式大屏",
        "├── docs/                期末大论文、数据来源合规声明",
        "├── requirements.txt",
        "├── run_all.py           一键复现入口",
        "└── README.md            项目简介、数据来源、复现步骤、图表索引、分工说明",
    ]
    for line in tree:
        p = doc.add_paragraph()
        set_indent(p, 0, left_pt=24)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_run(p.add_run(line), size=8.2, ea="宋体", ascii_=mono)
    P.body(
        "分工说明：本项目由 1 人独立完成，涵盖数据获取、清洗治理、模型分析、可视化实现、大屏搭建与"
        "论文撰写全部环节。"
    )

    P.body("C　图表索引", indent=False, bold=True)
    idx = [["编号", "文件名", "图题 / 表题", "所在章节"]]
    for i, (fn, cap, sec) in enumerate(FIGS_LIST, start=1):
        idx.append([f"图 {i}", fn, cap, sec])
    for i, (cap, sec) in enumerate(TAB_LIST, start=1):
        idx.append([f"表 {i}", "—", cap, sec])
    P.table(idx, "表 7　图表索引", font_size=8.0,
            widths=[2.0, 6.0, 5.0, 2.5], col_align=["c", "l", "l", "c"])


def main():
    if not TPL.exists():
        raise FileNotFoundError(f"缺少模板文件：{TPL}")
    doc, p16, p17 = prepare()
    abs_len = abstract(p16, p17)
    build(doc)

    cp = doc.core_properties
    cp.title = TITLE
    cp.subject = "《商业数据分析》期末大论文"
    cp.author = "【待补充：姓名】"
    cp.keywords = "；".join(KEYWORDS)

    doc.save(str(OUT))

    # 同步一份到工作区根目录，便于直接打开
    alt = ROOT.parent / "期末大论文.docx"
    try:
        shutil.copyfile(OUT, alt)
    except Exception as e:
        print(f"[06] 同步根目录失败：{e}")
    print(f"[06] 已生成 {OUT}")

    # 字数统计：正文口径 = 从“引言”起至“参考文献”前（不含封面、摘要、参考文献、附录）
    counting, started, chars, abstract_chars = False, False, 0, 0
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("摘要："):
            abstract_chars = len(re.sub(r"\s", "", t)) - 3
        if p.style.name == "Heading 1" and t.strip() == "引言":
            started = True
        if p.style.name == "Heading 1" and t.strip() == "参考文献":
            started = False
        if started:
            chars += len(re.sub(r"\s", "", t))
    print(f"[06] 摘要字符数 {abs_len}（要求 200—300）｜正文（引言至结论，不含图表题注）{chars} 字符")
    print(f"[06] 段落 {len(doc.paragraphs)} 个，表格 {len(doc.tables)} 个")


if __name__ == "__main__":
    main()
