# step-tools：STEP → 紧凑 IR（STEPIR）及其计算几何优化

STEPIR 把一个 STEP 零件转成给 LLM 读的紧凑 B-rep 描述（一行一个面，平面带边界环、拉伸结构、解析载体参数），用来让模型写出重建它的 CAD 脚本（SimpleCADAPI）。

本仓库是对 STEPIR 的一轮**计算几何优化**，以及用来度量它的**基准、评分器和真值生成流水线**。

> 一句话：同一个几何体经过拆面、导入导出、转 NURBS 之后 B-Rep 会变，原始 STEPIR 因此不稳定、token 数暴涨；
> 优化后 IR 对这些表示变化基本不变，且更短。

## 结果

### 真实零件盲测（120 个从未参与调参的 ABC 零件，只评一次）

对每个零件生成三种扰动：`split`（周期面在接缝处切成半面 + 大面按面积切开）、`nurbs`（所有面转成 B 样条）、`splitnurbs`（两者叠加），测候选在扰动后的 IR 是否与未扰动时一致。

| | 原始 stepir | 本仓库 |
|---|---|---|
| 稳定性（扰动前后 IR 记录的 F1） | 0.193 | **0.958** |
| 合并（被切开的同曲面碎片并回一个面，成对 F1） | 0.018 | **0.992** |
| NURBS 里的解析面认回（召回 / 特异度） | 0 / 1.000 | **0.974 / 1.000** |
| IR token：原件 / split / nurbs / splitnurbs | 6635 / 12161 / 14759 / 26449 | **5418 / 5927 / 5081 / 5840** |

ABC 零件本身不随仓库分发（许可原因），见下文"复现"。

### 合成基准（260 件，dev 族；括号为 held-out 族）

总分 0.855（起点）→ **0.926**（0.927）。分项：

| 能力 | 起点 | 现在 |
|---|---|---|
| 曲面识别（解析面召回；自由曲面不被误判） | 0.50 | 0.995 |
| 同曲面连通面合并 | 0.004 | 0.972 |
| 稳定性 | 0.124 | 0.978 |
| 操作来源（回转/螺旋/扭转/放样/扫掠…） | 0.586 | 0.820 |
| 倒角圆角（标出面 ∧ 圆滑的两个面 ∧ 半径） | 0.257 | 0.824 |

完整实验记录见 [docs/research_notes.md](docs/research_notes.md) 与 `docs/results_*.tsv`。

## 做了什么

1. **曲面识别**（`cand/geomnorm.py`）：精确 D1 采样（点+外法向）→ 平面（SVD）→ 球（法线交点）→ 回转面（法线与轴相交的线性方程，再在 (z,ρ) 平面看子午线是常数/直线/圆）。B 样条面若其实是平面、圆柱、圆锥、球、环面，就按解析面输出。
2. **边识别**：B 样条边认回直线、圆弧、整圆，平面边界环才能重新编码成 `L/A/C`，棱柱压缩才重新生效。
3. **合并同曲面连通面**：解析面按载体参数；样条面按"沿共享边法向与曲率（G2）连续"。组内共享边抵消，剩余有向边串成闭环；合并共线线段和同圆弧；合并后的取值范围在所有成员上重新实测。
4. **倒角圆角记录**（`cand/blends.py`）：在识别、合并后的面上找（与两个不同支撑面 G1 相切且截面圆弧 <170°、夹在两个平面之间的窄面、与共轴圆柱和垂直平面相邻的小圆锥）。`between` 给出它圆滑的两个面，被 IR 省略的侧面直接内联载体，供 `shared_boundary`/ql 选边。
5. **操作来源**（`cand/cadfit.py` + `stepir_ops.py`）：面被某个刚体运动扫出 ⟺ `n·c + (x×n)·w = 0`，解 6×6 零空间（回转/螺旋/拉伸）。非刚体的自由曲面再按沿轨道的等参线截面是否刚体全等，区分**扫掠**与**放样**。
6. **信息分层**（[docs/DESIGN_TIERS.md](docs/DESIGN_TIERS.md)）：哪些必须直接给、哪些可以安全压缩、哪些让 Agent 按需看。无证据的派生行被剪掉（评分不变、token 少 15%）；样条完整控制网、cadfit 证据、邻接关系放进 `cand/stepir_query.py` 按需查询。

