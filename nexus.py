#!/usr/bin/env python3
"""
NEXUS - AI CLI Chatbot
Supports: Claude | GPT | Gemini
Features: Natural language → command, output analysis, persistent chat history, voice input
"""

import os, sys, json, re, time, subprocess, shutil, textwrap, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
CONFIG_DIR  = Path.home() / ".nexus"
HISTORY_DIR = CONFIG_DIR / "history"
CONFIG_FILE = CONFIG_DIR / "config.json"
CONFIG_DIR.mkdir(exist_ok=True)
HISTORY_DIR.mkdir(exist_ok=True)

DEFAULT_CONFIG = {
    "provider": "claude",
    "model": {
        "claude": "claude-sonnet-4-20250514",
        "gpt":    "gpt-4o",
        "gemini": "gemini-2.0-flash-lite"
    },
    "api_keys": {
        "claude": "",
        "gpt":    "",
        "gemini": ""
    },
    "max_tokens": 2048,
    "temperature": 0.7,
    "voice_enabled": False
}

# ─── ANSI Colors ──────────────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; ITALIC="\033[3m"
BLACK="\033[30m"; RED="\033[91m"; GREEN="\033[92m"; YELLOW="\033[93m"
BLUE="\033[94m"; MAGENTA="\033[95m"; CYAN="\033[96m"; WHITE="\033[97m"
BG_BLACK="\033[40m"; BG_BLUE="\033[44m"

def c(col, txt): return f"{col}{txt}{R}"
def box(text, color=CYAN, width=60):
    line = color + "─" * width + R
    print(line)
    for ln in text.split("\n"):
        print(f"{color}│{R} {ln}")
    print(line)

# ─── Banner ───────────────────────────────────────────────────────────────────
BANNER = f"""
{CYAN}{BOLD}
  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝{R}
{DIM}  AI CLI Chatbot · Claude · GPT · Gemini · v2.0{R}
"""

HELP_TEXT = f"""
{BOLD}{CYAN}Commands:{R}
  {GREEN}/provider{R} [claude|gpt|gemini]  — Switch AI provider
  {GREEN}/model{R} [name]                  — Change model
  {GREEN}/clear{R}                         — Clear chat history
  {GREEN}/history{R}                       — Show chat sessions
  {GREEN}/load{R} [session_name]           — Load saved session
  {GREEN}/save{R} [name]                   — Save current session
  {GREEN}/run{R} [command]                 — Run a shell command
  {GREEN}/analyze{R} [command]             — Run & AI-analyze output
  {GREEN}/cmd{R} [description]             — Convert text → command
  {GREEN}/keys{R}                          — Set API keys
  {GREEN}/config{R}                        — Show config
  {GREEN}/voice{R}                         — Toggle voice mode (macOS/Linux)
  {GREEN}/help{R}                          — Show this help
  {GREEN}/exit{R}                          — Exit

{BOLD}{CYAN}Natural Language:{R}
  Just type anything — NEXUS will respond using the active AI.
  Wrap in {YELLOW}``{R} to run shell commands inline.
  Start with {YELLOW}!{R} to run a shell command directly.
"""

# ─── Config Manager ───────────────────────────────────────────────────────────
class Config:
    def __init__(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                saved = json.load(f)
            self.data = {**DEFAULT_CONFIG, **saved}
            # Merge nested dicts
            for k in ["model", "api_keys"]:
                self.data[k] = {**DEFAULT_CONFIG[k], **saved.get(k, {})}
        else:
            self.data = dict(DEFAULT_CONFIG)
        # Override from env
        for provider, env in [("claude","ANTHROPIC_API_KEY"),("gpt","OPENAI_API_KEY"),("gemini","GEMINI_API_KEY")]:
            val = os.environ.get(env, "")
            if val:
                self.data["api_keys"][provider] = val
        self.save()

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=2)

    def get(self, *keys):
        d = self.data
        for k in keys: d = d[k]
        return d

    def set(self, value, *keys):
        d = self.data
        for k in keys[:-1]: d = d[k]
        d[keys[-1]] = value
        self.save()

