#!/usr/bin/env bash
# run-chain.sh — runs the gate chain declared in gates/chain.conf (from the AI Factory Kit).
# "Done" means this exits 0. GATES.md §1 is the doctrine; this is the runner.
#
#   ./gates/run-chain.sh          run every slot in file order; stop at the first red
#   ./gates/run-chain.sh --list   print each slot and its state; run nothing
#
# gates/chain.conf, one slot per line (blank lines and full-line "#" comments are ignored):
#   <slot>: <shell command>   run from the project root (the directory above gates/) as
#                             bash -o pipefail -c '<command>', stdin from /dev/null;
#                             exit 0 = ok, anything else = red
#   <slot>: NA: <reason>      does not apply to this product; the reason is required and is
#                             printed on every run as N/A
#   <slot>: TODO              not wired yet: red, printed as "not wired"
# The nine standard slots — format static test build orphan-endpoints acceptance doc-sync
# spec-approval spec-numbers — must each be declared exactly once (a command, NA or TODO), so
# deleting a line cannot quietly drop a gate. Extra slots (eval, release-check, ...) may be
# added anywhere; slots run in file order. Slot names: lowercase letters, digits, hyphens.
#
# Exit: 0 green · 1 red (a slot failed or is not wired) · 2 config error (chain.conf missing
# or unparseable, a standard slot missing or declared twice, NA without a reason, every slot
# N/A — a chain that checks nothing is not green).
#
# GIT_DIR, GIT_WORK_TREE and GIT_INDEX_FILE are unset before any slot runs. Measured with
# git 2.43: a commit in a linked worktree hands the pre-commit hook GIT_DIR and GIT_INDEX_FILE
# as absolute paths. Without the unset, a slot whose tests build a scratch repository
# (git init; git add; git commit in a temp dir) committed into THIS repository instead, set
# core.bare=true on it, and the real commit then died with "cannot lock ref 'HEAD'".
#
# BLIND TO:
#   * WHAT THE COMMANDS CHECK. A slot is green when its command exits 0; "test: true" is
#     green. The chain is exactly as strong as chain.conf, which is why the careful guard asks
#     before chain.conf is edited and why a review reads it like code.
#   * WHETHER AN N/A REASON IS TRUE. It requires one and prints it every run; review judges it.
#   * THE STAGED SNAPSHOT. It checks the working tree. From the pre-commit hook, unstaged edits
#     can make it green for a commit that is red on its own; CI checks the committed tree.
#   * SLOTS AFTER THE FIRST RED. They did not run; the output lists them.
#   * ITSELF. Two-direction test: gates/run-chain.test.sh (including a real git commit refused
#     through gates/hooks/pre-commit).
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
CONF="$HERE/chain.conf"
STANDARD="format static test build orphan-endpoints acceptance doc-sync spec-approval spec-numbers"
SLOT_RX='^([a-z0-9][a-z0-9-]*)[[:space:]]*:(.*)$'

usage() { sed -n '2,/^set -uo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; }
config_error() { printf 'run-chain: gates/chain.conf: %s\n' "$*" >&2; exit 2; }
trim() { # trim <string> -> stdout, leading/trailing whitespace removed
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

MODE=run
case "${1:-}" in
  "") ;;
  --list) MODE=list ;;
  -h|--help) usage; exit 0 ;;
  *) echo "run-chain: unknown argument '$1' (try --help)" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { echo "run-chain: one argument at most (try --help)" >&2; exit 2; }

if [ ! -f "$CONF" ]; then
  config_error "not found. Copy gates/chain.conf.example to gates/chain.conf (adopt.py does this)."
fi

# ---- parse ------------------------------------------------------------------------------
NAMES=(); KINDS=(); VALUES=()
count=0; lineno=0
while IFS= read -r line || [ -n "$line" ]; do
  lineno=$((lineno + 1))
  line="${line%$'\r'}"
  text="$(trim "$line")"
  case "$text" in ''|'#'*) continue ;; esac
  if [[ "$text" =~ $SLOT_RX ]]; then
    name="${BASH_REMATCH[1]}"
    value="$(trim "${BASH_REMATCH[2]}")"
  else
    config_error "line $lineno: expected '<slot>: <command>' (slot = lowercase letters, digits, hyphens), got: $text"
  fi
  i=0
  while [ "$i" -lt "$count" ]; do
    [ "${NAMES[$i]}" = "$name" ] && config_error "line $lineno: slot '$name' is declared twice"
    i=$((i + 1))
  done
  case "$value" in
    '')
      config_error "line $lineno: slot '$name' is empty - write a command, 'NA: <reason>' or 'TODO'" ;;
    TODO|TODO:*|'TODO '*)
      kind=todo ;;
    NA:*)
      kind=na
      value="$(trim "${value#NA:}")"
      [ -n "$value" ] || config_error "line $lineno: slot '$name' is NA without a reason - write 'NA: <reason>'" ;;
    NA|'NA '*|N/A*|n/a*|na:*|Na:*)
      config_error "line $lineno: slot '$name': write 'NA: <reason>' exactly (got: $value)" ;;
    *)
      kind=cmd ;;
  esac
  NAMES[count]="$name"; KINDS[count]="$kind"; VALUES[count]="$value"
  count=$((count + 1))
