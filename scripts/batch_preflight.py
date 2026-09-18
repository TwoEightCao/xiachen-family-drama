#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批次开工校验 · xiachen-family-drama

出处：本脚本为原创实现。完整来源披露见仓库根目录 NOTICE.md。

`/连写` 每批开工前**必须先跑本脚本**。它做两件事：
  1) 校验（跳过则报错）：四份底稿是否齐备、台账头部字段是否完整、集号是否连续、伏笔是否超期；
  2) 输出「上下文重建摘要」——本批只需读这一段，不必重读四份全文，避免跨批次记忆漂移。

用法:
    python3 "<SKILL>/scripts/batch_preflight.py" <项目目录> --from 6 --to 10
    python3 "<SKILL>/scripts/batch_preflight.py" <项目目录>              # 只校验不校验集号
    python3 "<SKILL>/scripts/batch_preflight.py" <项目目录> --from 6 --to 10 --force
    python3 "<SKILL>/scripts/batch_preflight.py" --self-test

检查项:
    P1  四份底稿缺失（立项单.md / 人物圣经.md / 全剧大纲.md / 台账.md）
    P2  台账头部字段缺失（当前集/总集数/档位/赛道/情绪契约/单元划分/主角/底牌/反派四层）
    P3  集号不连续：--from 必须等于「当前集 + 1」（--force 可跳过）
    P4  人物账为空（无具名角色）
    P5  情绪契约缺失或过长（>60 字）
    P6  伏笔超期：状态为 埋/养 且 拟收 ≤ 当前集 - 3
    P7  本批区间超出总集数或 from > to
    P8  单元划分与总集数不匹配（单元数不在 2~4 或区间未覆盖全剧）

