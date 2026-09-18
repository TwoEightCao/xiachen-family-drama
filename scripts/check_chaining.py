#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨集承接机检 · xiachen-family-drama

出处：本脚本为原创实现（缺陷报告修 4）。完整来源披露见仓库根目录 NOTICE.md。

`validate_episode.py` 只查「集内」，本脚本只查「集与集之间」：相邻两集的
断章钩子有没有被下一集接住。**一部剧 = 80 个合格单元 + 79 段有效承接。**

两种工作模式：
  1) 声明模式（首选）：台账里有「承接账」时，以它为准做确定性校验。
     承接账结构见 `templates/ledger.md`，写入纪律见 `references/08-ledger.md` §一.5。
  2) 启发式模式（兜底）：台账里没有承接账时，从剧集正文反推——
     用「道具账 + 伏笔账 + 内置词表」作文物词表，比对第 N 集断章与第 N+1 集开场。
     该模式只用于存量稿子的体检，**计数为启发式**，不等于人工判读，且不检查 C3。

检查项:
    C1  存在性：第 N 集断章的物件/事件在第 N+1 集开场窗口内出现
    C2  兑现性（声明模式）：承接账声明要接的物件，确实出现在下一集开场窗口
    C3  超期性（声明模式）：状态为「悬」的钩子，距其埋入集 ≥3 集仍未兑现
    C4  台账质量（声明模式）：承接账逐集覆盖，且「上集断在」与「下集承接」指同一件事
    D1  诊断（不计 FAIL）：断章物件复活延迟 ≥3 集的清单

用法:
    python3 "<SKILL>/scripts/check_chaining.py" <项目目录>
    python3 "<SKILL>/scripts/check_chaining.py" <项目目录> --from 1 --to 20
    python3 "<SKILL>/scripts/check_chaining.py" <项目目录> --window action|line1|line2
    python3 "<SKILL>/scripts/check_chaining.py" <项目目录> --csv /tmp/chaining.csv
    python3 "<SKILL>/scripts/check_chaining.py" --self-test