## 目录

```
cand/        被测代码：stepir.py（STEP→IR）、stepir_ops.py（派生行）、geomnorm.py（识别/合并）、blends.py、cadfit.py、
             pipeline.py（评分器调用的入口）、stepir_query.py（按需查询）
bench/       评分器 eval_geom.py、变体与真值生成脚本、各零件的 model.py 与 design.json（不含 STEP，见下）
gen/         用 codex 补数据的流水线：任务清单、提示词、验证器、队列
real_eval/   真实零件上的分布外检验脚本
docs/        RESULTS.md（结论与局限）、DESIGN_TIERS.md、research_notes.md、program.md、autoresearch.json、各轮 results_*.tsv
```

## 环境与依赖

- Python 3.12；`SimpleCADAPI` 2.1.4（运行 `cand/` 与评分器）；`OCP`（`cadquery-ocp`）；`numpy`；`tokenizers`（评分器数 token）。
- 重新生成基准零件需要 SimpleCADAPI **2.2.5**（零件是用它写的）。
- 评分器用 Qwen 的 `tokenizer.json`：`export STEPIR_TOKENIZER=/path/to/tokenizer.json`。

## 用法

```bash
export STEPIR_NDIG=4
python cand/stepir.py part.step                         # 基础 IR（每行一个 JSON）
python cand/stepir_ops.py part.step --augment --fit     # IR + 派生行（blend / op / freeform / axis）
python cand/stepir_query.py part.step face 12           # 按需：第 12 号面的完整记录，样条面含控制网
python cand/stepir_query.py part.step evidence 12       # 按需：哪些刚体运动能扫出它（cadfit）
python cand/stepir_query.py part.step axis              # 按需：共轴簇与精确子午轮廓
python cand/stepir_query.py part.step neighbours 12     # 按需：邻面与相切长度
```

Python 入口（评分器就是调用它）：

```python
import sys; sys.path.insert(0, "cand")
import pipeline
out = pipeline.run("part.step")
out["lines"]      # IR 行（表头、面记录、派生行）
out["face_map"]   # SDK 面下标 → IR id；没有对应记录的 id 是被隐含的棱柱侧面
```

派生行格式：

```
{"derived":"blend","faces":[ir id],"kind":"fillet|chamfer","between":[a,b],"r":半径}   # between 的元素是 IR id，或内联载体
{"derived":"op","op":"extrude|revolve|helical|loft|sweep","faces":[...]}
{"derived":"freeform","faces":[...]}        # 没有任何刚体运动能扫出的面
{"derived":"axis","dir":[...],"point":[...],"faces":[...]}
```

## 复现基准

基准分三步生成，STEP 数据较大且部分来自第三方，所以不随仓库分发：

```bash
export SIMPLECAD_PYTHON=/path/to/python-with-SimpleCADAPI-2.2.5
python bench/export_orig.py                # 每个 bench/data/<case>/model.py → orig.step
python bench/build_variants.py --workers 8 # split / nurbs / splitnurbs 变体 + 父面真值（variants.json）
python bench/build_gt_ops.py --workers 6   # 重跑 model.py，得到每个面由哪个建模操作产生、倒角圆角的支撑面（gt_ops.json）
python bench/make_manifest.py              # 冻结数据哈希；评分器校验它，不一致则拒绝评分
python bench/eval_geom.py --workers 8      # 打印 SCORE 与各分项
```

`bench/data` 里 case-001…200 是程序化生成的 200 个单实体零件（曲面 70 / 机械 70 / 旋转 60），case-201…260 是用 codex 补的 60 个（沿曲线轨道的自由曲面扫掠、非全等截面放样、样条轮廓回转/拉伸，由 `gen/` 流水线生成并验证）。
评分器按**族**划分 dev / test，同族的 10 个零件不会跨集。

### 评分（`bench/eval_geom.py`）

候选入口 `cand/pipeline.py: run(step) -> {"lines","face_map"}`，**只按 `lines` 里可见的内容给分**；候选只拿到一个拷到空临时目录的 `part.step`，看不到真值和构造代码。

