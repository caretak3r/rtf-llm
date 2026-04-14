# Install Prompt Injection Defender

Install the prompt injection defender hooks into your Claude Code project.

## Instructions

Guide me through installing the prompt injection defender. Ask me:

1. **Which implementation?** Python (uv) or TypeScript (bun)
2. **Installation scope?** Project-only or user-wide
3. **Which tools to monitor?** All recommended tools or let me select

## Installation Steps

After gathering my preferences:

1. **Check prerequisites**

   - For Python: Verify `uv` is installed (`which uv`)
   - For TypeScript: Verify `bun` is installed (`which bun`)

2. **Copy hook files**

   - Copy the appropriate hook implementation to my project or user config
   - For project: `.claude/hooks/prompt-injection-defender/`
   - For user-wide: `~/.claude/hooks/prompt-injection-defender/`

3. **Copy patterns.yaml**

   - Place `patterns.yaml` alongside the hook script
   - This file contains all detection patterns

4. **Update settings configuration**

   - **IMPORTANT**: Check if `.claude/settings.local.json` exists first
   - If `settings.local.json` exists, merge hooks into THAT file (it takes precedence over `settings.json`)
   - If only `settings.json` exists, merge hooks there
   - Use the template from `python-settings.json` or `typescript-settings.json`
   - Adjust paths based on installation scope
   - For user-wide: update `~/.claude/settings.json`

   **Settings precedence (highest to lowest):**
   1. `.claude/settings.local.json` (local project - overrides all below)
   2. `.claude/settings.json` (project settings)
   3. `~/.claude/settings.json` (user settings)

5. **Restart Claude Code**
   - **CRITICAL**: Hooks are captured at session startup
   - Tell the user they MUST restart Claude Code for hooks to take effect
   - Exit the current session and start a new one

6. **Verify installation**
   - After restart, run a quick test to ensure the hook is working
   - Read a test file with known injection patterns
   - Use `/hooks` command to verify hooks are loaded

## Recommended Tool Configuration

Monitor these tools for prompt injection:

- `Read` - File contents
- `WebFetch` - Web page contents
- `Bash` - Command outputs
- `Grep` - Search results
- `Task` - Agent outputs
- `mcp__*` - All MCP tool outputs

## After Installation

**IMPORTANT**: Tell the user to restart Claude Code! Hooks only load at startup.

Explain what will happen after restart:

- When Claude reads files, fetches web pages, or runs commands
- The hook will scan the output for injection patterns
- If patterns are detected, Claude will see a warning
- Processing continues but Claude is warned to be cautious

The user can verify hooks are active by running `/hooks` in Claude Code.

## Reference Files

- Skill location: `.claude/skills/prompt-injection-defender/`
- Python hook: `hooks/defender-python/post-tool-defender.py`
- TypeScript hook: `hooks/defender-typescript/post-tool-defender.ts`
- Patterns: `patterns.yaml`
- Settings templates: `python-settings.json` / `typescript-settings.json`