退出码: 0 = 无断裂，1 = 存在断裂（或用法错误）
"""

import argparse
import csv
import re
import sys
from pathlib import Path

# 内置词表：本赛道常见具体道具 / 事件（启发式模式用，与项目台账词表合并）
BASE_VOCAB = [
    "银锁", "长命锁", "工具箱", "布鞋", "围裙", "搪瓷碗", "搪瓷缸", "筷子", "八仙桌",
    "樟木框", "全家福", "相框", "族谱", "房契", "房本", "存折", "银行卡", "回单",
    "记账本", "铁盒", "饼干盒", "米缸", "腌菜坛", "坛子", "褥子", "衣柜", "抽屉",
    "钥匙", "挂锁", "门锁", "门槛", "行李箱", "编织袋", "布袋", "纸箱", "档案袋",
    "录音", "录屏", "监控", "截图", "打印纸", "同意书", "声明", "遗嘱", "合同",
    "发票", "收据", "收条", "字条", "清单", "底册", "摸底表", "表格", "回执",
    "鉴定", "鉴定意见书", "笔录", "调解", "开庭", "传票", "律师函", "证词",
    "手机", "电话", "家族群", "短信", "作文", "作业本", "老照片", "照片",
    "木牌", "缝纫机", "灶台", "灶膛", "冰箱", "阳台", "主卧", "柴房", "储物间",
    "杂物间", "老宅", "堂屋", "村委会", "居委会", "派出所", "法院", "档案窗口",
    "医院", "金店", "饭店", "席面", "面点", "白案", "拆迁", "补偿", "过户",
    "养老院", "赡养", "分家", "偏房", "首付", "尾款", "月供", "彩礼", "嫁妆",
]

WINDOWS = {
    "action": "首个 △ 动作行",
    "line1": "场景起到第 1 句台词",
    "line2": "场景起到第 2 句台词",
}
DEFAULT_WINDOW = "action"


# ---------- 解析 ----------

def extract_episode(text):
    """取剧本正文块（与 validate_episode.py 同口径）。"""
    for b in re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S):
        if "【本集断章卡点】" in b or "黄金前3秒" in b:
            return b
    return text


def parse_hook(body):
    """返回 (停格画面, 停格台词, 观众问句)。"""
    m = re.search(r"【本集断章卡点】(.*?)(?:\n```|\Z)", body, re.S)
    if not m:
        return "", "", ""
    seg = m.group(1)
    frame = line = question = ""
    for l in seg.split("\n"):
        s = l.strip()
        if s.startswith("停格画面"):
            frame = re.sub(r"^停格画面[:：]\s*", "", s)
        elif s.startswith("停格台词"):
            line = re.sub(r"^停格台词[:：]\s*", "", s)
        elif s.startswith("观众问句"):
            question = re.sub(r"^观众问句[:：]\s*", "", s)
    return frame, line, question


def opening_window(body, mode=DEFAULT_WINDOW):
    """取开场窗口：从第一个 [场景] 开始，按 mode 截断。"""
    i = body.find("[场景")
    if i < 0:
        return ""
    lines = [x for x in body[i:].split("\n") if x.strip()]
    if mode == "action":
        for l in lines:
            if l.strip().startswith("△"):
                return l.strip()
        return ""
    out, d = [], 0
    need = 1 if mode == "line1" else 2
    for l in lines:
        out.append(l)
        if l.strip()[:1] in ('"', "“"):
            d += 1
        if d >= need:
            break
    return " ".join(out)


def parse_table(text, section_kw):
    """读台账某小节的表格数据行（与 batch_preflight.py 同口径）。"""
    lines = text.split("\n")
    start = None
    for i, l in enumerate(lines):
        if l.startswith("#") and section_kw in l:
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
        if cells[0] in ("ID", "角色", "道具", "规矩", "集", "回合"):
            continue
        if not any(cells):
            continue
        rows.append(cells)
    return rows


def build_vocab(ledger_text):
    """词表 = 内置 + 道具账第一列 + 伏笔账内容主干。"""
    vocab = set(BASE_VOCAB)
    for r in parse_table(ledger_text, "道具账"):
        if r and r[0]:
            vocab.add(r[0])
            for p in re.split(r"[（(）)、/×x\s]", r[0]):
                if len(p) >= 2:
                    vocab.add(p)
    for r in parse_table(ledger_text, "伏笔账"):
        if len(r) > 1 and r[1]:
            for p in re.split(r"[（(）)、，,→/；;：:\s]", r[1]):
                if 2 <= len(p) <= 8:
                    vocab.add(p)
    return {v for v in vocab if len(v) >= 2 and re.fullmatch(r"[\u4e00-\u9fa5]+", v)}


def norm(s):
    return re.sub(r"[\s，。！？；：、…—·“”\"'‘’（）()《》【】\[\]]", "", s or "")


def load_names(ledger_text):
    """从人物账取具名角色，用于把「仅人名共享」单独归类（弱承接）。"""
    names = set()
    for r in parse_table(ledger_text, "人物账"):
        if r and r[0]:
            nm = re.sub(r"[（(].*?[)）]", "", r[0]).strip()
            if 2 <= len(nm) <= 5:
                names.add(nm)
    return names


def load_project(proj: Path):
    ep_dir = proj / "episodes"
    eps = {}
    if ep_dir.is_dir():
        for p in sorted(ep_dir.glob("ep*.md")):
            m = re.search(r"(\d+)", p.stem)
            if m:
                eps[int(m.group(1))] = extract_episode(p.read_text(encoding="utf-8"))
    ledger_p = proj / "台账.md"
    ledger = ledger_p.read_text(encoding="utf-8") if ledger_p.exists() else ""
    return eps, ledger


# ---------- 检查 ----------

def check(proj: Path, rng=None, window=DEFAULT_WINDOW):
    """返回 (errors, warns, rows, diag, mode_str)。"""
    errors, warns, rows, diag = [], [], [], []
    eps, ledger = load_project(proj)
    if not eps:
        return [f"C0 未找到剧集：{proj}/episodes/ep*.md"], [], [], [], "—"

    vocab = build_vocab(ledger)
    declared = parse_table(ledger, "承接账")
    declared_mode = bool(declared)
    names = load_names(ledger)

    lo, hi = min(eps), max(eps)
    frm = rng[0] if rng and rng[0] else lo
    to = rng[1] if rng and rng[1] else hi

    # 预计算：每集正文词集 / 开场窗口词集 / 断章词集（避免逐对重复扫描全文）
    body_terms = {n: {v for v in vocab if v in eps[n]} for n in eps}
    win_terms = {n: {v for v in vocab if v in opening_window(eps[n], window)} for n in eps}
    hook_txt = {}
    hook_terms = {}
    for n in eps:
        f_n, l_n, _q = parse_hook(eps[n])
        hook_txt[n] = f"{f_n} {l_n}".strip()
        hook_terms[n] = {v for v in vocab if v in hook_txt[n]}

    for n in range(frm, min(to, hi - 1) + 1):
        if n not in eps or (n + 1) not in eps:
            continue
        hook_n = hook_txt[n]
        open_n1 = opening_window(eps[n + 1], window)
        hit = sorted(hook_terms[n] & win_terms[n + 1])
        name_hit = sorted({x for x in names if x in hook_n and x in open_n1})

        # ---- C1 存在性 + 三分类（强 / 弱（仅人名） / 完全不接）----
        if hit:
            verdict = "强承接"
        elif name_hit:
            verdict = "弱承接(仅人名)"
            errors.append(
                f"C1 第 {n}→{n+1} 集断裂（仅人名）：第{n}集断在「{(hook_n or '（无断章）')[:24]}」，"
                f"第{n+1}集开场只共享人名「{'/'.join(name_hit)}」，钩子本身没接")
        else:
            verdict = "完全不接"
            errors.append(
                f"C1 第 {n}→{n+1} 集断裂：第{n}集断在「{(hook_n or '（无断章）')[:24]}」，"
                f"第{n+1}集开场演的是「{(open_n1 or '（无开场）')[:24]}」")
        rows.append({"集": n, "断在": hook_n[:60], "下集开场": open_n1[:60],
                     "共有物件": "/".join(hit), "共有仅人名": "/".join(name_hit), "判定": verdict})

        # ---- 声明模式：C2 / C4 ----
        if declared_mode:
            rn = next((r for r in declared if r and r[0] == str(n)), None)
            rn1 = next((r for r in declared if r and r[0] == str(n + 1)), None)
            if rn is None or rn1 is None:
                errors.append(f"C4 承接账缺行：第 {n} 或第 {n+1} 集未登记")
                continue
            a = norm(rn[2] if len(rn) > 2 else "")
            b = norm(rn1[1] if len(rn1) > 1 else "")
            same = bool(a) and bool(b) and (
                a in b or b in a or bool(set(re.findall(r"..", a)) & set(re.findall(r"..", b))))
            if not same:
                errors.append(
                    f"C1 第 {n}→{n+1} 集声明断裂：第{n}集断在「{(rn[2] if len(rn) > 2 else '')[:20]}」，"
                    f"第{n+1}集承接写的是「{(rn1[1] if len(rn1) > 1 else '')[:20]}」")
            dobjs = {v for v in vocab if v in (rn[2] if len(rn) > 2 else "")}
            if dobjs and not any(v in open_n1 for v in dobjs):
                errors.append(
                    f"C2 第 {n+1} 集未兑现：承接账声明要接「{'/'.join(sorted(dobjs))}」，"
                    f"但开场窗口内没有该物件")

    # ---- C3 断章超期：项目级；只有承接账才有「状态 / 兑现集」----
    if declared_mode:
        for r in declared:
            if len(r) >= 6 and r[5] == "悬" and re.match(r"^\d+$", r[0] or ""):
                gap = hi - int(r[0])
                if gap >= 3:
                    errors.append(
                        f"C3 断章超期：第 {r[0]} 集断在「{(r[2] if len(r) > 2 else '')[:20]}」，"
                        f"标为「悬」已 {gap} 集未兑现（上限 2 集）")
    else:
        warns.append("C3 断章超期未检查：需台账「承接账」（见 templates/ledger.md）；"
                     "启发式模式只报 C1，避免与 C1 重复计数")

    # ---- D1 诊断（不计 FAIL）：断章物件复活延迟 ----
    for n in range(frm, min(to, hi - 1) + 1):
        if n not in eps or not hook_terms.get(n):
            continue
        objs = hook_terms[n]
        for k in range(n + 1, hi + 1):
            if k in body_terms and (objs & body_terms[k]):
                if k - n >= 3:
                    diag.append((n, k - n, "/".join(sorted(objs))[:26]))
                break

    mode = "声明模式（台账承接账）" if declared_mode else f"启发式模式（窗口={WINDOWS[window]}）"
    return errors, warns, rows, diag, f"{mode}｜词表 {len(vocab)}"


# ---------- 自检 ----------

def _mk_ep(n, hook_frame, open_action):
    return f"""第{n:02d}集：《测试》
