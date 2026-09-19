#!/usr/bin/env bash
# publish.sh — xiachen-family-drama 的安全发布器
#
# 用途：把本地提交推到 GitHub 并**从远端复验**。供「发布子代理」或人工调用。
#
# 用法：
#   ./scripts/publish.sh                 # 提交（若有改动）→ 推送 → 远端复验
#   ./scripts/publish.sh -m "提交说明"    # 指定提交说明
#   ./scripts/publish.sh --dry-run       # 只打印将要做什么，不推送
#   ./scripts/publish.sh --verify-only   # 不推送，只做远端复验
#
# token 读取顺序（**绝不写入 .git/config，绝不回显**）：
#   1) 环境变量 XIACHEN_GH_TOKEN
#   2) ~/.config/xiachen/gh_token   （推荐，600 权限，位于仓库之外）
#
# 安全约束（脚本内硬校验）：
#   - token 文件若位于本仓库内 → 直接拒绝运行（防止把密钥推上 GitHub）
#   - 推送使用一次性 URL，不落盘到 remote 配置
#   - 所有输出都经过掩码，token 不会出现在日志里
#   - 默认拒绝强推（--force 不支持，避免覆盖远端历史）

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

TOKEN_FILE="${XIACHEN_TOKEN_FILE:-$HOME/.config/xiachen/gh_token}"
REMOTE_NAME="origin"
BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null || echo main)"
MSG=""
DRY_RUN=0
VERIFY_ONLY=0

while [ $# -gt 0 ]; do
  case "$1" in
    -m|--message) MSG="${2:-}"; shift ;;
    --dry-run)    DRY_RUN=1 ;;
    --verify-only) VERIFY_ONLY=1 ;;
    -h|--help)    sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "未知参数：$1" >&2; exit 2 ;;
  esac
  shift
done

say()  { printf '%s\n' "$*"; }
die()  { printf 'FAIL  %s\n' "$*" >&2; exit 1; }
ok()   { printf 'OK    %s\n' "$*"; }

# ---------- 1. 解析 token ----------
resolve_token() {
  if [ -n "${XIACHEN_GH_TOKEN:-}" ]; then
    printf '%s' "$XIACHEN_GH_TOKEN"; return 0
  fi
  [ -f "$TOKEN_FILE" ] || return 1
  tr -d '\r\n' < "$TOKEN_FILE"
}

TOKEN="$(resolve_token)" || die "未找到 token。请设置环境变量 XIACHEN_GH_TOKEN，或写入 ${TOKEN_FILE}（chmod 600）"

