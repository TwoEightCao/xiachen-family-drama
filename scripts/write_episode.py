#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""write_episode.py — 主 agent 直连「写手」API 生成单集正文（写手路线的路线 C）

出处：本脚本为原创实现（v1.6.0）。完整来源披露见仓库根目录 NOTICE.md。

## 它解决什么

DSH 里子代理换模型受**会话级白名单**限制（`subagent-model-selection.allowedModels`
在会话创建时写入一次就不再变），所以「主 agent 用 A 模型、正文用 B 模型」在
子代理路线上要开新会话才生效。本脚本换一条路：**主 agent 保持不换（总控），
自己用 HTTP 直接调写手端点生成正文。** 一次会话一个模型的前提因此不再冲突。

## 分工没变

    账房（主 agent）＝ 立项/大纲/分集/五类账/承接账/台账登记/跑机检/门控/判定
    写手（本脚本）  ＝ 只产出正文文本，落到 episodes/epNNN.md
    判定            ＝ 仍然只由本地 Python 机检做，写手自评不构成证据

本脚本**不碰台账**，只写 `--out` 指定的那一个文件，另把调用元数据追加到
`--log`（默认 `<out 所在目录>/.writer-log.jsonl`，不含任何密钥）。

## 用法

    # 1) 先干跑：只打印请求概要，不发网络请求
    python3 write_episode.py --prompt-file handoff.txt --out episodes/ep001.md --dry-run

    # 2) 真跑
    python3 write_episode.py --prompt-file handoff.txt --out episodes/ep001.md \
        --model gemini-3.1-pro-preview --reasoning-effort high

    # 3) 离线自检（不联网、不需要 key）
    python3 write_episode.py --self-test

## 密钥（绝不回显、绝不落进产出文件）

读取顺序：
  1. 环境变量 `WRITER_API_KEY`
  2. `--key-file`，默认 `~/.config/xiachen/writer_key`

端点读取顺序：
  1. `--base-url`
  2. 环境变量 `WRITER_BASE_URL`
  3. 默认 `https://new.dszyym.com/v1`

硬校验：key 文件若位于**某个 git 仓库内** → 直接拒绝运行（防把密钥推上 GitHub）。
所有输出经过掩码，token 不进日志；产出文件里只有剧本正文。

