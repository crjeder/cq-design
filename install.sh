#!/usr/bin/env bash
# Install the cq-design skill into the Claude Code personal skills directory.
#
# Usage:
#   ./install.sh                 Copy the skill and provision its environment
#   ./install.sh --link          Symlink the repo instead of copying
#   ./install.sh --uninstall     Remove the installed skill
#   ./install.sh --dest <dir>    Override the skills directory
#   ./install.sh --help
#
# Destination defaults to $CLAUDE_SKILLS_DIR/cq-design, or
# ~/.claude/skills/cq-design when CLAUDE_SKILLS_DIR is unset.
set -euo pipefail

SKILL_NAME="cq-design"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

EXCLUDES=(
    ".git"
    ".venv"
    "__pycache__"
    ".pytest_cache"
    ".mypy_cache"
    ".ruff_cache"
    ".cocoindex_code"
    ".sentrux"
    ".playwright-mcp"
    ".vscode"
    "debug"
    "build"
    "BUILD_PLAN.json"
)

usage() {
    sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

mode="copy"
uninstall=0
skills_dir="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

while [ $# -gt 0 ]; do
    case "$1" in
        --link) mode="link"; shift ;;
        --uninstall) uninstall=1; shift ;;
        --dest) skills_dir="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

dest="$skills_dir/$SKILL_NAME"

if [ "$uninstall" -eq 1 ]; then
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        rm -rf "$dest"
        echo "Removed $dest"
    else
        echo "Nothing to remove at $dest"
    fi
    exit 0
fi

# Preflight before touching the skills directory.
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: 'uv' is not on PATH. Install it from https://docs.astral.sh/uv/ and re-run." >&2
    exit 1
fi

mkdir -p "$skills_dir"

if [ "$mode" = "link" ]; then
    rm -rf "$dest"
    if ! ln -s "$REPO_ROOT" "$dest"; then
        echo "Error: failed to create symlink at $dest" >&2
        exit 1
    fi
    echo "Linked $dest -> $REPO_ROOT"
else
    rm -rf "$dest"
    mkdir -p "$dest"
    if command -v rsync >/dev/null 2>&1; then
        args=()
        for e in "${EXCLUDES[@]}"; do args+=(--exclude "$e"); done
        rsync -a "${args[@]}" "$REPO_ROOT/" "$dest/"
    else
        # tar fallback with the same exclusions
        args=()
        for e in "${EXCLUDES[@]}"; do args+=(--exclude="$e"); done
        tar -C "$REPO_ROOT" "${args[@]}" -cf - . | tar -C "$dest" -xf -
    fi
    echo "Copied skill to $dest"

    # Stamp the commit that was copied, so `skill_version.py` can tell a stale
    # install apart from a current one. Skipped for --link: a symlink is always
    # as current as its target, so skill_version.py reads the target's live git
    # HEAD instead.
    if command -v git >/dev/null 2>&1 && commit="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)"; then
        commit_short="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
        branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"
        if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then dirty=true; else dirty=false; fi
        installed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        cat > "$dest/.version.json" <<EOF
{
  "commit": "$commit",
  "commit_short": "$commit_short",
  "branch": "$branch",
  "dirty": $dirty,
  "installed_at": "$installed_at"
}
EOF
    else
        echo "Note: $REPO_ROOT is not a git checkout -- skipping .version.json (skill_version.py will report 'unknown')"
    fi
fi

echo "Provisioning environment with 'uv sync'..."
uv sync --project "$dest"

echo "Done. cq-design installed at $dest"
echo "Check the installed version any time with: python \"$dest/src/skill_version.py\""
