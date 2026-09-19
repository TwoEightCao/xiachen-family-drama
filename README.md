# 下沉家庭伦理短剧编剧 · xiachen-family-drama

![license](https://img.shields.io/badge/license-MIT-blue.svg)
![python](https://img.shields.io/badge/python-%E2%89%A53.8-blue.svg)
![agent skills](https://img.shields.io/badge/agent--skills-SKILL.md-black.svg)

> 一个专做**下沉中老年家庭伦理短剧**的 AI Agent Skill：婆媳清算、白眼狼子女、寻亲认子、家产争夺、养老困境、保姆护工、黄昏恋骗婚、拆迁亲戚 —— 从一句话点子一路写到 60/80/100 集完稿，并且**写到第 80 集也不跑偏**。

**English**: An agent skill (SKILL.md) for writing Chinese down-market family-ethics short dramas (vertical, 60–100 episodes). It ships an emotional-contract episode engine, 8 genre tracks, character/continuity ledgers, and two verifier scripts. Adapted from [`short-drama-factory`](https://github.com/lixiaoxiao9888-create/short-drama-factory) (MIT). Docs are in Chinese.

---

## 缘起与引用

本项目**改编自** [`lixiaoxiao9888-create/short-drama-factory`](https://github.com/lixiaoxiao9888-create/short-drama-factory)（MIT，© 2026 lixiaoxiao9888-create「老李」），保留了它的核心方法论骨架：

- **情绪契约单元链往返法**（情绪契约贯穿全剧，矛盾按单元跑）
- **证据六档 × 反驳六档**阶梯、三缝合一、攻守转换
- 全剧四幕结构、三级付费墙、连续性台账、台词去 AI 味、四大断章公式、平台合规红线
- 「单集机检」的思路

在此基础上做了三处根本改造：

| | 上游 | 本项目 |
|---|---|---|
| **锚点** | 「爽」——尊严翻盘、碾压 | **「公道」**——「我这辈子的付出，得有人认账」。情绪契约固定为**让不认我的人当众认账** |
| **赛道** | 全品类 12+ 条 | 收窄为 **F1~F8 八条中老年家庭伦理赛道**，每条配一套可直接搬进回合表的「证据六档链」 |
| **闸门** | 通用红线 | 新增三条本赛道硬规矩 + **批次开工门控**（防跨批次漂移） |

另参考 [`0xsline/short-drama`](https://github.com/0xsline/short-drama)（MIT，© 2025 0xsline）的反派分层设计。

> **完整的来源披露、上游 MIT 许可全文、逐文件引用映射与改编程度实测数据见 [`NOTICE.md`](NOTICE.md)。**

---

## 它解决什么问题

下沉短剧的难点从来不是「生成一集剧本」，而是**两件事**：

1. **锚点找错**：把下沉中老年题材写成「战神归来」式的爽剧。实际观众要的不是主角变强，是**公道兑现**——「我这辈子的付出，得有人认账」。
2. **越写越漂**：AI 写到第 40 集，称谓变了、道具穿越了、伏笔烂尾了、主角性格前后不一。因为**上下文会被压缩、会话会重开**，对话记忆不可靠。
3. **集集合格、连起来不像一部剧**：每集单看都过关，但上一集的断章下一集根本不提，几乎每集都用全新钩子开场——观众每集重新入场一次。**这是「只有集内质检、没有跨集质检」的必然结果。**

本项目的对策：**把防漂移防线全部落在文件上，并且让它「不跑就报错」；集内与跨集两个方向都检。**

```text
台账（唯一事实源）＝ 伏笔账 + 人物账 + 道具账 + 规矩账 + 承接账
                                                 ↑ 叙事位置：上一集停在哪一帧、观众在等什么
        ↓ 每批开工
batch_preflight.py 门控 → 不通过不得开写 → 输出「上下文重建摘要」（含本集须承接 / 本集断在）
        ↓ 每集写完
validate_episode.py  机检（集内）→ 这一集自己合不合格
check_chaining.py    机检（跨集）→ 这一集有没有接住上一集
```

> **一部剧 = N 个合格单元 + N−1 段有效承接。** 只查前者，得到的就是 N 个孤立的合格单元。

---

## 双模型分工（可选，v1.5.0）

文笔活和记账活可以分开跑：**主 agent 当「账房」（立项/大纲/分集/五类账/台账更新/跑机检/判门控），单集正文外包给「写手子代理」**（例如 Gemini），判定仍归本地 Python。单模型也能跑通全流程——没有写手路由时自动退化。

```text
主 agent（账房）＝ 立项 / 大纲 / 分集 / 五类账 / 台账更新 / 机检 / 门控
写手子代理       ＝ 只写 episodes/epNNN.md，台账只读
判定             ＝ validate_episode.py + check_chaining.py + batch_preflight.py
```

派活用 [`templates/writer-handoff.md`](templates/writer-handoff.md)（填好即作为子代理提示词）；工序与硬规则见 `SKILL.md` §二。

**为什么换写手不会写崩**：写手与账房之间的接口是**承接账**，而这个契约是**按物件签的，不是按文字签的**——`check_chaining.py` C2 只问「承接账声明的物件有没有出现在下一集开场窗口」，不问措辞。写手可以自由改文笔、换句式，只要那一帧里的**东西**还在，就通过；把物件换掉或改丢，就报 C2。

> **文笔归写手，账归账房，物件的存续由机检裁决。**

完整场景（含 DSH 里子代理路由白名单的两个坑、故障排查表）见 [`docs/使用教程.md`](docs/使用教程.md) §9.5 场景 S9。

---

## 安装

### 方式一：克隆到 skills 目录（最简单）

```bash
git clone https://github.com/TwoEightCao/xiachen-family-drama.git \
  ~/.agents/skills/xiachen-family-drama
```

克隆完即可用 —— 仓库根目录就是 skill 根（`SKILL.md` 在根）。

### 方式二：一键脚本（多平台）

```bash
git clone https://github.com/TwoEightCao/xiachen-family-drama.git
cd xiachen-family-drama
./install.sh              # 自动探测已装的 harness，建软链
./install.sh --copy       # 复制而非软链
./install.sh --list       # 预览，不改动
```

脚本**幂等**：目标位置若已是真实目录（手动安装的版本）会跳过并报告，绝不覆盖；`--uninstall` 可移除。

> 软链模式已验证可用：DSH 的 skill 发现会对符号链接做 `stat` 并归类为目录（`nodeEntryKind`），Claude Code 与 Codex 同样跟随软链。若你的环境不跟随软链，改用 `./install.sh --copy`。

### 方式三：手动

把整个目录复制到任一 skills 根下，目录名建议保持 `xiachen-family-drama`：

| Harness | 用户级 | 项目级 |
|---|---|---|
| DeepSeek Harness (DSH) | `~/.dsh/skills/`、`~/.agents/skills/` | `<项目>/.dsh/skills/`、`<项目>/.agents/skills/` |
| Claude Code | `~/.claude/skills/` | `<项目>/.claude/skills/` |
| Codex CLI | `~/.codex/skills/` | — |

三者共用同一约定：`<skills根>/<name>/SKILL.md`，frontmatter 只需 `name` + `description`，因此**同一份文件三平台通用**。

> **中文文件名说明**：本仓库含中文文件名（如 `docs/使用教程.md`），且台账字段名亦为中文。Python 3 读写无碍；Windows 上建议先执行 `git config --global core.quotepath false`，否则 `git status` 会把中文名显示为八进制转义。

---

## 快速验证

```bash
SKILL=~/.agents/skills/xiachen-family-drama

python3 "$SKILL/scripts/validate_episode.py" --self-test
# → [self-test] 正向样本: PASS / 负向样本: 命中 ['E6','E7','E9'] / 档位识别回归: OK / OK

python3 "$SKILL/scripts/batch_preflight.py" --self-test
# → [self-test] 正向：errors=0 warns=0 / 负向：P3 / P1 / P6 均按预期命中 / OK

python3 "$SKILL/scripts/validate_episode.py" "$SKILL/examples/ep01-demo.md"
# → 档位：standard   正文体量：380 字 / 结果：PASS
```

三条都通过 = 安装正确。（要求 Python ≥ 3.8，无第三方依赖。）

> 注意路径写法：文档里的 `<SKILL>/scripts/...` 是给**人手粘贴**用的绝对路径形式。Agent 加载 skill 时会拿到基目录，能自行解析相对路径。

---

## 怎么用

装上之后，用自然语言或 `/指令` 触发，例如：

```
写个婆媳题材的下沉短剧
```

或直接下指令：

| 指令 | 用途 | 核心产出 |
|---|---|---|
| `/立项` `/策划` `/选题` | 赛道锚定 + 立项 | 立项单四件套 + 人物圣经 + 四幕骨架 + 2~3 个走向 |
| `/赛道` | 看八条赛道 | 各赛道的心理 / 执念模板 / 证据链 |
| `/全剧大纲` `/卡点规划` | 排全剧结构 | 单元链 + 每单元一张往返回合表 + 三级付费墙 |
| `/分集规划 1-10` | 排某段分集 | 每集冲突/场景/情绪流变/集尾断章（**不是正文**） |
| `/写剧本 第7集` | 写一集 | 90~120 秒标准档正文 |
| `/写长档 第7集` | 写一集长档 | 165~195 秒，双回合 + 中段小钩 |
| `/剧本医生` `/精修` | 改稿 | 台词七维暴改 + 断章打磨 + 去 AI 味 |
| `/合规审核` `/自检` | 过审 | 伦理雷区 + 平台红线 + 敏感词转译 |
| `/连写 6-10` | 批量连写 | 先跑门控，再逐集生产（**默认一次 1 集，批量靠它**） |
| `/极速短剧` `/直接写` | 试水 | 静默走完全部门控，直出 1~5 集 |

### 三条沟通原则

1. **一次说清五件事**：赛道 / 集数与档位 / 目标平台 / 要哪一步 / 硬约束。
2. **分批推进**，推荐 5 集一批（正好卡在台账检查点上），别一次要 20 集。
3. **先立宪法再动笔**：先把 `立项单.md`、`人物圣经.md`、`全剧大纲.md`、`台账.md` 落盘，再开写。

> 完整的分场景教程（8 种出剧场景的全流程话术 + 报错码速查 + 沟通反例）见 **[`docs/使用教程.md`](docs/使用教程.md)**。

---

## 八条赛道

| 编号 | 赛道 | 执念一句话模板 |
|---|---|---|
| F1 | 婆媳清算 | 我伺候你月子，你嫌我土 |
| F2 | 白眼狼子女 | 我养你大，你嫌我老 |
| F3 | 寻亲认子 | 我生的孩子，凭什么喊别人妈 |
| F4 | 家产争夺 | 拆迁款有我一半，你们当我死了 |
| F5 | 养老困境 | 三个儿子，没我一个床位 |
| F6 | 保姆护工 | 端屎端尿的是我，认妈的却是她 |
| F7 | 黄昏恋骗婚 | 我图他个伴，他图我那套房 |
| F8 | 拆迁暴富与亲戚 | 拆迁款下来那天，亲戚全活了 |

每条赛道都预置了**现成的 6 回合证据链**（道听途说 → 可抵赖物证 → 看似铁证 → 权威证据 → 多重合围 → 不可推翻的专属铁证），可直接搬进回合表。

---

## 方法论内核

- **情绪契约**：全剧锚点是一句话「让不认我的人当众认账」，换矛盾不换情绪。
- **单元链**：一个矛盾硬帽 **20~30 集**必须闭环（长档折半 10~15 集），60 集 = 2~3 单元，80 集 = 3 单元，100 集 = 3~4 单元。
- **往返六档**：每回合施压升一档、反驳升一档，两档都不升 = 废回合。
- **四层反派**：恶媳/恶婿 → 白眼狼子女（**可理解动机层**）→ 伪善亲戚乡邻 → 幕后真凶/规矩本身，换层不换欲。
- **承接账**：前四类账记的是**状态**，第五类记的是**叙事位置**——第 N 集停在哪一帧、观众在等哪个答案。铁律是「**第 N+1 集的承接必须等于第 N 集的断在**」，钩子最多悬 2 集。
- **三条硬规矩**：
  1. 不许把老人写成纯受害者 —— 必须带「藏着的底牌」，每 10 集至少动一次；
  2. 不许子女反派一坏到底 —— 至少一层要有可体谅的处境；
  3. 不许暴力泄愤收尾 —— 结局必须落在「当众认账 + 伦理秩序修复」。

---

## 三个脚本

```bash
SKILL=~/.agents/skills/xiachen-family-drama

# 1) 单集机检（集内）：档位/体量/场景/对白行/台词长度/断章五字段/中段小钩/高危词/复读/开篇禁令
python3 "$SKILL/scripts/validate_episode.py" episodes/ep001.md
python3 "$SKILL/scripts/validate_episode.py" episodes/ep001.md --format standard|long|manju|manju-long

# 2) 跨集承接机检：C1 断裂 / C2 未兑现 / C3 超期 / C4 台账 + 断章复活延迟诊断
python3 "$SKILL/scripts/check_chaining.py" .
python3 "$SKILL/scripts/check_chaining.py" . --csv /tmp/chaining.csv   # 逐对明细，便于人工比对

# 3) 批次开工门控：底稿/台账字段/集号连续/伏笔超期/断章超期 + 上下文重建摘要
python3 "$SKILL/scripts/batch_preflight.py" . --from 6 --to 10
python3 "$SKILL/scripts/batch_preflight.py" . --from 23 --to 23 --force   # 返修/补拍
```

门控的 **PASS 输出「上下文重建摘要」**是本项目最实用的一块：本批只读这一段摘要即可，不必重读四份全文 —— 这是把 80 集长剧的上下文成本压下来的关键。摘要里**含本集的叙事位置**（须承接什么、断在留给下一集什么），因为写单集最需要的恰恰是这一条。

`check_chaining.py` 有两种工作模式：**有承接账时**做确定性校验（声明 vs 正文）；**没有承接账时**（存量稿子）降级为启发式体检，用「道具账 + 伏笔账 + 内置词表」比对相邻集，此时计数为启发式，不等于人工判读。

---

## 项目结构

```text
xiachen-family-drama/
├── SKILL.md                        主引擎：8 个交互模式 + 门控 + 9 条红线
├── README.md / LICENSE / NOTICE.md / CHANGELOG.md
├── install.sh                      多平台幂等安装
├── docs/使用教程.md                 8 种出剧场景全流程教程
├── docs/发布流程.md                 发布子代理作业手册（含 token 轮换与安全红线）
├── references/
│   ├── 01-genre-map.md             F1~F8 八赛道 × 现成证据六档链
│   ├── 02-emotional-contract.md    情绪契约 + 单元链 + 往返六档
│   ├── 03-audience-paywall.md      受众画像 + 四幕 + 三级付费墙 + 篇幅规格
│   ├── 04-character-bible.md       人物圣经 + 老年主角三原型 + 四层反派
│   ├── 05-voice-dialogue.md        声口库 + 称谓表 + 辱骂分级 + 去 AI 味七维
│   ├── 06-hook-cliffhanger.md      黄金前3秒五母型 + 四大断章公式
│   ├── 07-compliance-taboo.md      平台红线 + 家庭伦理九大雷区
│   └── 08-ledger.md                批次开工规程 + 五类账（含承接账）+ 崩坏点
├── templates/
│   ├── episode-format.md           三档单集排版模板（含【上集承接】）
│   ├── project-bible.md            立项单 + 人物表 + 四幕骨架 + 链条式分集规划
│   ├── ledger.md                   台账空表（11 个机检字段 + 承接账）
│   └── writer-handoff.md           写手交接单（外包正文给子代理时填）
├── examples/ep01-demo.md           标准档单集示例（过机检）
└── scripts/
    ├── validate_episode.py         单集机检 · 集内（E1~E11）
    ├── check_chaining.py           跨集承接机检（C1~C4 + D1 诊断）
    ├── batch_preflight.py          批次开工门控（P1~P9）
    └── publish.sh                  安全发布器（一次性 token URL + 远端复验，不落盘密钥）
```

---

## 已知边界

| 你想做 | 本 skill | 替代做法 |
|---|---|---|
| 网文长篇 → 分集改编 | 无此流水线 | 先自己提炼成一句话点子，再 `/立项` |
| 分镜 / 角色三视图 / 视频提示词 | 明确不做 | 剧本到断章为止，接制作类 skill |
| 悬疑 / 规则怪谈 / 战神赘婿 / 霸总甜宠 | 不是本赛道 | 用通用短剧 skill |
| 中途更换情绪契约或赛道 | 无低成本方案 | 写完这部，下一部再做 |
| 一次产出 20 集以上 | 不支持一口气连写 | 分批 + 台账串起来 |

---

## 许可与致谢

本仓库以 **MIT License** 发布，见 [`LICENSE`](LICENSE)。

改编自 [`short-drama-factory`](https://github.com/lixiaoxiao9888-create/short-drama-factory)（MIT，© 2026 lixiaoxiao9888-create「老李」），并参考 [`short-drama`](https://github.com/0xsline/short-drama)（MIT，© 2025 0xsline）。上游版权声明与逐文件引用映射见 [`NOTICE.md`](NOTICE.md)。感谢这些开源作者的分享。
