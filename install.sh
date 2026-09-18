#!/usr/bin/env bash
# install.sh — 把 xiachen-family-drama 安装到各 agent harness 的 skills 目录
#
# 用法：
#   ./install.sh                    # 自动探测已存在的 harness，软链安装
#   ./install.sh --copy             # 复制而非软链
#   ./install.sh --target DIR       # 只装到指定目录（DIR 为 skills 目录本身）
#   ./install.sh --list             # 只列出会做什么，不实际改动（同 DRY_RUN=1）
#   ./install.sh --uninstall        # 移除本脚本创建的所有链接/副本
#
# 环境变量：
#   DSH_HOME    (默认 ~/.dsh)       AGENTS_HOME (默认 ~/.agents)
#   CLAUDE_HOME (默认 ~/.claude)    CODEX_HOME  (默认 ~/.codex)
#   DRY_RUN=1   预览，不做实际改动
#
# 语义：幂等。只管理自己创建的链接/副本；目标位置若已是「真实目录」或
#       指向别处的链接，一律跳过并报告，绝不覆盖。

set -euo pipefail

SKILL_NAME="xiachen-family-drama"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DSH_HOME="${DSH_HOME:-$HOME/.dsh}"
AGENTS_HOME="${AGENTS_HOME:-$HOME/.agents}"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"

MODE="link"          # link | copy
DRY_RUN="${DRY_RUN:-0}"
ACTION="install"     # install | uninstall
declare -a TARGETS=()
EXPLICIT_TARGET=""

# ---------- 参数 ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --copy)      MODE="copy" ;;
    --link)      MODE="link" ;;
    --list)      DRY_RUN=1 ;;
    --dry-run)   DRY_RUN=1 ;;
    --uninstall) ACTION="uninstall" ;;
    --target)    shift; EXPLICIT_TARGET="${1:-}" ;;
    -h|--help)   sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数：$1（用 --help 查看用法）" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*" >&2; }
plan() { printf 'PLAN  %s\n' "$*"; }
ok()   { printf 'OK    %s\n' "$*"; }
skip() { printf 'SKIP  %s\n' "$*"; }

# ---------- 收集目标 ----------
collect_targets() {
  if [ -n "$EXPLICIT_TARGET" ]; then
    TARGETS=("$EXPLICIT_TARGET")
    return
  fi
  local found=0
  for home in "$AGENTS_HOME" "$DSH_HOME" "$CLAUDE_HOME" "$CODEX_HOME"; do
    if [ -d "$home" ]; then
      TARGETS+=("$home/skills")
      found=1
    fi
  done
  if [ "$found" -eq 0 ]; then
    warn "未探测到任何已安装的 harness（$AGENTS_HOME / $DSH_HOME / $CLAUDE_HOME / $CODEX_HOME 都不存在）"
    say  "      默认安装到 $AGENTS_HOME/skills（DeepSeek Harness 用户级 skills 根）"
    TARGETS=("$AGENTS_HOME/skills")
  fi
}

# ---------- 安装 ----------
install_one() {
  local skills_dir="$1"
  local dest="$skills_dir/$SKILL_NAME"

  if [ -L "$dest" ]; then
    local cur; cur="$(readlink "$dest")"
    if [ "$cur" = "$SRC" ]; then
      ok "已是最新链接：$dest"
    else
      skip "$dest 已存在且指向别处（$cur），不覆盖。如需替换请先手动删除。"
    fi
    return
  fi
  if [ -e "$dest" ]; then
    skip "$dest 已存在真实文件/目录，不覆盖（可能是手动安装的版本）。"
    return
  fi
  if [ ! -d "$skills_dir" ]; then
    if [ "$DRY_RUN" = "1" ]; then plan "mkdir -p $skills_dir"; else mkdir -p "$skills_dir"; fi
  fi

  if [ "$MODE" = "copy" ]; then
    if [ "$DRY_RUN" = "1" ]; then plan "cp -R $SRC -> $dest"; else
      cp -R "$SRC" "$dest"
      rm -rf "$dest/.git"
      ok "已复制到 $dest"
    fi
  else
    if [ "$DRY_RUN" = "1" ]; then plan "ln -s $SRC -> $dest"; else
      ln -s "$SRC" "$dest"
      ok "已链接 $dest -> $SRC"
    fi
  fi
}

# ---------- 卸载 ----------
uninstall_one() {
  local skills_dir="$1"
  local dest="$skills_dir/$SKILL_NAME"
  if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$SRC" ]; then
    if [ "$DRY_RUN" = "1" ]; then plan "rm $dest"; else rm "$dest"; ok "已移除链接 $dest"; fi
  elif [ -e "$dest" ]; then
    skip "$dest 不是本脚本创建的链接，未删除（若为 --copy 安装请手动删除）。"
  else
    skip "$dest 不存在，无需处理。"
  fi
}

# ---------- 主流程 ----------
collect_targets

say "xiachen-family-drama 安装器"
say "  源目录：$SRC"
say "  模式：$MODE$([ "$DRY_RUN" = "1" ] && echo "（DRY_RUN，仅预览）")"
say "  目标："
for t in "${TARGETS[@]}"; do say "    - $t/$SKILL_NAME"; done
say ""

for t in "${TARGETS[@]}"; do
  if [ "$ACTION" = "uninstall" ]; then uninstall_one "$t"; else install_one "$t"; fi
done

say ""
if [ "$DRY_RUN" = "1" ]; then
  say "以上为预览。去掉 DRY_RUN / --list 后重新执行即可生效。"
else
  say "完成。验证："
  say "  python3 \"$SRC/scripts/validate_episode.py\" --self-test"
  say "  python3 \"$SRC/scripts/batch_preflight.py\" --self-test"
  say "然后在 agent 中新开一个会话，说「写个婆媳短剧」应能触发本 skill。"
fi