# ─── AI Providers ─────────────────────────────────────────────────────────────
def call_claude(messages, config):
    key = config.get("api_keys", "claude")
    if not key: raise ValueError("Claude API key not set. Use /keys")
    payload = json.dumps({
        "model":      config.get("model", "claude"),
        "max_tokens": config.get("max_tokens"),
        "messages":   messages
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         key,
            "anthropic-version": "2023-06-01"
        }
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["content"][0]["text"]

def call_gpt(messages, config):
    key = config.get("api_keys", "gpt")
    if not key: raise ValueError("OpenAI API key not set. Use /keys")
    payload = json.dumps({
        "model":       config.get("model", "gpt"),
        "messages":    messages,
        "max_tokens":  config.get("max_tokens"),
        "temperature": config.get("temperature")
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]

def call_gemini(messages, config):
    key = config.get("api_keys", "gemini")
    if not key: raise ValueError("Gemini API key not set. Use /keys")
    model = config.get("model", "gemini")
    # Fallback model list — tried in order if previous fails
    FALLBACK_MODELS = [
        "gemini-2.0-flash-lite",
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-2.5-flash",
    ]
    if not model.startswith("gemini") or model in ("gemini-1.5-flash", "gemini-1.5-pro"):
        model = FALLBACK_MODELS[0]
    # Build contents — Gemini needs alternating user/model
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += "\n" + m["content"]
        else:
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    if not contents or contents[0]["role"] != "user":
        contents.insert(0, {"role": "user", "parts": [{"text": "Hello"}]})
    payload = json.dumps({
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.7}
    }).encode()
    # Try model, fallback on 503/429/404
    models_to_try = [model] + [m for m in FALLBACK_MODELS if m != model]
    last_err = None
    for attempt_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{attempt_model}:generateContent"
        req = urllib.request.Request(url, data=payload, headers={
            "Content-Type": "application/json",
            "X-goog-api-key": key
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode()
            try:
                msg = json.loads(err_body).get("error", {}).get("message", err_body[:200])
            except:
                msg = err_body[:200]
            last_err = f"Gemini API error {e.code} ({attempt_model}): {msg}"
            if e.code in (503, 429, 404):
                continue  # try next model
            raise ValueError(last_err)
        except Exception as e:
            last_err = str(e)
            continue
    raise ValueError(f"All Gemini models failed. Last error: {last_err}")

PROVIDERS = {"claude": call_claude, "gpt": call_gpt, "gemini": call_gemini}

PROVIDER_COLORS = {"claude": MAGENTA, "gpt": GREEN, "gemini": BLUE}
PROVIDER_ICONS  = {"claude": "◆", "gpt": "⬡", "gemini": "✦"}

# ─── Chat Session ─────────────────────────────────────────────────────────────
class ChatSession:
    def __init__(self, config):
        self.config   = config
        self.messages = []
        self.session_name = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.system = (
            "You are NEXUS, an expert AI assistant living in the terminal. "
            "You help users with: coding, shell commands, system analysis, debugging, and general questions. "
            "When showing commands, wrap them in ```bash code blocks. "
            "Be concise but thorough. Format output clearly for a terminal display."
        )

    def add(self, role, content):
        self.messages.append({"role": role, "content": content})

    def ask(self, user_input):
        self.add("user", user_input)
        provider = self.config.get("provider")
        fn = PROVIDERS.get(provider)
        if not fn:
            raise ValueError(f"Unknown provider: {provider}")
        # Claude uses system separately, others get it prepended
        msgs = self.messages
        if provider != "claude" and self.system:
            msgs = [{"role": "user", "content": f"[System: {self.system}]\n\nUser: {user_input}"}] + self.messages[:-1] + [self.messages[-1]]

        if provider == "claude":
            payload_msgs = msgs
            # Add system param separately in call_claude if needed
            key = self.config.get("api_keys", "claude")
            if not key: raise ValueError("Claude API key not set. Use /keys")
            payload = json.dumps({
                "model":      self.config.get("model", "claude"),
                "max_tokens": self.config.get("max_tokens"),
                "system":     self.system,
                "messages":   payload_msgs
            }).encode()
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01"
                }
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            reply = data["content"][0]["text"]
        else:
            reply = fn(msgs, self.config)

        self.add("assistant", reply)
        return reply

    def save(self, name=None):
        name = name or self.session_name
        path = HISTORY_DIR / f"{name}.json"
        with open(path, "w") as f:
            json.dump({"name": name, "messages": self.messages, "created": str(datetime.now())}, f, indent=2)
        return path

    def load(self, name):
        path = HISTORY_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"Session '{name}' not found")
        with open(path) as f:
            data = json.load(f)
        self.messages = data["messages"]
        self.session_name = data["name"]

# ─── Output Renderer ──────────────────────────────────────────────────────────
def render_response(text, provider):
    col = PROVIDER_COLORS.get(provider, CYAN)
    icon = PROVIDER_ICONS.get(provider, "◈")
    width = min(shutil.get_terminal_size().columns - 4, 100)

    print(f"\n{col}{BOLD}{icon} {provider.upper()}{R}{DIM}  ────────────────────────────{R}")

    # Parse code blocks
    parts = re.split(r"(```[\w]*\n[\s\S]*?```)", text)
    for part in parts:
        if part.startswith("```"):
            # Code block
            lang_match = re.match(r"```(\w*)\n", part)
            lang = lang_match.group(1) if lang_match else ""
            code = re.sub(r"```\w*\n|```$", "", part).strip()
            lang_label = f" {lang} " if lang else " code "
            print(f"\n  {YELLOW}╭─{lang_label}{'─'*max(0,40-len(lang_label))}╮{R}")
            for line in code.split("\n"):
                print(f"  {YELLOW}│{R} {GREEN}{line}{R}")
            print(f"  {YELLOW}╰{'─'*42}╯{R}\n")
        else:
            # Regular text — wrap nicely
            lines = part.strip().split("\n")
            for line in lines:
                if line.startswith("# "):
                    print(f"\n  {BOLD}{CYAN}{line[2:]}{R}")
                elif line.startswith("## "):
                    print(f"\n  {BOLD}{line[3:]}{R}")
                elif line.startswith("- ") or line.startswith("* "):
                    print(f"  {CYAN}•{R} {line[2:]}")
                elif re.match(r"^\d+\. ", line):
                    num, rest = line.split(". ", 1)
                    print(f"  {CYAN}{num}.{R} {rest}")
                elif line.startswith("**") and line.endswith("**"):
                    print(f"  {BOLD}{line[2:-2]}{R}")
                elif line == "":
                    print()
                else:
                    # Word wrap long lines
                    wrapped = textwrap.fill(line, width=width-4, initial_indent="  ", subsequent_indent="  ")
                    print(wrapped)

    print(f"\n{DIM}{'─'*40}{R}")

def render_command_output(cmd, output, exit_code):
    col = GREEN if exit_code == 0 else RED
    status = "✓ OK" if exit_code == 0 else f"✗ exit {exit_code}"
    print(f"\n{YELLOW}╭─ $ {cmd} ──── {col}{status}{R}{YELLOW} ─╮{R}")
    for line in output.strip().split("\n")[:50]:  # limit 50 lines
        print(f"{YELLOW}│{R}  {line}")
    if output.count("\n") > 50:
        print(f"{YELLOW}│{R}  {DIM}... (truncated){R}")
    print(f"{YELLOW}╰{'─'*50}╯{R}")

# ─── Command Converter ────────────────────────────────────────────────────────
CMD_SYSTEM = """You are a shell command expert. Convert natural language to shell commands.
Return ONLY the command(s), no explanation. Use bash syntax.
If multiple commands needed, chain with && or show separately.
Example:
User: show me all python files modified today
Answer: find . -name "*.py" -newer $(date -d 'today 00:00' +%Y%m%d) 2>/dev/null || find . -name "*.py" -mtime -1"""

def text_to_command(description, session):
    """Convert natural language description to shell command using AI."""
    old_msgs = session.messages.copy()
    old_system = session.system
    try:
        session.system = CMD_SYSTEM
        session.messages = []
        cmd = session.ask(description)
    finally:
        session.messages = old_msgs
        session.system = old_system
    # Clean up
    cmd = cmd.strip().strip("`").strip()
    if cmd.startswith("bash\n"):
        cmd = cmd[5:]
    return cmd

# ─── Output Analyzer ──────────────────────────────────────────────────────────
def analyze_output(cmd, output, exit_code, session):
    """Ask AI to analyze command output."""
    analysis_prompt = f"""Analyze this terminal command and its output:

Command: {cmd}
Exit code: {exit_code}
Output:
```
{output[:3000]}
```

Provide:
1. What this output means
2. Any warnings or errors detected
3. Key findings or metrics
4. Suggested next steps (if any)

Be concise and terminal-friendly."""

    return session.ask(analysis_prompt)

# ─── Voice Input (macOS/Linux) ─────────────────────────────────────────────────
def voice_input():
    """Try to capture voice input. Returns text or None."""
    # macOS
    if sys.platform == "darwin":
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'set t to (do shell script "say -v Zoe \'Listening...\'")\n'
                 'tell application "SpeechRecognitionServer"\n  listen\nend tell'],
                capture_output=True, text=True, timeout=10
            )
            return result.stdout.strip() or None
        except:
            pass
    # Linux with sox/speech-recognition
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print(c(CYAN, "  🎤 Listening..."))
            audio = r.listen(source, timeout=5)
        return r.recognize_google(audio)
    except ImportError:
        print(c(YELLOW, "  [!] Install SpeechRecognition: pip install SpeechRecognition pyaudio"))
    except Exception as e:
        print(c(RED, f"  [!] Voice error: {e}"))
    return None