| 项 | 权重 | 含义 |
|---|---|---|
| stability | 0.30 | 扰动后的 IR 记录（载体+面积）与未扰动时的 F1 |
| merge | 0.15 | 同一原始面被切开的碎片是否并入同一个 IR 组（成对 F1；不同原始面被并到一起算误并） |
| analytic | 0.20 | NURBS 化后真实解析面认对载体的召回，与自由曲面不被误判成解析面的特异度；误判由评分器用 OCP 取样独立复核 |
| origin | 0.20 | 自由曲面/锥/环面的操作来源；刚体运动说给非刚体面算 0，只说 `freeform` 给一半 |
| blend | 0.15 | 倒角/圆角面被标出，`between` 恰是它圆滑的两个前置面，圆角半径 ±3%；对非倒角面的误报进分母 |

token 因子 `tokf = min(1, 1.25/TOK_REL, 1.15/TOK_REL_ORIG)`，`TOK_REL` 是四种形态 IR 的平均 token 与冻结的基线（4028）之比，超预算才罚。

## 补数据流水线（`gen/`）

用 codex CLI 写基准里缺的零件（脚本和验证都是本仓库的，codex 只负责写 `model.py`）：

```bash
python gen/make_tasks.py                    # → tasks.json（60 个任务，7 类）
export CODEX_BIN=codex SIMPLECAD_PYTHON=... VALIDATE_PYTHON=...
python gen/run_queue.py --parallel 6        # 每个任务一个 codex，验证后失败的带原因重试
```

验证器 `gen/validate.py` 强制：脚本可运行并导出 STEP、导出结果是单个有效实体、**确实含有自由曲面**、静态扫描禁止读 STEP 或绕开 SDK。8 路并发时会触发限流，队列会自动退避重试。

## 局限与诚实声明

- **倒角圆角在真实零件上并不比 SDK 原有提示更准**（带文件名标签的真实件：倒角件 24/75 对 26/75，圆角件 47/75 对 49/75）。本版本的价值是对 NURBS / 拆面表示保持不变、支撑面内联，不是检出率更高。
- 合成基准自带标签歧义，**没有去迎合**：沉头孔锥面≈倒角、草图圆角≈fillet、两个全等截面之间的线性放样≈拉伸、截面同形平移的 gordon≈扫掠。这些在评分里表现为"误报/错断言"。
- **自由曲面的拆分碎片并不总能合并**：OCC 拆分样条面时会重新逼近曲面，沿共享边的法向、曲率会出现 0.5°–1° 的偏差，G2 判据因此漏掉约 3% 的同父相邻对，**个别零件会整件合不上**（如 case-212 这个沿曲线轨道的扫掠件，拆分后 20 对碎片全部未合并）。我离线扫了 6039 对相邻样条面：只看法向的宽松判据会误并 550 多对"仅相切"的不同曲面，所以没有放宽。解析面（平面/柱/锥/球/环）的合并不受此影响。
- 放样/扫掠的阈值 `sweep_tol=2.5e-3` 来自 OCC 扫掠逼近精度，别的建模器的近似误差可能不同；它给出的是假设性标签，不是证明。
- 基准里的两个生成器风格单一（全是 OCC 精确几何）。因此额外做了三项分布外检验：120 个真实 ABC 件盲测（上表）；150 个带真实文件名标签的件检验倒角圆角规则（**推翻了我先前按生成器调的两条规则**，已改回，合成基准分数因此主动下降 0.013）；曲面识别容差灵敏度（放大 10 倍才开始误判，当前值离失效点有 10 倍余量）。
- 按需查询（第三层）只验证了"取得回来"，**没有在 agent 轨迹里验证**是否减少错误或回合数。
- 评分器在实验中途修正过 4 次，每次都重新初始化并记录在 [docs/research_notes.md](docs/research_notes.md)。
- 新 IR 的面号、派生行、被隐含面与旧版 stepir 不兼容；已用旧 IR 生成的训练数据需要重建。

细节见 [docs/RESULTS.md](docs/RESULTS.md)。

## 来源

- 基准 case-001…200 的 `model.py` 来自同一研究项目里另一轮合成的 `tail-solid200` 程序化生成器；case-201…260 由 codex（gpt-6.1-sol）按 `gen/prompt_template.md` 写成并经 `gen/validate.py` 验证。
- 优化过程是一个自动实验循环：每个实验一个 commit，按评分保留或回滚；`docs/program.md` 与 `docs/autoresearch.json` 是该循环的契约。