# ---------- 2. 安全校验：token 文件不得位于仓库内 ----------
case "$(cd "$(dirname "$TOKEN_FILE")" 2>/dev/null && pwd)/$(basename "$TOKEN_FILE")" in
  "$REPO_ROOT"/*) die "token 文件位于仓库内（${TOKEN_FILE}）——这会把密钥推上 GitHub。请移到仓库外。" ;;
esac

# 仓库里若出现 token/key 字面量，立刻拒绝。
# ⚠️ 本段的所有前缀都必须经**变量拼接**再进模式串 —— 否则这些前缀会以字面量
#    出现在本脚本源码里，被下面第一条「长度无关」的检查当成命中而自我误报。
#    （v1.5.1 踩过一次：把 github 个人令牌的前缀连着下划线直接写进正则与注释，
#      结果连干净仓库都 FAIL。注释里也一样不能出现那种字面量。）
GH_PREFIX='gh'; GH_KINDS='pousr'
PAT_PREFIX="${GH_PREFIX}${GH_KINDS:0:1}"; PAT2_PREFIX='github_pat'
GOOG_PREFIX='AIza'; OAI_PREFIX='sk-'
KEY_RE="(${GH_PREFIX}[${GH_KINDS}]_[A-Za-z0-9]{30,}|${PAT2_PREFIX}_[A-Za-z0-9_]{30,}|${GOOG_PREFIX}[0-9A-Za-z_-]{30,}|${OAI_PREFIX}[A-Za-z0-9_-]{30,})"
if git rev-parse --git-dir >/dev/null 2>&1; then
  if git grep -qI -e "${PAT_PREFIX}_" -e "${PAT2_PREFIX}_" -- . 2>/dev/null \
     || git grep -qIE -e "$KEY_RE" -- . 2>/dev/null; then
    die "仓库已跟踪的文件里出现 token/key 字面量，先清理再发布"
  fi
  # 凭据 / 设置文件绝不允许被跟踪（.gitignore 是提示，这里是闸门）
  SUSPECT="$(git ls-files | grep -E '(^|/)(\.credentials.*|credentials\.(ya?ml|json)|settings\.ya?ml|config\.ya?ml|\.env.*|writer_?key.*|\.writer-log.*)$' || true)"
  if [ -n "$SUSPECT" ]; then
    say "以下凭据/设置文件已被 git 跟踪："
    printf '%s\n' "$SUSPECT" | sed 's/^/  /'
    die "禁止发布：请 git rm --cached 这些文件，并确认 .gitignore 生效"
  fi
fi

REMOTE_URL="$(git remote get-url "$REMOTE_NAME" 2>/dev/null)" || die "未配置远程 $REMOTE_NAME"
case "$REMOTE_URL" in *"$TOKEN"*) die "远程 URL 里嵌了 token，请先 git remote set-url 清理" ;; esac

say "仓库：$REPO_ROOT"
say "分支：$BRANCH   远程：$REMOTE_URL"
say "模式：$([ "$DRY_RUN" = 1 ] && echo 'DRY-RUN（不推送）' || ([ "$VERIFY_ONLY" = 1 ] && echo '仅复验' || echo '发布'))"
say ""

# ---------- 3. 提交本地改动 ----------
if [ "$VERIFY_ONLY" = 0 ]; then
  if [ -n "$(git status --porcelain)" ]; then
    say "待提交改动："
    git status --short | sed 's/^/  /'
    if [ -z "$MSG" ]; then
      MSG="chore: 更新 $(date '+%Y-%m-%d %H:%M')"
      say "（未指定 -m，使用默认说明：${MSG}）"
    fi
    if [ "$DRY_RUN" = 1 ]; then
      say "PLAN  git add -A && git commit -m \"$MSG\""
    else
      git add -A && git commit -q -m "$MSG" && ok "已提交"
    fi
  else
    ok "工作区干净，无需提交"
  fi
fi

LOCAL_SHA="$(git rev-parse HEAD)"

# ---------- 4. 推送（一次性 URL，不落盘） ----------
if [ "$VERIFY_ONLY" = 0 ]; then
  if [ "$DRY_RUN" = 1 ]; then
    say "PLAN  git push <一次性 token URL> $BRANCH"
  else
    OUT="$(git push "https://${TOKEN}@${REMOTE_URL#https://}" "$BRANCH" 2>&1)"
    RC=$?
    printf '%s\n' "$OUT" | sed "s/${TOKEN}/***TOKEN***/g"
    [ $RC -eq 0 ] || die "推送失败（退出码 ${RC}）"
    ok "已推送 $LOCAL_SHA"
  fi
fi
unset TOKEN

# ---------- 5. 远端复验 ----------
if [ "$DRY_RUN" = 1 ]; then say "（DRY-RUN 跳过复验）"; exit 0; fi

REMOTE_SHA="$(git ls-remote "$REMOTE_URL" "refs/heads/$BRANCH" 2>/dev/null | awk '{print $1}')"
if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
  ok "远端 $BRANCH = 本地 HEAD（${LOCAL_SHA}）"
else
  die "远端 SHA（${REMOTE_SHA}）与本地 HEAD（${LOCAL_SHA}）不一致"
fi

# 从远端真正克隆一份跑自检，验证「别人下载能不能用」
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git clone -q "$REMOTE_URL" "$TMP/repo" || die "从远端克隆失败"
ok "远端克隆成功（$(cd "$TMP/repo" && git ls-files | wc -l | tr -d ' ') 个文件）"

FAILED=0
for s in validate_episode batch_preflight check_chaining; do
  if [ -f "$TMP/repo/scripts/$s.py" ]; then
    if python3 "$TMP/repo/scripts/$s.py" --self-test >/dev/null 2>&1; then
      ok "远端 $s.py --self-test PASS"
    else
      printf 'FAIL  远端 %s.py --self-test FAIL\n' "$s"; FAILED=1
    fi
  fi
done
[ $FAILED -eq 0 ] || die "远端复验未通过"

say ""
say "发布完成：$REMOTE_URL  分支 $BRANCH  提交 $LOCAL_SHA"
