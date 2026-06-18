#!/bin/bash
# 项目级安装：将 meta-skill 安装到当前项目的 .opencode/ 目录
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DEST="$SCRIPT_DIR/.opencode/skills"
AGENT_DEST="$SCRIPT_DIR/.opencode/agents"

mkdir -p "$SKILL_DEST"
mkdir -p "$AGENT_DEST"

# 安装所有 meta-skill
for skill in skill-digest skill-evaluator skill-test-designer skill-test-runner skill-test-judge; do
  src="$SCRIPT_DIR/$skill"
  if [ -d "$src" ]; then
    cp -r "$src" "$SKILL_DEST/"
    echo "  ✓ $skill"
  else
    echo "  ✗ $skill (目录不存在，跳过)"
  fi
done

# 安装配套 subagent
if ls "$SCRIPT_DIR/agents/"*.md >/dev/null 2>&1; then
  cp "$SCRIPT_DIR/agents/"*.md "$AGENT_DEST/"
  echo "  ✓ 配套 subagent 已安装"
fi

echo ""
echo "✓ meta-skill 已安装到 $SKILL_DEST"
echo ""
echo "如需全局安装，将 .opencode/skills/ 复制到 ~/.config/opencode/skills/ 即可。"
