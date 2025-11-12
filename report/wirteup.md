# 🌿 项目名称：季节性绿化 —— 全球植被变化的交互式可视化（MODIS）

## 一、研究问题（Motivation & Question）
本项目旨在回答：**全球不同地区的植被在一年四季中如何变化？**  
我们希望通过月度 NDVI（Normalized Difference Vegetation Index，归一化植被指数）的交互式探索，帮助用户理解南北半球的季节交替与不同气候带（热带/温带）的植被差异。

---

## 二、数据来源与处理（Data & Transformations）
- **数据集**：NASA **MODIS/Terra MOD13C2**（月度 NDVI，空间分辨率 0.05°）  
- **时间范围**：2024 年 1–12 月（12 个 HDF 文件）  
- **数据来源**：**NASA Earthdata** 官方平台（earthdata.nasa.gov），通过 MODIS 子集下载接口获取  
- **处理目标**：将全球 0.05° 月度 NDVI 栅格，聚合为**国家级别**（country-level）的月平均 NDVI

**处理流程（可复现）：**
1. 使用 `xarray` 读取每月 HDF（NDVI 波段）并应用缩放因子（1e-4），过滤填充值。  
2. 依据 MOD13C2 的全球规则网格（0.05°）构建经纬度坐标。  
3. 使用 `geopandas` 加载国家边界（Natural Earth，EPSG:4326）。  
4. 将国家多边形栅格化为 2D 标签图层（每个像元归属一个国家），通过 `numpy.bincount` 计算国家内像元的**加权平均**，得到国家月度 NDVI。  
5. 输出 `data/ndvi_country_2024_clean.csv`，字段：`iso3, month, ndvi_mean`；清洗去除无效 ISO（如 `-99`）与缺失值。  

**数据规模与范围：**
- 171 个国家 × 12 个月 = **2052 条记录**  
- NDVI 范围约 **-0.10 ~ 0.89**，均值约 **0.50**（与 MODIS 常见分布一致）

---

## 三、可视化设计（Visual Encodings）
- **空间编码（位置）**：世界国家边界（Natural Earth 投影）。  
- **颜色编码（色彩）**：NDVI 使用连续绿色色带（`d3.interpolateGreens`），域值固定为 **[0.10, 0.85]**，避免少量极端值影响整体对比。  
- **时间编码（滑块）**：通过月份滑块在 1–12 月之间切换。  
- **图例**：在页面下方提供 NDVI 低—高的连续色带提示。

> 设计理由：位置用地理投影最直观；植被强度用绿色渐变具备良好的语义一致性；固定域值提升跨月比较的一致性。

---

## 四、交互设计与实现（Interaction & Implementation）
- **缩放与拖拽（Pan & Zoom）**：探索局部区域与整体格局。  
- **悬停提示（Tooltip）**：显示国家名称与当前月份 NDVI 值。  
- **月份滑块（Dynamic Query）**：实现时间轴切换，快速比较季节差异。  
- **点击国家（Details-on-Demand）**：右侧面板显示该国 **全年 NDVI 折线图**（1–12 月），附平均值，便于对单个国家季节幅度进行洞察。

> 实现要求：仅使用 **D3.js**；前端读取 `data/ndvi_country_2024_clean.csv`，无自定义后端。

---

## 五、主要发现（Findings）
1. **季节交替显著**：6 月北半球 NDVI 高、南半球低；12 月反转。  
2. **热带常绿**：亚马逊、东南亚等热带地区全年 NDVI 较高且稳定，季节波动小。  
3. **温带显著季节性**：如中国、欧洲等在夏季 NDVI 达峰、冬季下降明显。

这些现象与基本气候地理知识一致，验证了 NDVI 作为大尺度植被活力指标的有效性。

---

## 六、开发过程与分工（Process & Teamwork）
**人时统计（people-hours）**（三人合计约 **18–24 小时**）：  
- 数据检索与下载：2–3 h  
- 脚本开发与聚合（HDF→国家级 CSV）：6–8 h  
- 前端 D3 地图与交互（滑块、缩放、tooltip）：4–6 h  
- 国家折线图副视图与样式打磨：3–4 h  
- 文档与幻灯片：3 h

**分工：**
- **毕豪硕（Haoshuo Bi）**：数据下载与预处理脚本、D3 主图与交互实现  
- **石一东（Yidong Shi）**：报告撰写（本文件）、结果分析与总结  
- **单云涛（Yuntao Shan）**：演示幻灯片、GitHub Pages 部署与展示

---

## 七、局限与未来改进（Limitations & Next Steps）
- **空间分辨率限制**：0.05° 网格导致小岛屿国家数据缺失或不稳定。  
- **时间覆盖有限**：当前仅分析 2024 年，可扩展为多年度趋势与异常年比较。  
- **变量单一**：后续可叠加温度、降水、土地利用等，分析 NDVI 与气候要素的耦合关系。  
- **交互扩展**：加入动画播放（自动按月循环）、区域过滤、国家对比（多选对比折线）等高级交互。

---

## 八、仓库与可复现性（Repository & Reproducibility）
- **数据文件**：`data/ndvi_country_2024_clean.csv`（国家×月份 NDVI）  
- **处理脚本**：`tools/build_ndvi_csv.py`（从 MODIS HDF 聚合至国家级）  
- **前端页面**：`index.html`（D3 地图、滑块、tooltip、折线副视图）  
- **部署**：GitHub Pages（公开访问，无需后端）

> 备注：脚本仅依赖公开数据与常用开源库（`xarray`、`geopandas`、`rasterio`/`regionmask`、`numpy`、`pandas`），可按 README 步骤复现。

---

## 九、参考与致谢（References）
- NASA Earthdata. MODIS/Terra Vegetation Indices (MOD13C2). Monthly NDVI, 0.05 Degree CMG.  
- Natural Earth. Admin 0 – Countries.  
- Mike Bostock, D3.js 文档与示例（d3js.org）  
- world-atlas（TopoJSON 国家边界数据）

---

## 十、结论（Conclusion）
我们基于 NASA MODIS 的卫星观测，构建了**可交互**的全球 NDVI 可视化系统，完整展示 2024 年国家尺度的植被季节变化，并通过副视图强化对单国季节曲线的理解。该作品在表达清晰度、交互有效性与可复现性方面均满足课程要求，并为进一步的气候-生态关联分析提供了基础。

原始 MODIS NDVI HDF 文件（MOD13C2.A2024*.hdf）约 1GB，因体积原因未上传。
可通过 NASA Earthdata 搜索 “MOD13C2” 下载，再运行 `tools/build_ndvi_csv.py` 重现结果。