# ─── Shell Runner ─────────────────────────────────────────────────────────────
def run_shell(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    output = result.stdout + result.stderr
    return output, result.returncode

# ─── Keys Setup ───────────────────────────────────────────────────────────────
def setup_keys(config):
    print(f"\n{BOLD}{CYAN}API Keys Setup{R}")
    print(f"{DIM}Press Enter to keep current value{R}\n")
    for provider, env in [("claude","ANTHROPIC_API_KEY"),("gpt","OPENAI_API_KEY"),("gemini","GEMINI_API_KEY")]:
        current = config.get("api_keys", provider)
        masked = f"{'*'*8}{current[-4:]}" if len(current) > 4 else "(not set)"
        try:
            val = input(f"  {PROVIDER_COLORS[provider]}{provider.upper()}{R} key [{masked}]: ").strip()
            if val:
                config.set(val, "api_keys", provider)
                print(f"  {GREEN}✓ Saved{R}")
        except (KeyboardInterrupt, EOFError):
            break
    print()

# ─── Spinner ──────────────────────────────────────────────────────────────────
def spinner_start(msg="Thinking"):
    import threading
    stop_event = threading.Event()
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    def _spin():
        i = 0
        while not stop_event.is_set():
            sys.stdout.write(f"\r  {CYAN}{frames[i % len(frames)]}{R} {DIM}{msg}...{R}  ")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write("\r" + " " * 40 + "\r")
        sys.stdout.flush()
    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    return stop_event

# ─── Prompt ───────────────────────────────────────────────────────────────────
def get_prompt(provider, voice_mode=False):
    col = PROVIDER_COLORS.get(provider, CYAN)
    icon = PROVIDER_ICONS.get(provider, "◈")
    voice_str = f" {MAGENTA}🎤{R}" if voice_mode else ""
    return f"\n{col}{BOLD}{icon} nexus{R}{DIM}[{provider}]{R}{voice_str} {CYAN}›{R} "

# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    print(BANNER)
    config  = Config()
    session = ChatSession(config)
    voice_mode = config.data.get("voice_enabled", False)

    provider = config.get("provider")
    print(f"  {DIM}Provider: {PROVIDER_COLORS[provider]}{provider.upper()}{R}  "
          f"{DIM}Model: {config.get('model', provider)}{R}")

    # Warn if no API key for current provider
    current_key = config.get("api_keys", provider)
    if not current_key:
        print(f"  {YELLOW}⚠  No API key for {provider.upper()}!{R}")
        has_any = False
        for p in PROVIDERS:
            k = config.get("api_keys", p)
            if k:
                print(f"    {GREEN}✓{R} {PROVIDER_COLORS[p]}{p}{R} — has key, use: /provider {p}")
                has_any = True
        if not has_any:
            print(f"  {RED}  No API keys set. Run /keys or set env vars.{R}")
            print(f"  {CYAN}  Free Gemini key → https://aistudio.google.com/app/apikey{R}")
        print()
    print(f"  {DIM}Type {GREEN}/help{R}{DIM} for commands. {GREEN}/keys{R}{DIM} to set API keys.{R}\n")

    while True:
        try:
            if voice_mode:
                print(get_prompt(config.get("provider"), voice_mode), end="", flush=True)
                user_input = voice_input() or ""
                if user_input:
                    print(c(WHITE, user_input))
                else:
                    user_input = input("").strip()
            else:
                user_input = input(get_prompt(config.get("provider"))).strip()

        except (KeyboardInterrupt, EOFError):
            print(f"\n\n  {DIM}Goodbye. Session saved.{R}")
            session.save()
            break

        if not user_input:
            continue

        # ── Built-in commands ──────────────────────────────────────────────
        if user_input.startswith("/"):
            parts = user_input.split(maxsplit=1)
            cmd   = parts[0].lower()
            arg   = parts[1] if len(parts) > 1 else ""

            if cmd == "/exit":
                print(f"\n  {DIM}Goodbye!{R}")
                session.save()
                break

            elif cmd == "/help":
                print(HELP_TEXT)

            elif cmd == "/provider":
                if arg in PROVIDERS:
                    config.set(arg, "provider")
                    session.config = config
                    print(f"  {GREEN}✓ Switched to {PROVIDER_COLORS[arg]}{arg.upper()}{R}")
                else:
                    print(f"  {RED}✗ Unknown provider. Options: {', '.join(PROVIDERS.keys())}{R}")

            elif cmd == "/model":
                if arg:
                    provider = config.get("provider")
                    config.set(arg, "model", provider)
                    print(f"  {GREEN}✓ Model set to: {arg}{R}")
                else:
                    for p in PROVIDERS:
                        print(f"  {PROVIDER_COLORS[p]}{p}{R}: {config.get('model', p)}")

            elif cmd == "/clear":
                session.messages = []
                print(f"  {GREEN}✓ Chat history cleared{R}")

            elif cmd == "/keys":
                setup_keys(config)

            elif cmd == "/config":
                print(f"\n{BOLD}Current Config:{R}")
                print(json.dumps({k: v for k, v in config.data.items() if k != "api_keys"}, indent=2))
                keys_status = {p: "✓ set" if config.get("api_keys", p) else "✗ not set"
                               for p in PROVIDERS}
                print(f"\n{BOLD}API Keys:{R} {json.dumps(keys_status, indent=2)}\n")

            elif cmd == "/history":
                sessions = sorted(HISTORY_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
                if sessions:
                    print(f"\n{BOLD}Saved Sessions:{R}")
                    for i, s in enumerate(sessions[:10], 1):
                        mtime = datetime.fromtimestamp(s.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                        print(f"  {CYAN}{i}.{R} {s.stem}  {DIM}{mtime}{R}")
                else:
                    print(f"  {DIM}No saved sessions.{R}")

            elif cmd == "/load":
                try:
                    session.load(arg)
                    print(f"  {GREEN}✓ Loaded session: {arg} ({len(session.messages)} messages){R}")
                except FileNotFoundError as e:
                    print(f"  {RED}✗ {e}{R}")

            elif cmd == "/save":
                path = session.save(arg or None)
                print(f"  {GREEN}✓ Session saved: {path}{R}")

            elif cmd == "/voice":
                voice_mode = not voice_mode
                config.set(voice_mode, "voice_enabled")
                state = f"{GREEN}ON{R}" if voice_mode else f"{RED}OFF{R}"
                print(f"  Voice mode: {state}")

            elif cmd == "/run":
                if arg:
                    print(f"  {DIM}Running...{R}")
                    output, code = run_shell(arg)
                    render_command_output(arg, output, code)
                else:
                    print(f"  {RED}Usage: /run [command]{R}")

            elif cmd == "/analyze":
                if arg:
                    print(f"  {DIM}Running command...{R}")
                    output, code = run_shell(arg)
                    render_command_output(arg, output, code)
                    stop = spinner_start("Analyzing")
                    try:
                        analysis = analyze_output(arg, output, code, session)
                    finally:
                        stop.set()
                    render_response(analysis, config.get("provider"))
                else:
                    print(f"  {RED}Usage: /analyze [command]{R}")

            elif cmd == "/cmd":
                if arg:
                    stop = spinner_start("Converting to command")
                    try:
                        command = text_to_command(arg, session)
                    finally:
                        stop.set()
                    print(f"\n  {YELLOW}Generated command:{R}")
                    print(f"  {GREEN}$ {command}{R}")
                    run_it = input(f"\n  {DIM}Run it? [y/N]: {R}").strip().lower()
                    if run_it == "y":
                        output, code = run_shell(command)
                        render_command_output(command, output, code)
                        analyze_it = input(f"  {DIM}Analyze output? [y/N]: {R}").strip().lower()
                        if analyze_it == "y":
                            stop = spinner_start("Analyzing")
                            try:
                                analysis = analyze_output(command, output, code, session)
                            finally:
                                stop.set()
                            render_response(analysis, config.get("provider"))
                else:
                    print(f"  {RED}Usage: /cmd [describe what you want to do]{R}")

            else:
                print(f"  {RED}Unknown command. Type /help{R}")

        # ── Shell shortcut: !command ───────────────────────────────────────
        elif user_input.startswith("!"):
            cmd = user_input[1:].strip()
            output, code = run_shell(cmd)
            render_command_output(cmd, output, code)

        # ── Inline shell: `command` ────────────────────────────────────────
        elif user_input.startswith("`") and user_input.endswith("`"):
            cmd = user_input[1:-1].strip()
            output, code = run_shell(cmd)
            render_command_output(cmd, output, code)
            # Also send context to AI
            context = f"I ran: `{cmd}`\nOutput:\n{output[:1000]}\nExit code: {code}"
            stop = spinner_start()
            try:
                reply = session.ask(context)
            except Exception as e:
                stop.set()
                print(f"\n  {RED}✗ Error: {e}{R}\n")
                continue
            stop.set()
            render_response(reply, config.get("provider"))

        # ── Normal chat ───────────────────────────────────────────────────
        else:
            stop = spinner_start()
            try:
                reply = session.ask(user_input)
            except Exception as e:
                stop.set()
                print(f"\n  {RED}✗ Error: {e}{R}")
                if "API key" in str(e):
                    print(f"  {YELLOW}→ Use /keys to set your API key{R}")
                continue
            stop.set()
            render_response(reply, config.get("provider"))

if __name__ == "__main__":
    main()
