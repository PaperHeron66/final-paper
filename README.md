# 基于 UCI 零售数据的客户价值与销售预测

> 复现：`pip install -r requirements.txt` 后执行 `python run_all.py`，将依次生成清洗数据、23 张图表、交互式大屏与排版好的期末大论文。原始数据（43.5 MB）与中间缓存（`*.pkl`、`fact_sales.csv`、`retail.db`）体积较大，已由 `.gitignore` 排除，需按第二节的官方链接自行下载后放入 `data/raw/`。

---

## 一、项目简介

| 项目 | 内容 |
|---|---|
| 研究对象 | 英国某注册于线上的礼品零售商（无实体门店，客户以批发商为主） |
| 数据规模 | 原始 1,067,371 行 × 8 字段；清洗后事实表见 `data/clean/schema.json` |
| 时间跨度 | 2009-12-01 至 2011-12-09（25 个自然月，其中 24 个完整月参与建模） |
| 分析模型 | RFM 八分类、同期群留存、帕累托/ABC、波士顿矩阵、Apriori 关联规则、SARIMA 预测（6 类） |
| 可视化 | 14 张模板复现图 + 8 张业务模型图 + 1 个交互式大屏（共 23 张图表） |
| 技术栈 | pandas、NumPy、Matplotlib、Seaborn、Plotly、statsmodels、mlxtend、python-docx |
| 合规性 | 仅使用官方 ZIP 一次性下载，**未使用任何爬虫**，未使用 Power BI / Tableau 等 BI 软件 |

### 核心结果（全部由 `run_all.py` 从原始数据重算）

| 指标 | 结果 |
|---|---|
| 清洗后事实表 | 965,509 行 / 37,470 张订单 / 5,741 位可识别客户 / 4,879 个商品 |
| 总销售额 | 13,383,817 英镑（24 个完整月，月均 544,610 英镑） |
| 退货率 | 5.35%（7,406 张退货单，退货金额 71.6 万英镑） |
| RFM | 重要客户 2,870 人占 49.99%，贡献 91.36% 销售额 |
| 同期群 | 次月留存 22.9%，此后两年稳定在 18%–24% 的平台 |
| 帕累托 | 1,119 个 SKU（22.9%）贡献 80.0% 销售额 |
| 波士顿矩阵 | 明星：Germany、France；现金牛：United Kingdom、EIRE、Netherlands |
| 关联规则 | 15 条规则，最强提升度 19.36 |
| SARIMA | 留出 6 个月回测 MAPE 5.27%、RMSE 44,905 英镑；点预测覆盖 2011-12 至 2012-05 |

## 二、数据来源

- 名称：**Online Retail II**（UCI Machine Learning Repository，数据集编号 502）
- 主页：<https://archive.ics.uci.edu/dataset/502/online+retail+ii>
- 下载：<https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip>（官方 ZIP，43.5 MB）
- 引用：Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5CG6D>
- 许可：**CC BY 4.0**（署名后允许共享与改编）
- 获取日期：2026-10-31

数据为脱敏交易流水，不含任何个人身份信息，客户仅以 5 位编号标识。详细声明见 `docs/数据来源合规声明.md`。

## 三、目录结构

```
repo/
├── data/
│   ├── raw/                官方原始数据（online_retail_II.xlsx，不入库）
│   └── clean/              清洗结果：CSV / schema.json / retail.db
├── scripts/
│   ├── 01_load.py          数据加载与字段规范化
│   ├── 02_clean.py         清洗治理、星型模型、三格式导出
│   ├── 03_analysis.py      RFM / 同期群 / 帕累托 / 波士顿 / Apriori / SARIMA
│   ├── 04_visuals.py       14 张模板复现图 + 8 张业务模型图
│   ├── 05_dashboard.py     Plotly 交互式大屏（HTML + 版式图）
│   ├── 06_report.py        按模板生成期末大论文 DOCX
│   ├── config.py           路径、配色、随机种子
│   ├── viz_style.py        中文字体与图表样式
│   └── report_lib.py       DOCX 排版工具（三线表、题注、悬挂缩进）
├── outputs/
│   ├── figures/            fig01–fig23.png（150 dpi）
│   ├── tables/             t01–t15 结果表 + results.json
│   └── dashboard.html      交互式大屏
├── docs/
│   ├── 期末大论文.docx      成品论文
│   └── 数据来源合规声明.md
├── requirements.txt
├── run_all.py              一键复现入口
└── README.md
```

## 四、复现步骤

```bash
# 1. 安装依赖（Python 3.10+）
pip install -r requirements.txt

# 2. 放置原始数据
#    从 https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip 下载，
#    将 online+retail+ii.zip 或解压后的 online_retail_II.xlsx 放入 data/raw/

# 3. 一键复现（约 3–6 分钟，视机器性能）
python run_all.py

# 也可分步执行
python scripts/01_load.py
python scripts/02_clean.py
python scripts/03_analysis.py
python scripts/04_visuals.py
python scripts/05_dashboard.py
python scripts/06_report.py
```