【档位】：标准档（90～120 秒）
【所属阶段】：第一幕・（第 {n}/80 集 ｜ 单元A ｜ 往返第 1 回合・证据档1/反驳档1）
【黄金前3秒钩子】：极端羞辱【当众被亲人否认】——她端锅站在门口。
【本集小账】：把我是谁咽下去
[场景 1]：内景・老宅厨房・日
[人物]：何秀莲、苏巧云
{open_action}
何秀莲（手在围裙上擦了两下）：
"我不挑。"
【本集断章卡点】
公式：公式 1【物证露头前一秒截断】
停格画面：{hook_frame}
停格台词：「这上面记的，你们谁都不知道——」
观众问句：账本上到底记了什么？
黑屏：（黑屏：下滑解锁第 {n+1} 集）
"""


def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d) / "proj"
        (proj / "episodes").mkdir(parents=True)
        (proj / "台账.md").write_text(
            "# 台账\n\n## 道具账\n| 道具 | 持有 |\n|---|---|\n| 长命银锁 | 何秀莲 |\n",
            encoding="utf-8")

        # 正向：第 2 集开场接住第 1 集断章的银锁
        (proj / "episodes" / "ep001.md").write_text(
            _mk_ep(1, "工具箱盖压着那把银锁，镜头怼到她的手背。",
                   "△ 特写：砂锅盖子掀开一条缝。"), encoding="utf-8")
        (proj / "episodes" / "ep002.md").write_text(
            _mk_ep(2, "刘凤的行李箱堵在门口。",
                   "△ 特写：工具箱被掀开，银锁压在盖子上。"), encoding="utf-8")
        errs, _, _, _, mode = check(proj, (1, 1))
        print(f"[self-test] 正向样本（承接）: {mode} → errors={errs or '无'}")
        assert not errs, "正向样本本应无断裂"

        # 负向：第 2 集开场换成了别的东西
        (proj / "episodes" / "ep002.md").write_text(
            _mk_ep(2, "刘凤的行李箱堵在门口。",
                   "△ 特写：一张打印纸被拍在冰箱门上。"), encoding="utf-8")
        errs2, _, _, _, _ = check(proj, (1, 1))
        codes = {e.split()[0] for e in errs2}
        print(f"[self-test] 负向样本（断裂）: 命中 {sorted(codes)}")
        assert "C1" in codes, "负向样本应命中 C1"

        # 声明模式：承接账声明与上集断在不是同一件事 → C1
        (proj / "台账.md").write_text(
            "# 台账\n\n## 道具账\n| 道具 | 持有 |\n|---|---|\n| 长命银锁 | 何秀莲 |\n\n"
            "## 承接账\n"
            "| 集 | 本集承接（上集断章） | 本集断在（留给下一集） | 观众问句 | 兑现集 | 状态 |\n"
            "|---|---|---|---|---|---|\n"
            "| 1 | —（首集） | 银锁被扔进工具箱 | 这锁她还要不要 | 3 | 悬 |\n"
            "| 2 | 打印纸拍在冰箱上 | 刘凤拎箱入住 | 那她住哪 | 2 | 收 |\n",
            encoding="utf-8")
        errs3, warns3, _, _, mode3 = check(proj, (1, 1))
        codes3 = sorted({e.split()[0] for e in errs3})
        print(f"[self-test] 声明模式: {mode3} → {codes3}")
        assert "C1" in codes3, "声明不一致应命中 C1"

        # C3 超期：第 1 集标「悬」且项目已写完第 4 集 → 距埋入 3 集
        (proj / "episodes" / "ep003.md").write_text(
            _mk_ep(3, "房契被锁进抽屉。", "△ 特写：院门口的雪化成泥。"), encoding="utf-8")
        (proj / "episodes" / "ep004.md").write_text(
            _mk_ep(4, "族谱被挂上墙。", "△ 特写：灶膛里的火苗窜起来。"), encoding="utf-8")
        errs4, _, _, _, _ = check(proj, (3, 3))
        codes4 = sorted({e.split()[0] for e in errs4})
        print(f"[self-test] C3 超期: 命中 {codes4}")
        assert "C3" in codes4, "悬 3 集未兑现应命中 C3"
        print("[self-test] OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", nargs="?")
    ap.add_argument("--from", dest="frm", type=int)
    ap.add_argument("--to", dest="to", type=int)
    ap.add_argument("--window", default=DEFAULT_WINDOW, choices=list(WINDOWS))
    ap.add_argument("--csv")
    ap.add_argument("--quiet", action="store_true", help="只打印统计，不逐条打印 FAIL")
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

    errors, warns, rows, diag, mode = check(proj, (args.frm, args.to), args.window)

    print(f"=== 跨集承接机检 · {args.project} ===")
    print(f"模式：{mode}")
    for w in warns:
        print("WARN", w)
    if not args.quiet:
        for e in errors:
            print("FAIL", e)

    c1 = sum(1 for e in errors if e.startswith("C1"))
    c2 = sum(1 for e in errors if e.startswith("C2"))
    c3 = sum(1 for e in errors if e.startswith("C3"))
    c4 = sum(1 for e in errors if e.startswith("C4"))
    strong = sum(1 for r in rows if r["判定"] == "强承接")
    weak = sum(1 for r in rows if r["判定"] == "弱承接(仅人名)")
    none_ = sum(1 for r in rows if r["判定"] == "完全不接")
    n_rows = max(len(rows), 1)
    print(f"\nC1 断裂 {c1} ｜ C2 未兑现 {c2} ｜ C3 超期 {c3} ｜ C4 台账 {c4} ｜ 合计 {len(errors)}")
    print(f"承接分布：强承接 {strong}/{len(rows)} = {100*strong//n_rows}% ｜ "
          f"弱承接(仅人名) {weak} ｜ 完全不接 {none_}")
    print(f"断裂合计（弱 + 完全不接）= {weak + none_}")

    if diag and not args.quiet:
        print("\nD1 诊断 · 断章物件复活延迟 ≥3 集的（不计 FAIL）：")
        for n, gap, objs in diag[:20]:
            print(f"  第 {n} 集断章的「{objs}」隔 {gap} 集才再出现")
        if len(diag) > 20:
            print(f"  …共 {len(diag)} 处")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=["集", "断在", "下集开场", "共有物件", "共有仅人名", "判定"])
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\n逐对明细已写入：{args.csv}")

    if errors:
        print(f"\n结果：FAIL（{len(errors)} 项）")
        return 1
    print("\n结果：PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
