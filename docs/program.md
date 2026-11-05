# program.md — 让 STEP IR 在 token 不涨的前提下，用计算几何推断出更多东西

## 目标（一个数）

最大化 `SCORE`（`bench/eval_geom.py` 打印）：dev 族上的**计算几何成功率**（5 项加权）× **token 因子**。
`TEST_SCORE` 是同一指标在 held-out 族上的值，只用来防止过拟合 dev 族，**不是优化目标**：dev 涨而 test 明显掉就不能 keep。

## 背景

`cand/` 是被测的 STEP→IR 代码（起点 = 2026-11-05 的 stepir.py / stepir_ops.py / cadfit.py）。IR 是给 LLM 看的紧凑 B-rep 描述（一行一个面）。
问题：同一个几何体经不同建模器、导入导出、面分割之后 B-rep 不同，依赖原始面分割的 IR 不稳定。要求：
1. **合并**几何上属于同一曲面的连通区域（拆开的半圆柱、被切开的平面……），给 LLM 高层理解；
2. NURBS 里实际是平面/圆柱/圆锥/球/环面的面，**重新识别为解析曲面**（边同理：B 样条直线、圆弧要认回 L/A）；
3. 扫掠/放样来的曲面：测出**操作来源**（extrude / revolve / helical / loft / sweep / skin / 非刚体 freeform）；
4. 倒角、圆角：记录它圆滑的**那两个面**和半径，供 `shared_boundary` / ql 选边；
5. **token 数保持少**：识别、合并之后 IR 应当比现在更短，不是更长。

## 基准（只读，别改）

`bench/data/<case>/`：200 个 SimpleCADAPI 程序化零件（20 族 × 10；曲面 70 / 机械 70 / 旋转 60），每件有 `model.py`（真值构造代码）和 4 个形态：
`orig`、`split`（周期面在接缝处切成半面 + 大面按面积切开）、`nurbs`（所有面转 B 样条）、`splitnurbs`（两者叠加）。
真值全部精确：变体面→原始面（几何求得）、原始面的真实载体、每个面由哪个建模操作产生（重跑 `model.py` 得到，`gt_ops.json`）、倒角/圆角面圆滑的两个前置面。
dev / test 按**族**划分（同族 10 件不会跨 dev/test）。`bench/MANIFEST.json` 冻结全部数据哈希，被改会拒绝评分。

## 评分（`bench/eval_geom.py`，只读）

候选入口 `cand/pipeline.py: run(step_path) -> {"lines": [IR 行], "face_map": {SDK 面号: IR id}}`。**只按 `lines` 里可见的内容给分**。
候选只拿到一个拷到空临时目录的 `part.step`，看不到别的文件。

| 项 | 权重 | 含义 |
|---|---|---|
| stability | 0.30 | 候选在变体上的 IR 记录（载体+面积）与它在 orig 上的记录的 F1：LLM 看到的东西有多稳定 |
| merge | 0.15 | 同一原始面被切开的碎片是否并入同一个 IR 组（成对 F1；不同原始面被并到一起算误并；本来就同载体相邻的面不计分） |
| analytic | 0.20 | `nurbs`/`splitnurbs` 里真实解析面认对载体（类型+参数）的召回，与自由曲面**不被误判成解析面**的特异度，取平均；误判的由 harness 用 OCP 取样独立复核 |
| origin | 0.20 | 自由曲面/锥/环面的来源：放样/扫掠/skin、回转、螺旋/扭转、样条拉伸；错把刚体运动说给非刚体面算 0，只说 `freeform` 给一半 |
| blend | 0.15 | 倒角/圆角面被标出 ∧ `between` 恰是它圆滑的两个前置面 ∧ 圆角半径 ±3%；对非倒角面的误报进分母 |

token 因子 `tokf = min(1, 1.25/TOK_REL, 1.15/TOK_REL_ORIG)`：`TOK_REL` = 四种形态 IR 的平均 token / 冻结的基线 orig 平均 token（4028）。
不鼓励无限压缩：超过预算才罚；但**基线在 split/nurbs 变体上膨胀 2.2–4.5 倍**，所以合并与识别本身就会把 tokf 拉回 1。

派生行格式（harness 读取）：`{"derived":"blend","faces":[ir id],"kind":"fillet|chamfer","between":[a,b],"r":半径}`；
`{"derived":"op","op":"extrude|revolve|helical|loft|sweep|skin","faces":[...]}`；`{"derived":"freeform","faces":[...]}`；
`{"derived":"origin","op":...,"faces":[...]}`。IR id 没有对应记录的面视为"被隐含"（棱柱侧面）。新增字段/派生行可以自由设计，只要上面这些仍能被读出。

## 规则

- 可改：`cand/` 下全部（`stepir.py`、`stepir_ops.py`、`cadfit.py`、`pipeline.py`，可新增模块）。只读：`bench/` 下评分、数据、manifest、本文件、`autoresearch.json`。
- 只用 SimpleCADAPI 2.1.4 + OCP + numpy/scipy（SimpleCADAPI 2.1.4 环境）；不新增依赖、不联网。
- **不得**读取 `bench/data` 下除传入 STEP 外的任何文件；不得按文件名/case 号/族名/面数特判；容差必须随零件尺度（bbox 对角线）缩放；
  不得为刷分在 `lines` 里写不为真的断言（harness 的独立复核会抓到解析面误判；其余靠你自律）。
- 每次评测 ≤ 30 分钟；单个 STEP 超时 240 s 算失败。不改 harness 的指标定义。
- 不 `git push`；每个实验一个 commit。

## 简单性准则

同等分数下代码越少越好；为 0.002 的提升引入大段脆弱代码不值得。能删就删。

## 建议探索方向（按预期收益排序，随时重排）

1. **曲面识别（已验证可行）**：原型在 NURBS 化的解析面上 圆柱 149/149、圆锥 9/9、环面 28/28、球 4/4、平面 182/186（漏的是采样点不足的小面）。方法：精确 D1 采样（点+法向）→ 平面（SVD）→ 球（法线交点）→ 回转面（法线线与轴相交的 6×6 线性方程，再在 (z,ρ) 平面看子午线是常数/直线/圆）。小面用 UV 格点加密采样。
2. **边识别**：B 样条边→直线（弦距）/圆弧（平面圆拟合 + 走向）/整圆，让 `edge_seg` 输出 L/A/C；这是棱柱压缩重新生效、token 降下来的前提。
3. **同载体连通面合并**：按 SDK 的边实体号去掉组内共享边，剩余有向边按端点串成环（外环/内环用平面内面积符号判定）；解析面比载体，样条面比极点网/取样距离；只合并**相邻**的同载体面，不相邻的同平面凸台不合并。
4. **来源溯源**：cadfit 把 loft / twisted / helical / gordon 区分开（截面是否全等 → sweep/螺旋；截面渐变 → loft；网格蒙皮 → skin）；`EXTRUSION` 面直接给 extrude 方向。
5. **倒角/圆角记录**：基线有 525 个误报（把真圆柱当圆角）、半数漏检；用"与两个支撑面相切 + 半径恒定 + 面窄"判据，并给 `between`；多边倒角链、端部。
6. token：识别合并之后重新检查哪些字段多余（BSPL 的 loops 若可解析化、`adj` 冗余）。

## 禁止的方向

改 harness、改真值、改容差定义、按 dev 族特调。需要时可以把想法写进 `.autoresearch/notes.md`。
