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

# Optional: Sync protected folders to external backup (if script exists)
SYNC_SCRIPT="$(dirname "$(git rev-parse --git-dir)")/../.sync-protected-folders.sh"
[ -x "$SYNC_SCRIPT" ] && "$SYNC_SCRIPT" sync 2>/dev/null &

# Only run on branch switches (not file checkouts)
if [ "$branch_switch" = "1" ]; then
    new_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    
    # Only clean when switching to a chapter branch
    if [[ "$new_branch" =~ ^chapter-[0-9]+$ ]]; then
        # Optional: Restore protected folders if missing (if script exists)
        [ -x "$SYNC_SCRIPT" ] && "$SYNC_SCRIPT" restore 2>/dev/null
        
        echo ""
        echo "🧹 Cleaning workspace for $new_branch..."
        
        # Backup .env if it exists
        [ -f .env ] && cp .env .env.bak
        
        # CRITICAL: Only clean UNTRACKED files, NEVER use -X flag
        # Clean untracked files and directories, excluding:
        # - .env.bak (temporary backup)
        # - en/ (course content folder)
        # - docs/ (documentation folder)
        # - .env_template (template file)
        git clean -fd -e .env.bak -e en/ -e docs/ -e .env_template -q
        
        # Remove ONLY __pycache__ directories, avoid en/ and docs/
        find . -type d -name "__pycache__" -not -path "./en/*" -not -path "./docs/*" -exec rm -rf {} + 2>/dev/null || true
        
        # Restore .env
        [ -f .env.bak ] && mv .env.bak .env
        
        echo "✅ Workspace cleaned for $new_branch"
        echo "   Preserved: .env, en/, docs/ folders"
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
echo "   • Preserves your docs/ folder (documentation)"
echo "   • Only removes UNTRACKED files (never touches ignored files)"
echo "   • Only activates when switching to chapter-1, chapter-2, chapter-3, etc."
echo ""
echo "🎯 Try it out:"
echo "   git checkout chapter-2"
echo "   git checkout chapter-3"
echo ""
echo "💡 The hook is now active for all future branch switches!"
echo ""