done < "$CONF"

missing=""
for want in $STANDARD; do
  found=0; i=0
  while [ "$i" -lt "$count" ]; do
    [ "${NAMES[$i]}" = "$want" ] && found=1
    i=$((i + 1))
  done
  [ "$found" -eq 1 ] || missing="$missing $want"
done
[ -z "$missing" ] || config_error "standard slot(s) not declared:$missing - declare each one: a command, 'NA: <reason>' or 'TODO'"

n_cmd=0; n_na=0; n_todo=0; i=0
while [ "$i" -lt "$count" ]; do
  case "${KINDS[$i]}" in cmd) n_cmd=$((n_cmd + 1)) ;; na) n_na=$((n_na + 1)) ;; todo) n_todo=$((n_todo + 1)) ;; esac
  i=$((i + 1))
done
[ $((n_cmd + n_todo)) -gt 0 ] || config_error "every slot is N/A - a chain that checks nothing is not green"

# ---- --list -------------------------------------------------------------------------------
if [ "$MODE" = list ]; then
  printf 'gates/chain.conf: %d slots - %d wired, %d N/A, %d not wired\n' "$count" "$n_cmd" "$n_na" "$n_todo"
  i=0
  while [ "$i" -lt "$count" ]; do
    case "${KINDS[$i]}" in
      cmd)  printf '  %-18s run      %s\n' "${NAMES[$i]}" "${VALUES[$i]}" ;;
      na)   printf '  %-18s N/A      %s\n' "${NAMES[$i]}" "${VALUES[$i]}" ;;
      todo) printf '  %-18s TODO     not wired\n' "${NAMES[$i]}" ;;
    esac
    i=$((i + 1))
  done
  exit 0
fi

# ---- run ----------------------------------------------------------------------------------
cd "$ROOT" || config_error "cannot cd to the project root $ROOT"
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE

red() { # red <index> <why>
  local k="$1" why="$2" rest="" j
  printf '[%d/%d] %s: RED - %s\n' "$((k + 1))" "$count" "${NAMES[$k]}" "$why"
  j=$((k + 1))
  while [ "$j" -lt "$count" ]; do rest="$rest ${NAMES[$j]}"; j=$((j + 1)); done
  [ -z "$rest" ] || printf '      not run:%s\n' "$rest"
  printf "GATE RED at '%s' - no commit on red. Fix it, or explicitly revert (GATES.md section 1).\n" "${NAMES[$k]}"
  exit 1
}

printf 'gate chain: %d slots from gates/chain.conf (%d wired, %d N/A, %d not wired)\n' "$count" "$n_cmd" "$n_na" "$n_todo"
ran=0; i=0
while [ "$i" -lt "$count" ]; do
  name="${NAMES[$i]}"; value="${VALUES[$i]}"
  case "${KINDS[$i]}" in
    na)
      printf '[%d/%d] %s: N/A - %s\n' "$((i + 1))" "$count" "$name" "$value" ;;
    todo)
      red "$i" "not wired (TODO) - put its command in gates/chain.conf, or 'NA: <reason>'" ;;
    cmd)
      printf '[%d/%d] %s: $ %s\n' "$((i + 1))" "$count" "$name" "$value"
      "${BASH:-bash}" -o pipefail -c "$value" </dev/null
      rc=$?
      if [ "$rc" -ne 0 ]; then
        case "$rc" in
          126) red "$i" "exit 126 - a script it runs is not executable? chmod +x it, and git update-index --chmod=+x so clones get the bit" ;;
          127) red "$i" "exit 127 - command not found" ;;
          *)   red "$i" "exit $rc" ;;
        esac
      fi
      ran=$((ran + 1))
      printf '[%d/%d] %s: ok\n' "$((i + 1))" "$count" "$name" ;;
  esac
  i=$((i + 1))
done
printf 'GATE GREEN - %d ran, %d N/A\n' "$ran" "$n_na"
exit 0
