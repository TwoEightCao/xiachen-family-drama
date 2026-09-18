# 第三方声明与引用映射（NOTICE）

本仓库是一份**改编作品（derivative work）**，并非从零原创。本文件用于完整披露来源、保留上游版权声明，并给出逐文件的引用映射。

> **维护约定**：新增或重写任何衍生文件时，必须同步更新本文件的 §2 映射表。

---

## 1. 上游项目与许可全文

### 1.1 主要来源：short-drama-factory

- 项目：https://github.com/lixiaoxiao9888-create/short-drama-factory
- 用途：本项目**骨架来源**。保留了其「情绪契约单元链往返法」（情绪契约 / 单元链 / 证据六档 × 反驳六档 / 三缝合一）、全剧节奏与付费墙架构、连续性台账、台词诊断、断章公式体系、合规红线，以及"单集机检"的思路。
- 许可：MIT

```text
MIT License

Copyright (c) 2026 lixiaoxiao9888-create (老李)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 1.2 次要来源：short-drama

- 项目：https://github.com/0xsline/short-drama
- 用途：`references/04-character-bible.md` 的**四层反派体系**参考其 `references/villain-design.md` 的分层设计思路。
- 许可：MIT

```text
MIT License

Copyright (c) 2025 0xsline

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 2. 逐文件引用映射

| 本仓库文件 | 来源文件 | 改写范围 |
|---|---|---|
| `SKILL.md` | `short-drama-factory/SKILL.md` | 保留「档位 / 交互模式 / 执行顺序 / 硬红线 / 文件索引」框架；锚点由「爽」改为「公道」；赛道收窄为 F1~F8；新增三条本赛道硬规矩与批次开工门控 |
| `references/01-genre-map.md` | `short-drama-factory/references/genre-map.md` | 12 条全品类赛道（4 条赛道扩为 12+）**替换**为本赛道 F1~F8 八条中老年家庭伦理赛道，并为每条补齐可直接搬用的「证据六档链」 |
| `references/02-emotional-contract.md` | `short-drama-factory/references/emotion-flow-roundtrip.md` | 保留情绪契约 / 单元链 / 三缝合一 / 证据六档 / 反驳六档 / 攻守转换 / 回合表格式；把证据与反驳六档的**每一档实例**改写为中老年家庭伦理语境；新增本赛道档 6 归属规则 |
| `references/03-audience-paywall.md` | `short-drama-factory/references/hongguo-beat-sheet.md` | 保留四幕结构、三级付费墙与篇幅规格骨架；**替换**受众画像与付费心理为本赛道专属；修正四幕实际占比与集区间（原文近似值 → 18.75/37.5/25/18.75） |
| `references/04-character-bible.md` | `short-drama-factory/references/character-bible.md` + `short-drama/references/villain-design.md` | 四件套框架来自前者；四层反派体系的分层思路参考后者；**新增**老年主角三原型、五类「藏着的底牌」、可理解动机层、配角功能位、全员名册与校验清单 |
| `references/05-voice-dialogue.md` | `short-drama-factory/references/dialogue-doctor-anti-ai.md` | 保留「去 AI 味」诊断思路；**重写**为七类人物语言指纹、亲属称谓地域对照表、辱骂三级转译、金句模板库（24 条），诊断维度扩为七维 |
| `references/06-hook-cliffhanger.md` | `short-drama-factory/references/golden-3s-hook-library.md` + `cliffhanger-master-formulas.md` | 沿用「黄金前 3 秒五母型」与「四大断章公式」命名；**全部定义与 40 条实例按本赛道重写**；新增中段小钩写法与钩子强度四维自评表 |
| `references/07-compliance-taboo.md` | `short-drama-factory/references/screenplay-compliance-rules.md` | 保留平台一票否决与敏感词转译骨架；**新增**家庭伦理九大雷区（遗弃老人 / 子女互害 / 私刑 / 重男轻女等）与伦理呈现三条正向要求 |
| `references/08-ledger.md` | `short-drama-factory/references/continuity-ledger.md` | 保留四类账与读写规程；**第四类账由「世界观规则账」替换为「规矩账」**（家规 / 乡俗 / 法律）；新增批次开工硬门控、长档差异与台账崩坏点 |
| `templates/episode-format.md` | `short-drama-factory/templates/episode-format.md` | 保留三档单集排版骨架；新增必填 `【档位】` 字段与断章五字段格式对齐 |
| `templates/ledger.md` | `short-drama-factory/templates/ledger.md` | 保留头部字段 + 四类账 + 回合表 + 付费墙结构；字段按本赛道重排（新增赛道 / 主角 / 底牌 / 反派四层），供机检脚本解析 |
| `templates/project-bible.md` | — | 原创（整合立项单 / 人物表 / 四幕骨架 / 单元链 / 回合表 / 付费墙 / 交付目录） |
| `scripts/validate_episode.py` | 思路参考 `short-drama-factory/scripts/validate_episode.py` | 原创实现。自行定义 E1~E11 检查项与档位识别机制 |
| `scripts/batch_preflight.py` | — | 原创。批次开工门控 P1~P8 + 上下文重建摘要 |
| `examples/ep01-demo.md` | — | 原创示例 |
| `docs/使用教程.md` | — | 原创 |
| `CHANGELOG.md` | — | 原创 |

