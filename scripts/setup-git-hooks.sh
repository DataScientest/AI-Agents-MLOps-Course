#!/bin/bash
#
# Git Hook Installer for AI Agents MLOps Course
# This script installs a post-checkout hook that automatically cleans
# the workspace when switching between chapter branches.
#
# Usage: bash scripts/setup-git-hooks.sh
#

set -e

HOOK_DIR=".git/hooks"
HOOK_FILE="$HOOK_DIR/post-checkout"

echo ""
echo "🔧 Installing Git hooks for AI Agents MLOps Course..."
echo ""

# Ensure hooks directory exists
mkdir -p "$HOOK_DIR"

# Create the post-checkout hook
cat > "$HOOK_FILE" << 'EOF'
#!/bin/bash
#
# Post-checkout hook for AI Agents MLOps Course
# Automatically cleans workspace when switching to chapter branches
# while preserving .env and en/ folder
#

prev_ref=$1
new_ref=$2
branch_switch=$3

# Only run on branch switches (not file checkouts)
if [ "$branch_switch" = "1" ]; then
    new_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    
    # Only clean when switching to a chapter branch
    if [[ "$new_branch" =~ ^chapter-[0-9]+$ ]]; then
        echo ""
        echo "🧹 Cleaning workspace for $new_branch..."
        
        # Backup .env if it exists
        [ -f .env ] && cp .env .env.bak
        
        # Clean untracked files and directories, excluding:
        # - .env.bak (temporary backup)
        # - en/ (course content folder)
        # - .env_template (template file)
        git clean -fd -e .env.bak -e en/ -e .env_template -q
        
        # Remove __pycache__ directories (ignored files)
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        
        # Restore .env
        [ -f .env.bak ] && mv .env.bak .env
        
        echo "✅ Workspace cleaned for $new_branch"
        echo "   Preserved: .env, en/ folder"
        echo ""
    fi
fi
EOF

# Make the hook executable
chmod +x "$HOOK_FILE"

echo "✅ Git hook installed successfully!"
echo ""
echo "📋 What this does:"
echo "   • Automatically cleans workspace when switching chapter branches"
echo "   • Preserves your .env file (API keys)"
echo "   • Preserves your en/ folder (course content)"
echo "   • Only activates when switching to chapter-1, chapter-2, chapter-3, etc."
echo ""
echo "🎯 Try it out:"
echo "   git checkout chapter-2"
echo "   git checkout chapter-3"
echo ""
echo "💡 The hook is now active for all future branch switches!"
echo ""
