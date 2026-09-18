#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单集机检 · xiachen-family-drama

出处：本脚本为原创实现，机检思路参考 short-drama-factory（MIT，
© 2026 lixiaoxiao9888-create「老李」）的 scripts/validate_episode.py。
完整来源披露见仓库根目录 NOTICE.md。

用法:
    python3 "<SKILL>/scripts/validate_episode.py" <单集剧本.md> [--format auto|standard|long|manju|manju-long]
    python3 "<SKILL>/scripts/validate_episode.py" --self-test

档位（规格权威: references/03-audience-paywall.md §四）:
    standard    标准档  90~120 秒  正文 350~500   场景 <=2  对白 >=4
    long        长档   165~195 秒  正文 650~850   场景 <=3  对白 >=8  必设中段小钩
    manju       漫剧档  60~90 秒   正文 260~400   场景 <=2  对白 >=4
    manju-long  漫剧长档 140~170 秒 正文 520~680   场景 <=3  对白 >=8  必设中段小钩

检查项:
    E1  档位未标注（未写【档位】字段且无法从头部判定）；已按体量反推
    E2  正文体量不在该档位区间（仅当档位已明确标注或用 --format 指定时报）
    E3  场景数超出该档位上限
    E4  对白行数低于该档位下限
    E5  单句台词超过硬上限 25 字
    E6  缺【黄金前3秒钩子】字段
    E7  【本集断章卡点】缺失或五字段不全
    E8  长档/漫剧长档缺【本集中段小钩】
    E9  命中合规高危/一票否决词
    E10 台词复读（同一句台词重复出现）
    E11 开场第一句台词是称呼语起手（开篇禁令）
    W1  出现抽象心理词（建议改成可观测动作）
    W2  正文未登记【本集小账】