**改编程度实测**：对本仓库 `*.md` 与两个上游来源做逐行比对（去空白、长度 ≥12 字的行），完全一致的行占比 **8.0%**；其中 `templates/ledger.md` 26.5%、`references/08-ledger.md` 15.4%、`templates/episode-format.md` 14.5%。其余为改写或新增。此数据用于如实说明改编深度，不作精确法律计量。

---

## 3. 调研参考（仅阅读，未引入内容）

以下项目在选题调研阶段被阅读，但其内容**未进入本仓库**，仅致谢其信息价值：

| 项目 | 用途 |
|---|---|
| [kunhai-88/hongguo-shortdrama-screenwriting-course](https://github.com/kunhai-88/hongguo-shortdrama-screenwriting-course) | 红果官方《短剧编剧第一课》整理，用于校验平台侧节奏与过稿口径 |
| [icooldp/400-duanju-shuangdian](https://github.com/icooldp/400-duanju-shuangdian) | 爆款短剧爽点方法论汇编，用于确认爽点密度口径 |
| [doublesq97-ui/su-ai-short-drama](https://github.com/doublesq97-ui/su-ai-short-drama) | 女频/男频双版本 skill 的工程结构参考（references + templates 分层） |
| [yanshangcha01/libtv-shortdrama-storyboard](https://github.com/yanshangcha01/libtv-shortdrama-storyboard) | 男频短剧爽感拆解，用于对照验收 |
| [zenstory-ai/drama-skills](https://github.com/zenstory-ai/drama-skills) | 短剧/漫剧 skill 合集，用于对照验收 |

---

## 4. 本仓库的原创部分

以下内容为本仓库原创，不在上游范围内：

- **方法论锚点的替换**：由上游的「爽」（尊严翻盘、碾压）改为「**公道**」——「我这辈子的付出，得有人认账」，并据此把全剧情绪契约固定为「让不认我的人当众认账」。
- **赛道收窄**：F1~F8 八条中老年家庭伦理赛道，每条配一套可直接搬进回合表的「证据六档链」。
- **三条本赛道硬规矩**：不许把老人写成纯受害者（须有「藏着的底牌」，每 10 集至少动一次）／不许子女反派一坏到底（第 2 层须有可理解动机）／不许暴力泄愤收尾（结局须为当众认账 + 伦理秩序修复）。
- **两个校验脚本**及其规格体系（E1~E11、P1~P8）。
- **批次开工门控与上下文重建摘要**机制。
- `templates/project-bible.md`、`examples/ep01-demo.md`、`docs/使用教程.md`。

---

## 5. 许可

本仓库整体以 **MIT License** 发布，见 [`LICENSE`](LICENSE)。

因包含上述 MIT 许可作品的改编内容，本仓库同时保留其原始版权声明（见 §1）。上游与本仓库的许可条款一致，均为 MIT。