退出码: 0 = PASS（可能有 WARN），1 = FAIL（不得开写）
"""

import argparse
import re
import sys
from pathlib import Path

DOCS = ["立项单.md", "人物圣经.md", "全剧大纲.md", "台账.md"]
HEAD_FIELDS = ["当前集", "总集数", "档位", "赛道", "情绪契约",
               "单元划分", "主角", "底牌", "反派四层"]
STALE_TOLERANCE = 3  # 伏笔超期容忍集数（与 references/08-ledger.md 一致）

FMT_ALIAS = {"漫剧长档": "漫剧长档", "标准档": "标准档",
             "长档": "长档", "漫剧档": "漫剧档"}


# ---------- 解析 ----------

def parse_header(text):
    """读台账开头的 `键: 值` 头部字段（兼容全角冒号）。"""
    head = {}
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("#") or line.startswith(">"):
            continue
        m = re.match(r"^([^:：|]{2,12})[:：]\s*(.+)$", line)
        if m:
            k, v = m.group(1).strip(), m.group(2).strip()
            head.setdefault(k, v)
        if line.startswith("##"):
            break
    return head


def parse_table(text, section_kw):
    """取标题含 section_kw 的小节里的表格数据行（跳表头/分隔/空行）。"""
    lines = text.split("\n")
    start = None
    for i, l in enumerate(lines):
        if l.lstrip("#").strip().startswith(section_kw) or (
                l.startswith("#") and section_kw in l):
            start = i
            break
    if start is None:
        return []
    rows = []
    for l in lines[start + 1:]:
        s = l.strip()
        if s.startswith("#"):
            break
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        if cells[0] in ("ID", "角色", "道具", "规矩", "回合"):
            continue
        if not any(cells):          # 空模板行 |  |  |  |
            continue
        rows.append(cells)
    return rows


def parse_units(text):
    """解析 单元划分: A(1-25) / B(26-52) / C(53-80)"""
    out = []
    for name, a, b in re.findall(r"([A-D])\s*[（(]\s*(\d+)\s*[-~～]\s*(\d+)\s*[)）]", text):
        out.append((name, int(a), int(b)))
    return out


def act_ranges(total):
    """从 references/03-audience-paywall.md 读四幕区间（单一事实源，不在此重复常量）。"""
    p = Path(__file__).resolve().parent.parent / "references" / "03-audience-paywall.md"
    if not p.exists():
        return {}
    t = p.read_text(encoding="utf-8")
    if total in (80, 60, 100):
        sec = t.split("## 三、")[1].split("### 三级付费墙")[0]
        col = {80: 1, 60: 2, 100: 3}[total]
    elif total in (40, 30, 50):
        sec = t.split("### 长档四幕折算")[1].split("**结局硬约束**")[0]
        col = {40: 1, 30: 2, 50: 3}[total]
    else:
        return {}
    out = {}
    for l in sec.split("\n"):
        if not l.startswith("| ") or "～" not in l:
            continue
        cells = [c.strip() for c in l.strip("|").split("|")]
        if len(cells) <= col:
            continue
        m = re.search(r"(\d+)\s*～\s*(\d+)", cells[col])
        if m and cells[0]:
            out[cells[0]] = (int(m.group(1)), int(m.group(2)))
    return out


def find_act(acts, ep):
    for name, (a, b) in acts.items():
        if a <= ep <= b:
            return f"{name}（{a}～{b}）"
    return "—"


# ---------- 校验 ----------

def check(proj: Path, rng, force=False):
    errors, warns = [], []
    frm, to = rng

    # P1 文件齐备
    missing = [d for d in DOCS if not (proj / d).exists()]
    if missing:
        errors.append(f"P1 缺少底稿：{'、'.join(missing)}（无台账不得开写）")
        return errors, warns, {}, {}, []

    ledger = (proj / "台账.md").read_text(encoding="utf-8")
    head = parse_header(ledger)

    # P2 头部字段
    lack = [f for f in HEAD_FIELDS if not head.get(f)]
    if lack:
        errors.append(f"P2 台账头部缺字段：{'、'.join(lack)}")

    # P5 情绪契约
    pact = head.get("情绪契约", "")
    if not pact:
        pass  # 已由 P2 报
    elif len(pact) > 60:
        warns.append(f"P5 情绪契约 {len(pact)} 字偏长（建议 ≤60），过长易中途变味")

    # P4 人物账
    chars = parse_table(ledger, "人物账")
    if not chars:
        errors.append("P4 人物账为空：至少登记主角与第 1 层反派，未建档角色不得给台词")

    # P6 伏笔超期
    cur = int(head.get("当前集", "0") or 0)
    for r in parse_table(ledger, "伏笔账"):
        if len(r) < 5:
            continue
        fid, content, _buried, due, state = r[0], r[1], r[2], r[3], r[4]
        if state in ("埋", "养") and re.match(r"^\d+$", due or ""):
            if int(due) <= cur - STALE_TOLERANCE:
                errors.append(
                    f"P6 伏笔超期：{fid}「{content}」拟收第 {due} 集，当前已到第 {cur} 集"
                    f"（超期 >{STALE_TOLERANCE} 集）")

    # P3 集号连续性
    try:
        total = int(head.get("总集数", "0"))
    except (TypeError, ValueError):
        total = 0
    if frm and not force:
        try:
            _cur = int(head.get("当前集", "0"))
        except (TypeError, ValueError):
            _cur = None
        if _cur is not None and frm != _cur + 1:
            errors.append(
                f"P3 集号不连续：当前集 {_cur}，本批应从第 {_cur + 1} 集开始，"
                f"实际申请第 {frm} 集（确认要跳写请加 --force）")

    # P7 集号
    if frm and to and frm > to:
        errors.append(f"P7 区间非法：--from {frm} > --to {to}")
    if to and total and to > total:
        errors.append(f"P7 本批第 {to} 集超出总集数 {total}")

    # P8 单元划分
    units = parse_units(head.get("单元划分", ""))
    if total and units:
        if not (2 <= len(units) <= 4):
            warns.append(f"P8 单元数 {len(units)} 不在 2~4（60集2~3 / 80集3 / 100集3~4）")
        if units[0][1] != 1 or units[-1][2] != total:
            warns.append(f"P8 单元划分未覆盖全剧（{units[0][1]}～{units[-1][2]}，总集数 {total}）")
    elif total and not units:
        warns.append("P8 单元划分无法解析（格式应为 A(1-25) / B(26-52) / C(53-80)）")

    return errors, warns, head, {"chars": chars, "ledger": ledger}, units


# ---------- 摘要 ----------

def summary(proj, head, data, units, rng):
    frm, to = rng
    ledger = data["ledger"]
    cur = int(head.get("当前集", "0") or 0)
    try:
        total = int(head.get("总集数", "0") or 0)
    except ValueError:
        total = 0
    acts = act_ranges(total)

    out = []
    out.append("=" * 62)
    out.append("上下文重建摘要（本批只读这一段，不必重读四份全文）")
    out.append("=" * 62)
    out.append(f"剧名/赛道：{head.get('赛道','—')}")
    out.append(f"档位/总集数：{head.get('档位','—')} / {total} 集")
    out.append(f"情绪契约：{head.get('情绪契约','—')}   ← 全剧不改")
    out.append(f"主角：{head.get('主角','—')}")
    out.append(f"底牌：{head.get('底牌','—')}   ← 每 10 集至少动一次")
    out.append(f"反派四层：{head.get('反派四层','—')}")
    out.append(f"付费墙：{head.get('付费墙','未登记')}")
    out.append("-" * 62)
    out.append(f"当前集：{cur}  →  本批：第 {frm}～{to} 集"
               if frm else f"当前集：{cur}")
    for ep in ([frm] if frm else []):
        out.append(f"本批起点所属：{find_act(acts, ep)}")
    for name, a, b in units:
        if frm and a <= frm <= b:
            out.append(f"本批所属单元：单元 {name}（第 {a}～{b} 集）"
                       f"{'  ⚠ 单元硬帽 20~30 集，到点必须闭环' if b - a + 1 >= 20 else ''}")
            break

    out.append("-" * 62)
    out.append("人物关系现值（写前对齐，称谓不许漂）：")
    for r in data["chars"][:12]:
        if len(r) >= 4:
            out.append(f"  · {r[0]} ｜ {r[3]} ｜ 变动集 {r[4] if len(r) > 4 else '—'}")
    out.append("  关系现值只认：敌对 / 表面客气 / 动摇 / 倒戈 / 认账")

    fb = parse_table(ledger, "伏笔账")
    pend = [r for r in fb if len(r) >= 5 and r[4] in ("埋", "养")]
    out.append("-" * 62)
    out.append(f"待收伏笔（{len(pend)} 条）：")
    for r in pend[:10]:
        out.append(f"  · {r[0]} {r[1]}（埋于 {r[2]}，拟收 {r[3]}）")
    props = parse_table(ledger, "道具账")
    if props:
        out.append("关键道具现值：")
        for r in props[:8]:
            if len(r) >= 3:
                out.append(f"  · {r[0]} ｜ 持有 {r[1]} ｜ {r[2]}（第 {r[3] if len(r)>3 else '—'} 集）")
    rules = parse_table(ledger, "规矩账")
    if rules:
        out.append("已立规矩：")
        for r in rules[:8]:
            if len(r) >= 1:
                out.append(f"  · {r[0]}（确立第 {r[1] if len(r)>1 else '—'} 集）"
                           f"{'  ⚠ 已被违反' if len(r)>3 and r[3].startswith('是') else ''}")
    rnd = parse_table(ledger, "往返回合表")
    matched = False
    if rnd and frm:
        for r in rnd:
            m = re.search(r"(\d+)\s*[-~～]\s*(\d+)", r[1] if len(r) > 1 else "")
            if m and int(m.group(1)) <= frm <= int(m.group(2)):
                out.append("-" * 62)
                out.append(f"本批所在回合：回合 {r[0]}（第 {r[1]}）")
                out.append(f"  证据档：{r[2] if len(r)>2 else '—'}")
                out.append(f"  反驳档：{r[3] if len(r)>3 else '—'}")
                out.append("  ↑ 本批各集的证据/反驳档不得超出此回合区间")
                matched = True
                break
    if frm and not matched:
        out.append("-" * 62)
        out.append("本批所在回合：⚠ 台账回合表中未找到覆盖本批起点的回合"
                   "——先补全台账回合表（每单元 6 回合）再开写")
    out.append("=" * 62)
    out.append("写后必做：更新台账四类账 → 跑 validate_episode.py → 过人工自检清单")
    return "\n".join(out)


# ---------- 自检 ----------

def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "立项单.md").write_text("# 立项单\n", encoding="utf-8")
        (proj / "人物圣经.md").write_text("# 人物圣经\n", encoding="utf-8")
        (proj / "全剧大纲.md").write_text("# 全剧大纲\n", encoding="utf-8")
        tpl = Path(__file__).resolve().parent.parent / "templates" / "ledger.md"
        ledger = tpl.read_text(encoding="utf-8").replace("当前集: 0", "当前集: 5")
        (proj / "台账.md").write_text(ledger, encoding="utf-8")

        errs, warns, head, data, units = check(proj, (6, 10))
        print(f"[self-test] 正向：errors={len(errs)} warns={len(warns)}")
        for e in errs:
            print("   ", e)
        assert not any(x.startswith(("P1", "P2", "P3", "P4")) for x in errs), \
            "正向样本不应有 P1~P4 错误"

        # 负向1：集号不连续
        e2, _, _, _, _ = check(proj, (20, 24))
        assert any(x.startswith("P3") for x in e2), "应报 P3 集号不连续"

        # 负向2：缺台账
        (proj / "台账.md").unlink()
        e3, _, _, _, _ = check(proj, (6, 10))
        assert any(x.startswith("P1") for x in e3), "应报 P1 缺底稿"

        # 负向3：伏笔超期
        (proj / "台账.md").write_text(
            ledger.replace("当前集: 5", "当前集: 40"), encoding="utf-8")
        e4, _, _, _, _ = check(proj, (41, 45))
        assert any(x.startswith("P6") for x in e4), "应报 P6 伏笔超期"

        print("[self-test] 负向：P3 / P1 / P6 均按预期命中")
        print("[self-test] OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?")
    ap.add_argument("--from", dest="frm", type=int)
    ap.add_argument("--to", dest="to", type=int)
    ap.add_argument("--force", action="store_true", help="跳过 P3 集号连续性检查")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0
    if not args.project:
        ap.error("需要传入项目目录")

    proj = Path(args.project)
    if not proj.is_dir():
        print(f"FAIL 项目目录不存在：{proj}")
        return 1

    errs, warns, head, data, units = check(proj, (args.frm, args.to), args.force)

    print(f"=== 批次开工校验 · {args.project}"
          + (f" · 第 {args.frm}～{args.to} 集" if args.frm else "") + " ===")
    for w in warns:
        print("WARN", w)
    for e in errs:
        print("FAIL", e)

    if errs:
        print(f"\n结果：FAIL（{len(errs)} 项）—— 不得开写，先修台账/底稿")
        return 1

    print("结果：PASS")
    if data:
        print()
        print(summary(proj, head, data, units, (args.frm, args.to)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
