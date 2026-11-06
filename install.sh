#!/usr/bin/env bash
# Install the cq-design skill into the Claude Code personal skills directory.
#
# Usage:
#   ./install.sh                 Copy the skill and provision its environment
#   ./install.sh --link          Symlink the repo instead of copying
#   ./install.sh --uninstall     Remove the installed skill
#   ./install.sh --dest <dir>    Override the skills directory
#   (agents go to $CLAUDE_AGENTS_DIR, default: <skills dir>/../agents)
#   ./install.sh --help
#
# Destination defaults to $CLAUDE_SKILLS_DIR/cq-design, or
# ~/.claude/skills/cq-design when CLAUDE_SKILLS_DIR is unset.
set -euo pipefail

SKILL_NAME="cq-design"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Copied into a copy install; everything else in the repo is dev-only.
ALLOWLIST=(
    SKILL.md .claude-plugin agents commands skill prompts reference src templates
    pyproject.toml uv.lock .python-version LICENSE
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
# Agents are also placed in the personal agents directory (sibling of the skills dir) so
# they load even when a skills-dir copy does not expose agents/. Local only, no marketplace.
agents_dir="${CLAUDE_AGENTS_DIR:-$(dirname "$skills_dir")/agents}"

remove_agents() {
    for f in "$REPO_ROOT"/agents/*.md; do
        rm -f "$agents_dir/cq-design-$(basename "$f")"
    done
}

if [ "$uninstall" -eq 1 ]; then
    remove_agents
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
    for e in "${ALLOWLIST[@]}"; do
        if [ -e "$REPO_ROOT/$e" ]; then cp -R "$REPO_ROOT/$e" "$dest/"; fi
    done
    find "$dest" -type d \( -name __pycache__ -o -name '*.egg-info' -o -name .fossil \) \
        -prune -exec rm -rf {} +
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

mkdir -p "$agents_dir"
for f in "$REPO_ROOT"/agents/*.md; do
    cp "$f" "$agents_dir/cq-design-$(basename "$f")"
done
echo "Copied agents to $agents_dir"

echo "Provisioning environment with 'uv sync'..."
uv sync --project "$dest"

echo "Done. cq-design installed at $dest"
echo "Check the installed version any time with: python \"$dest/src/skill_version.py\""
