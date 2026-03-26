# NEXUS — AI CLI Chatbot

**Multi-provider AI chatbot for your terminal. Supports Claude, GPT-4, and Gemini.**

---

## Features

- **Multi-provider**: Switch between Claude, GPT-4o, Gemini instantly
- **Persistent chat**: Conversations saved automatically with full history
- **Text → Command**: Convert natural language to shell commands using AI
- **Output analysis**: Run commands and get AI analysis of results
- **Inline shell**: Run `!command` or `` `command` `` directly in chat
- **Voice input**: Speak instead of type (macOS/Linux with SpeechRecognition)
- **Session management**: Save, load, and browse past chat sessions
- **Rich formatting**: Code blocks, markdown, color-coded output

---

## Install

```bash
bash install.sh
source ~/.bashrc
```

---

## Setup API Keys

```bash
# Option 1: Environment variables (recommended)
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."

# Option 2: Inside NEXUS
nexus
> /keys
```

---

## Usage

```bash
nexus
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `/provider claude\|gpt\|gemini` | Switch AI provider |
| `/model gpt-4o` | Change model |
| `/cmd list all running processes by memory` | Text → shell command |
| `/analyze df -h` | Run command + AI analysis |
| `/run ls -la` | Run shell command |
| `!ls -la` | Quick shell shortcut |
| `` `ps aux` `` | Run + send output to AI |
| `/save mysession` | Save current chat |
| `/load mysession` | Load saved chat |
| `/history` | Browse saved sessions |
| `/clear` | Clear chat history |
| `/voice` | Toggle voice input |
| `/keys` | Set API keys |
| `/config` | View configuration |
| `/help` | Show help |
| `/exit` | Exit |

---

## Examples

```
nexus[claude] › show me disk usage on my system
  → AI explains + suggests commands

nexus[claude] › /cmd find all log files larger than 100MB
  Generated: find / -name "*.log" -size +100M 2>/dev/null
  Run it? [y/N]: y

nexus[claude] › /analyze docker ps -a
  → Runs docker ps -a, then AI analyzes what containers are running

nexus[claude] › /provider gpt
  ✓ Switched to GPT

nexus[gpt] › What's the best way to monitor server performance?
  → Continues conversation in context
```

---

## Config File

Located at: `~/.nexus/config.json`

```json
{
  "provider": "claude",
  "model": {
    "claude": "claude-sonnet-4-20250514",
    "gpt": "gpt-4o",
    "gemini": "gemini-1.5-flash"
  },
  "max_tokens": 2048,
  "temperature": 0.7
}
```

## Sessions

Saved at: `~/.nexus/history/`