退出码：0 = 成功；1 = 失败（网络/解析/校验/用法）。
"""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_BASE_URL = "https://new.dszyym.com/v1"
DEFAULT_KEY_FILE = "~/.config/xiachen/writer_key"
DEFAULT_MAX_TOKENS = 8192
DEFAULT_TIMEOUT = 300
EFFORTS = ("none", "minimal", "low", "medium", "high")


# ---------- 密钥与掩码 ----------

def resolve_key(key_file: str):
    """返回 (key, 来源说明)。不回显 key 本身。"""
    env = os.environ.get("WRITER_API_KEY")
    if env:
        return env.strip(), "环境变量 WRITER_API_KEY"
    p = Path(os.path.expanduser(key_file))
    if not p.is_file():
        return None, f"未找到（{p}）"
    return p.read_text(encoding="utf-8").strip(), str(p)


def key_file_inside_repo(p: Path):
    """key 文件若在某个 git 仓库内，返回该仓库根，否则 None。"""
    try:
        cur = p.resolve().parent
    except OSError:
        return None
    for _ in range(64):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            return None
        cur = cur.parent
    return None


def mask(text: str, secret: str) -> str:
    """把 secret 从输出里抹掉。"""
    if not secret:
        return text
    out = text.replace(secret, "***KEY***")
    # 再兜一层：任何 sk- 开头的长串都抹掉
    return re.sub(r"sk-[A-Za-z0-9_\-]{16,}", "***KEY***", out)


# ---------- 响应解析 ----------

def strip_fences(text: str) -> str:
    """模型爱把整集包在 ``` 里。若整体被单个围栏包住，剥掉围栏保留内容。"""
    t = text.strip()
    m = re.fullmatch(r"```[a-zA-Z]*\n(.*?)```", t, re.S)
    if m:
        return m.group(1).strip()
    return t


def extract_content(payload: dict) -> str:
    """从 chat.completion 响应里取正文。兼容 content 为字符串或分片数组。"""
    choices = payload.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        parts = []
        for c in content:
            if isinstance(c, dict) and isinstance(c.get("text"), str):
                parts.append(c["text"])
            elif isinstance(c, str):
                parts.append(c)
        content = "".join(parts)
    return strip_fences(content or "")


def usage_summary(payload: dict) -> dict:
    u = payload.get("usage") or {}
    g = u.get("gemini_usage_metadata") or {}
    return {
        "prompt_tokens": u.get("prompt_tokens"),
        "completion_tokens": u.get("completion_tokens"),
        "thoughts_tokens": g.get("thoughtsTokenCount"),
        "total_tokens": u.get("total_tokens"),
        "finish_reason": ((payload.get("choices") or [{}])[0] or {}).get("finish_reason"),
    }


# ---------- 主流程 ----------

def build_body(model, prompt, system, effort, max_tokens, temperature):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        body["temperature"] = temperature
    if effort:
        body["reasoning_effort"] = effort
    return body


def call_api(base_url, key, body, timeout):
    url = base_url.rstrip("/") + "/chat/completions"
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", "Bearer " + key)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 0, json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser(
        description="主 agent 直连写手 API 生成单集正文（只写 --out 一个文件）")
    ap.add_argument("--prompt-file", help="写手提示词文件（= 填好的 templates/writer-handoff.md 正文）")
    ap.add_argument("--prompt", help="或直接给提示词字符串")
    ap.add_argument("--system-file", help="可选：系统提示词文件")
    ap.add_argument("--out", help="产出文件路径，通常 episodes/epNNN.md")
    ap.add_argument("--model", default="gemini-3.1-pro-preview", help="模型 id")
    ap.add_argument("--base-url", default=None, help=f"OpenAI 兼容端点，默认 {DEFAULT_BASE_URL}")
    ap.add_argument("--key-file", default=DEFAULT_KEY_FILE, help="密钥文件路径")
    ap.add_argument("--reasoning-effort", default="high", choices=EFFORTS,
                    help="none/minimal 可用于省思考 token；默认 high")
    ap.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    ap.add_argument("--log", default=None, help="调用元数据 jsonl（默认 <out目录>/.writer-log.jsonl）")
    ap.add_argument("--raw-out", default=None, help="可选：存原始 JSON 响应，便于排查")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的 --out")
    ap.add_argument("--dry-run", action="store_true", help="只打印请求概要，不发网络请求")
    ap.add_argument("--self-test", action="store_true", help="离线自检（不联网）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    # ---- 参数校验 ----
    if not args.out:
        print("FAIL  必须指定 --out")
        return 1
    if not (args.prompt_file or args.prompt):
        print("FAIL  必须指定 --prompt-file 或 --prompt")
        return 1
    if args.prompt_file and not Path(args.prompt_file).is_file():
        print(f"FAIL  提示词文件不存在：{args.prompt_file}")
        return 1

    out = Path(args.out)
    if out.exists() and not args.force:
        print(f"FAIL  产出文件已存在：{out}")
        print("      拒绝覆盖（防止把人工改过的稿子冲掉）。确认要覆盖请加 --force。")
        return 1

    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        prompt = args.prompt
    system = Path(args.system_file).read_text(encoding="utf-8") if args.system_file else None

    base_url = args.base_url or os.environ.get("WRITER_BASE_URL") or DEFAULT_BASE_URL
    key, src = resolve_key(args.key_file)

    # ---- key 安全校验：绝不允许密钥文件位于 git 仓库内 ----
    if not os.environ.get("WRITER_API_KEY") and key:
        kp = Path(os.path.expanduser(args.key_file))
        repo = key_file_inside_repo(kp)
        if repo is not None:
            print(f"FAIL  密钥文件位于 git 仓库内（{repo}）—— 这会把密钥推上 GitHub。")
            print("      请移到仓库外，例如 ~/.config/xiachen/writer_key")
            return 1

    body = build_body(args.model, prompt, system, args.reasoning_effort,
                      args.max_tokens, args.temperature)

    print(f"端点  {base_url}")
    print(f"模型  {args.model}    reasoning_effort={args.reasoning_effort}")
    print(f"密钥  {src}（不回显）")
    print(f"提示词 {len(prompt)} 字符   产出 {out}")

    if args.dry_run:
        print("DRY-RUN  未发送请求。请求概要：")
        print(f"  messages={len(body['messages'])}  max_tokens={args.max_tokens}  "
              f"temperature={args.temperature}")
        print(f"  提示词 sha256={hashlib.sha256(prompt.encode()).hexdigest()[:16]}")
        return 0

    if not key:
        print("FAIL  未找到密钥。请写入 ~/.config/xiachen/writer_key（chmod 600），")
        print("      或设置环境变量 WRITER_API_KEY。")
        return 1

    status, raw = call_api(base_url, key, body, args.timeout)
    raw_masked = mask(raw, key)

    if args.raw_out:
        Path(args.raw_out).write_text(raw_masked, encoding="utf-8")

    if status != 200:
        print(f"FAIL  HTTP {status}")
        print("      " + raw_masked[:600].replace("\n", " "))
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"FAIL  响应不是 JSON：{e}")
        print("      " + raw_masked[:400].replace("\n", " "))
        return 1

    if payload.get("error"):
        print(f"FAIL  端点返回错误：{str(payload['error'])[:400]}")
        return 1

    content = extract_content(payload)
    if not content.strip():
        print("FAIL  响应里没有正文（choices[0].message.content 为空）")
        return 1

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content.rstrip() + "\n", encoding="utf-8")

    u = usage_summary(payload)
    print(f"OK    已写入 {out}（{len(content)} 字符）")
    print(f"      用量 prompt={u['prompt_tokens']} completion={u['completion_tokens']} "
          f"thoughts={u['thoughts_tokens']} finish={u['finish_reason']}")

    # ---- 调用元数据（不含密钥，供账房审计）----
    log = Path(args.log) if args.log else out.parent / ".writer-log.jsonl"
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "out": str(out),
            "model": args.model,
            "base_url": base_url,
            "reasoning_effort": args.reasoning_effort,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "prompt_chars": len(prompt),
            "output_chars": len(content),
            **u,
        }
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"      元数据已追加 {log}")
    except OSError as e:
        print(f"WARN  元数据写入失败（不影响产出）：{e}")

    return 0


# ---------- 自检（离线，不联网、不需要 key） ----------

def self_test():
    print("[self-test] 响应解析：")
    p1 = {"choices": [{"message": {"content": "第01集：《测试》\n【档位】：标准档"}}]}
    assert extract_content(p1).startswith("第01集"), "字符串 content 解析失败"
    p2 = {"choices": [{"message": {"content": [{"text": "A"}, {"text": "B"}]}}]}
    assert extract_content(p2) == "AB", "分片 content 解析失败"
    p3 = {"choices": [{"message": {"content": "```text\n第01集：X\n```"}}]}
    assert extract_content(p3) == "第01集：X", "围栏剥离失败"
    p4 = {"choices": [{"message": {"content": "```\n第01集：Y\n```\n"}}]}
    assert extract_content(p4) == "第01集：Y", "无语言标记围栏剥离失败"
    p5 = {"choices": []}
    assert extract_content(p5) == "", "空 choices 应返回空串"
    print("  OK  字符串 / 分片 / 围栏 / 空响应")

    print("[self-test] 掩码：")
    m = mask("error: bad key sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 rejected", "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456")
    assert "sk-ABCDEF" not in m, "显式密钥未抹掉"
    m2 = mask("other sk-ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 here", "different-key")
    assert "sk-ABCDEF" not in m2, "兜底正则未抹掉"
    print("  OK  显式替换 + sk- 兜底正则")

    print("[self-test] 请求体构造：")
    b = build_body("m", "P", None, "high", 100, 1.0)
    assert b["messages"] == [{"role": "user", "content": "P"}], "无系统提示词时不应插入 system"
    assert b["reasoning_effort"] == "high" and b["max_tokens"] == 100
    b2 = build_body("m", "P", "S", None, 100, None)
    assert b2["messages"][0] == {"role": "system", "content": "S"}, "系统提示词未前置"
    assert "reasoning_effort" not in b2 and "temperature" not in b2, "未指定时不应带这两个字段"
    print("  OK  system 前置 / 可选字段省略")

    print("[self-test] 用量摘要：")
    u = usage_summary({"usage": {"prompt_tokens": 7, "completion_tokens": 108,
                                 "gemini_usage_metadata": {"thoughtsTokenCount": 107}},
                       "choices": [{"finish_reason": "stop"}]})
    assert u["thoughts_tokens"] == 107 and u["finish_reason"] == "stop"
    print("  OK  含 gemini_usage_metadata 的用量解析")

    print("[self-test] 仓库内密钥文件检测：")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d) / "repo"; (repo / ".git").mkdir(parents=True)
        inside = repo / "writer_key"; inside.write_text("x", encoding="utf-8")
        assert key_file_inside_repo(inside) == repo.resolve(), "仓库内密钥文件应被识别"
        outside = Path(d) / "outside_key"; outside.write_text("x", encoding="utf-8")
        assert key_file_inside_repo(outside) is None, "仓库外密钥文件不应被误判"
    print("  OK  仓库内拒绝 / 仓库外放行")

    print("[self-test] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