**可复现性约定**

- 全局随机种子 `SEED = 42`（见 `scripts/config.py`），所有抽样、抖动散点、分位切分均固定该值。
- 全量数据参与计算，未对事实表抽样；仅在客户气泡图（抽 6,000 人）与箱线图抖动散点（每国 ≤ 400 点）两处抽样，方法已写入论文 3.3 节。
- 中间结果全部落盘（`outputs/tables/*.csv`、`results.json`），论文中的每个数字都可由这些文件回溯。

## 五、图表索引

| 编号 | 文件 | 图题 | 章节 |
|---|---|---|---|
| 图 1 | fig01_月度销售额折线图.png | 月度销售额走势与三月移动平均 | 5.1 |
| 图 2 | fig02_国家销售额条形图.png | 销售额前 10 位国家分布 | 5.1 |
| 图 3 | fig03_订单金额分布直方图.png | 订单金额分布（对数坐标） | 5.1 |
| 图 4 | fig04_下单时段热力图.png | 工作日下单时段热力图 | 5.1 |
| 图 5 | fig05_销量单价散点图.png | 单品销量、单价与销售额三维散点图 | 5.1 |
| 图 6 | fig06_月度销售额面积图.png | 月度销售额面积图与累计贡献曲线 | 5.2 |
| 图 7 | fig07_年度月度对比簇状柱形图.png | 2010 与 2011 年 1–11 月销售额对比 | 5.2 |
| 图 8 | fig08_国家结构环形图.png | 销售额国家结构环形图 | 5.2 |
| 图 9 | fig09_订单量与客单价双轴图.png | 订单量与客单价双轴组合图 | 5.2 |
| 图 10 | fig10_国家订单金额箱线图.png | 主要国家订单金额箱线图 | 5.2 |
| 图 11 | fig11_商品销售额树状图.png | 销售额前 12 位商品树状图 | 5.2 |
| 图 12 | fig12_客户层级雷达图.png | 核心客户层级 RFM 画像雷达图 | 5.2 |
| 图 13 | fig13_环比增量分解瀑布图.png | 近 13 个月销售额环比增量瀑布图 | 5.2 |
| 图 14 | fig14_核心指标KPI卡片.png | 核心经营指标 KPI 卡片 | 5.2 |
| 图 15 | fig15_RFM分层客户规模.png | RFM 八分类客户规模与销售额贡献 | 5.3 |
| 图 16 | fig16_客户价值气泡图.png | 客户价值气泡图 | 5.3 |
| 图 17 | fig17_同期群留存热力图.png | 同期群月度留存热力图 | 5.3 |
| 图 18 | fig18_商品销售额帕累托图.png | 商品销售额帕累托图与 ABC 分类 | 5.3 |
| 图 19 | fig19_波士顿矩阵四象限.png | 波士顿矩阵四象限图 | 5.3 |
| 图 20 | fig20_关联规则提升度.png | 购物篮关联规则 Top10 | 5.3 |
| 图 21 | fig21_预测与置信区间.png | 月度销售额 SARIMA 预测与 95% 置信区间 | 5.3 |
| 图 22 | fig22_回测误差对比.png | 回测期实际值与预测值对比 | 5.3 |
| 图 23 | fig23_交互式大屏.png | 交互式商业分析大屏（8 个联动组件） | 5.4 |

结果表：`t01` 原始概览、`t02` 清洗日志、`t03` 探索统计、`t04` 外键校验、`t05` 月度趋势、`t06` RFM 分层、`t08` 同期群、`t09` 帕累托/ABC、`t10` 波士顿矩阵、`t11` 关联规则、`t12` 预测明细、`t13` 误差指标、`t15` 大屏 KPI。

## 六、交互式大屏

- 打开方式：浏览器直接打开 `outputs/dashboard.html`（无需后端）。
- 组件 8 个：KPI 卡片、月度趋势、国家结构、客户分层、留存热力、预测区间、订单量与退货额、热销商品明细。
- 联动方式：顶部年份 / 地区 / 客户层级筛选器驱动全局面板；趋势图下拉切换指标口径；环形图点击扇区过滤明细表。
- 论文中的图 23 为同一数据源渲染的静态版式图；若本机安装 `kaleido`，`05_dashboard.py` 会自动改用 Plotly 直出截图。

## 七、分工说明

本项目由 1 人独立完成，涵盖数据获取、清洗治理、模型分析、可视化实现、大屏搭建与论文撰写全部环节。

## 八、环境

Python 3.10+；依赖见 `requirements.txt`。Windows 下中文字体使用「微软雅黑 / 黑体」，`scripts/viz_style.py` 会自动探测并降级，保证图表中文正常显示。