退出码: 0 = PASS（可能有 WARN），1 = FAIL
"""

import argparse
import re
import sys

# 档位规格: (正文体量下限, 上限, 场景上限, 对白行下限, 是否必设中段小钩)
SPEC = {
    "standard": (350, 500, 2, 4, False),
    "long": (650, 850, 3, 8, True),
    "manju": (260, 400, 2, 4, False),
    "manju-long": (520, 680, 3, 8, True),
}

# E9 合规高危 / 一票否决词（对应 references/07-compliance-taboo.md）
BANNED = [
    "杀了你", "要你的命", "老不死的", "断子绝孙", "绝户",
    "黑社会", "打断你的腿", "精神病院", "上访", "下蛊", "改命",
    "自杀", "同归于尽",
]

# W1 抽象心理词（建议改成可观测动作）
ABSTRACT = ["心里", "内心", "感到很", "伤心地", "痛苦地", "默默地想", "心想"]

# E11 称呼语起手黑名单
VOCATIVE = ["妈，", "妈：", "爸，", "儿子，", "儿媳，", "婆婆，", "老李", "老张"]

CLIFF_FIELDS = ["公式", "停格画面", "停格台词", "观众问句", "黑屏"]


LONG_RE = re.compile(r"长档|约\s*3\s*分钟|3\s*分钟|165\s*[~～-]\s*195")
MANJU_RE = re.compile(r"漫剧|解说漫")
FMT_ALIAS = {"标准档": "standard", "长档": "long", "漫剧档": "manju", "漫剧长档": "manju-long"}


def detect_format(text):
    """从剧本【档位】字段或头部标注判定档位。判定不出返回 None（交由 E1 处理）。"""
    m = re.search(r"【档位】\s*[:：]\s*([^\n（(]*)", text)
    if m:
        label = m.group(1).strip()
        for k, v in FMT_ALIAS.items():
            if k in label:
                return v
    is_long = bool(LONG_RE.search(text))
    is_manju = bool(MANJU_RE.search(text))
    if is_long and is_manju:
        return "manju-long"
    if is_long:
        return "long"
    if is_manju:
        return "manju"
    if "标准档" in text:
        return "standard"
    return None


def parse(text):
    """抽出正文行（对白 / △动作 / 断章画面）与结构字段。"""
    dialogue, action, scene = [], [], []
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\[场景", s):
            scene.append(s)
        elif s.startswith("△"):
            action.append(s[1:].strip())
        elif s.startswith("停格画面") or s.startswith("停格台词"):
            action.append(re.sub(r"^停格(画面|台词)[:：]", "", s).strip())
        elif s.startswith('"') or s.startswith("“"):
            dialogue.append(s.strip('"“” '))
    return dialogue, action, scene


def strip_punct(s):
    return re.sub(r"[：:△\"“”\s，。！？、…—]", "", s)


def check(text, fmt, declared=True):
    errors, warns = [], []
    lo, hi, max_scene, min_dialogue, need_midhook = SPEC[fmt]

    dialogue, action, scene = parse(text)
    body = sum(len(strip_punct(x)) for x in dialogue + action)

    # E1 / E2 档位与正文体量
    in_range = lo <= body <= hi
    if not declared:
        fits = [k for k, v in SPEC.items() if v[0] <= body <= v[1]]
        if fits:
            errors.append(
                f"E1 档位未标注：已按体量反推为 {fmt} 档（{lo}~{hi} 字）；"
                f"请在剧本头部补【档位】字段或加 --format"
            )
        else:
            errors.append(
                f"E1 档位未标注且正文体量 {body} 字不落在任何档区间"
                f"（standard 350~500 / long 650~850 / manju 260~400 / manju-long 520~680）"
            )
    elif not in_range:
        errors.append(f"E2 正文体量 {body} 字，{fmt} 档要求 {lo}~{hi} 字")

    # E3 场景数
    if len(scene) > max_scene:
        errors.append(f"E3 场景 {len(scene)} 个，{fmt} 档上限 {max_scene} 个")

    # E4 对白行
    if len(dialogue) < min_dialogue:
        errors.append(f"E4 对白行 {len(dialogue)} 行，{fmt} 档要求 ≥{min_dialogue} 行")

    # E5 单句长度
    for d in dialogue:
        if len(strip_punct(d)) > 25:
            errors.append(f"E5 台词超 25 字（{len(strip_punct(d))} 字）：{d[:20]}…")

    # E6 黄金前3秒
    if "黄金前3秒" not in text and "黄金前 3 秒" not in text:
        errors.append("E6 缺【黄金前3秒钩子】字段")

    # E7 断章五字段
    if "【本集断章卡点】" not in text:
        errors.append("E7 缺【本集断章卡点】")
    else:
        seg = text.split("【本集断章卡点】", 1)[1]
        missing = [f for f in CLIFF_FIELDS if f not in seg]
        if missing:
            errors.append(f"E7 断章字段缺失：{'、'.join(missing)}")

    # E8 长档中段小钩
    if need_midhook and "中段小钩" not in text:
        errors.append("E8 长档缺【本集中段小钩】")

    # E9 合规高危词
    for w in BANNED:
        if w in text:
            errors.append(f"E9 命中合规高危词「{w}」")

    # E10 台词复读
    seen = {}
    for d in dialogue:
        key = strip_punct(d)
        if len(key) < 6:
            continue
        seen[key] = seen.get(key, 0) + 1
    for k, v in seen.items():
        if v >= 2:
            errors.append(f"E10 台词复读：{k[:16]}… 出现 {v} 次")

    # E11 开场称呼语起手
    if dialogue:
        first = dialogue[0]
        for v in VOCATIVE:
            if first.startswith(v):
                errors.append(f"E11 第一句台词以称呼语起手：{first[:16]}…")
                break

    # W1 抽象心理词
    for w in ABSTRACT:
        if w in text:
            warns.append(f"W1 出现抽象心理词「{w}」，建议改成可观测动作")

    # W2 本集小账
    if "本集小账" not in text:
        warns.append("W2 缺【本集小账】标签（便于对账，非强制）")

    return errors, warns, body


def self_test():
    good = '''第01集：《测试》
【档位】：标准档（90～120 秒）
【所属阶段】：第一幕・（第 1/80 集 ｜ 单元A ｜ 往返第 1 回合・证据档1/反驳档1）
【黄金前3秒钩子】：极端羞辱【当众被亲人否认】——她端锅站在门口，儿媳伸手一拦。
【本集小账】：把我是谁咽下去，但留下一本谁都想不到的账
[场景 1]：内景・酒店包厢门口・日
[人物]：周桂兰、刘美娟、周建军
△ 特写：砂锅盖子掀开一条缝，白汽糊住整个镜头。
△ 中景：周桂兰双手端锅站在门口，脚尖把门缝又顶开一点。
刘美娟（伸手一拦，指甲划过锅沿）：
"哎——这锅放这儿。"
周桂兰（愣住，手没松）：
"美娟，这是给月月催奶的鲫鱼汤。"
刘美娟（回头冲满桌人笑，声音抬高两度）：
"这汤是月嫂炖的，这位是请的阿姨。"
△ 中景：满桌亲戚抬头看了一眼，又低头夹菜。
周建军（放下筷子，没往门口看）：
"妈，你先放下吧。"
周桂兰（在围裙上擦了两下，把锅放在门边地上）：
"放下就放下。"
△ 特写：砂锅放在地上，热气贴着地砖散开，没人再碰它。
△ 中景：包厢里的转盘继续转，没人给门口留一把椅子。
周桂兰（转身往外走，手扶着门框）：
"我先回了，你们吃。"
刘美娟（没回头，给孩子擦嘴）：
"阿姨慢走。"
△ 中景：走廊尽头的电梯口，她把围裙解下来叠好，放进布袋。
周桂兰（对着电梯门上的影子，抬手理了理头发）：
"我不挑，我真不挑。"
[场景 2]：内景・老宅厨房・夜
[人物]：周桂兰
△ 特写：一双手伸进腌菜坛，摸出一个裹着塑料袋的铁盒。
△ 特写：铁盒打开，里面是一本卷了边的账本，第一页写着卖房款。
△ 特写：账本夹层里滑出一张泛黄的收据，落款的日期被水浸花了。
周桂兰（把收据按回账本夹层里）：
"这一张，得留到最后。"
△ 中景：她把账本合上，压回坛底，直起身看了一眼墙上的全家福。
△ 特写：全家福里站着儿子、儿媳、抱着的孩子，没有她。
周桂兰（对着账本，像跟人说话）：
"我不挑。"
△ 近景：她抬手要把相框挪正，停住，又收了回来。
【本集断章卡点】
公式：公式 1【物证露头前一秒截断】
停格画面：拇指按着账本封底内侧，掀开一条缝，露出半行红笔字，手停在那儿。
停格台词：「这上面记的，你们谁都不知道——」
观众问句：账本上到底记了什么？
黑屏：（黑屏：下滑解锁第 2 集）
'''
    fmt = detect_format(good) or "standard"
    errors, warns, body = check(good, fmt)
    ok = not errors
    print(f"[self-test] 正向样本: {'PASS' if ok else 'FAIL'} ({body} 字)")
    for e in errors:
        print("   ", e)
    assert ok, "正向样本本应通过"

    bad = good.replace("我不挑。", "妈的，你这个老不死的！").replace(
        "【本集断章卡点】", "").replace("【黄金前3秒钩子】", "")
    bfmt = detect_format(bad) or "standard"
    errors2, _, _ = check(bad, bfmt)
    codes = {e.split()[0] for e in errors2}
    print(f"[self-test] 负向样本: 命中 {sorted(codes)}")
    assert {"E6", "E7", "E9"} <= codes, "负向样本应命中 E6/E7/E9"

    # 档位识别回归：漫剧长档 / 长档 / 漫剧 / 未标注
    assert detect_format("【本集时长】：180 秒（长档·约3分钟）") == "long"
    assert detect_format("漫剧长档 140~170 秒") == "manju-long"
    assert detect_format("漫剧档 60~90 秒") == "manju"
    assert detect_format("第1集 无档位标注") is None
    print("[self-test] 档位识别回归: OK")
    print("[self-test] OK")


def extract_episode(text):
    """若文件里含围栏代码块，取其中含剧集正文字段的那一块；否则用全文。"""
    blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", text, re.S)
    for b in blocks:
        if "【本集断章卡点】" in b or "黄金前3秒" in b or re.search(r"^第\s*\d+\s*集", b.strip()):
            return b
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?")
    ap.add_argument("--format", default="auto",
                    choices=["auto", "standard", "long", "manju", "manju-long"])
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        self_test()
        return 0

    if not args.path:
        ap.error("需要传入单集剧本文件路径")

    try:
        raw = open(args.path, encoding="utf-8").read()
    except OSError as exc:
        print(f"FAIL 无法读取文件：{exc}")
        return 1

    text = extract_episode(raw)
    if args.format == "auto":
        fmt = detect_format(text)
        declared = fmt is not None
        if fmt is None:
            # 未标注档位：先用体量反推最可能的档，避免用错规格连报下游错
            d0, a0, _ = parse(text)
            b0 = sum(len(strip_punct(x)) for x in d0 + a0)
            fits = [k for k, v in SPEC.items() if v[0] <= b0 <= v[1]]
            fmt = fits[0] if fits else "standard"
    else:
        fmt = args.format
        declared = True
    errors, warns, body = check(text, fmt, declared)

    print(f"文件：{args.path}")
    print(f"档位：{fmt}{'' if declared else '（未标注，按体量反推）'}   正文体量：{body} 字")
    for w in warns:
        print("WARN", w)
    for e in errors:
        print("FAIL", e)

    if errors:
        print(f"\n结果：FAIL（{len(errors)} 项）")
        return 1
    print("\n结果：PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
