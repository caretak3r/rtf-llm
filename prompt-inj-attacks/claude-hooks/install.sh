#!/bin/bash
#
# Claude Hooks - Prompt Injection Defender Installer
# 
# Usage:
#   From claude-hooks repo:  ./install.sh /path/to/your-project
#   Or with curl:            bash <(curl -s https://raw.githubusercontent.com/lasso-security/claude-hooks/main/install.sh) /path/to/your-project
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔═══════════════════════════════════════════════════════════╗"
    echo "║        Claude Hooks - Prompt Injection Defender           ║"
    echo "╚═══════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Determine script location (claude-hooks repo root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if we're running from the claude-hooks repo
if [[ ! -f "$SCRIPT_DIR/.claude/skills/prompt-injection-defender/patterns.yaml" ]]; then
    print_error "This script must be run from the claude-hooks repository root."
    print_info "Clone the repo first: git clone https://github.com/lasso-security/claude-hooks.git"
    exit 1
fi

# Get target project directory
TARGET_PROJECT="${1:-}"

if [[ -z "$TARGET_PROJECT" ]]; then
    echo ""
    read -p "Enter the path to your project: " TARGET_PROJECT
fi

# Expand ~ to home directory
TARGET_PROJECT="${TARGET_PROJECT/#\~/$HOME}"

# Convert to absolute path
TARGET_PROJECT="$(cd "$TARGET_PROJECT" 2>/dev/null && pwd)" || {
    print_error "Directory does not exist: $TARGET_PROJECT"
    exit 1
}

print_header
echo ""
print_info "Source: $SCRIPT_DIR"
print_info "Target: $TARGET_PROJECT"
echo ""

# Check for UV
if ! command -v uv &> /dev/null; then
    print_warning "UV is not installed. Installing UV..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    print_success "UV installed"
else
    print_success "UV is already installed"
fi

# Create hooks directory
HOOKS_DIR="$TARGET_PROJECT/.claude/hooks/prompt-injection-defender"
mkdir -p "$HOOKS_DIR"
print_success "Created hooks directory: .claude/hooks/prompt-injection-defender/"

# Copy Python hook files
SOURCE_HOOKS="$SCRIPT_DIR/.claude/skills/prompt-injection-defender/hooks/defender-python"
if [[ -d "$SOURCE_HOOKS" ]]; then
    cp -r "$SOURCE_HOOKS"/* "$HOOKS_DIR/"
    print_success "Copied Python hook files"
else
    print_error "Source hook files not found at: $SOURCE_HOOKS"
    exit 1
fi

# Copy patterns.yaml
SOURCE_PATTERNS="$SCRIPT_DIR/.claude/skills/prompt-injection-defender/patterns.yaml"
if [[ -f "$SOURCE_PATTERNS" ]]; then
    cp "$SOURCE_PATTERNS" "$HOOKS_DIR/"
    print_success "Copied patterns.yaml"
else
    print_error "patterns.yaml not found at: $SOURCE_PATTERNS"
    exit 1
fi

# Make Python files executable
chmod +x "$HOOKS_DIR"/*.py 2>/dev/null || true
print_success "Made hook scripts executable"

# Create settings file if it doesn't exist
SETTINGS_DIR="$TARGET_PROJECT/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.local.json"

if [[ ! -f "$SETTINGS_FILE" ]]; then
    mkdir -p "$SETTINGS_DIR"
    cat > "$SETTINGS_FILE" << 'EOF'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt-injection-defender/post-tool-defender.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "WebFetch",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt-injection-defender/post-tool-defender.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt-injection-defender/post-tool-defender.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Grep",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt-injection-defender/post-tool-defender.py",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Task",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/prompt-injection-defender/post-tool-defender.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
EOF
    print_success "Created .claude/settings.local.json with hook configuration"
else
    print_warning "settings.local.json already exists - you may need to merge hook configuration manually"
    print_info "See INSTALLATION.md for the required hook configuration"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Installation complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
print_info "Restart Claude Code to activate the prompt injection defender."
echo ""
print_info "Files installed:"
echo "    $HOOKS_DIR/"
ls -la "$HOOKS_DIR" | tail -n +2 | awk '{print "      " $NF}'
echo ""

