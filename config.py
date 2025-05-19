import os
import json
from pathlib import Path

# Configuration directory
CONFIG_DIR = Path.home() / ".claude-windows-control"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Default configuration
DEFAULT_CONFIG = {
    "api_key": "",  # API key should be entered by user, never stored in the repo
    "model": "claude-3-7-sonnet-20250219",
    "max_output_tokens": 4096,
    "thinking_budget": 2048,
    "system_prompt": """<SYSTEM_CAPABILITY>
* You are controlling a Windows computer.
* You can use mouse and keyboard actions to interact with the UI.
* You can take screenshots to see what's on screen.
* You can run PowerShell commands to perform system operations.
* When viewing a page it's helpful to zoom out so you can see everything on the page.
* When using your computer function calls, they take a while to run and send back to you.
</SYSTEM_CAPABILITY>

<IMPORTANT>
* When navigating complex interfaces, take screenshots frequently to check your progress.
* If a task requires accessing sensitive information, ask for user confirmation first.
* Break complex tasks into simple steps and verify each step.
</IMPORTANT>"""
}

def ensure_config_dir():
    """Create configuration directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
def load_config():
    """Load configuration from file, or create default if it doesn't exist."""
    ensure_config_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    # Restrict file permissions to user only
    os.chmod(CONFIG_FILE, 0o600)

def save_api_key(api_key):
    """Save API key to configuration."""
    config = load_config()
    config["api_key"] = api_key
    save_config(config)

def get_api_key():
    """Get API key from configuration."""
    return load_config().get("api_key", "")