# Claude Desktop Pilot

A powerful desktop automation tool that gives Claude direct control over your Windows computer using Anthropic's Computer Use feature. Claude Desktop Pilot connects to the Anthropic API and leverages Claude's computer agent capabilities to see and interact with your desktop environment through screenshots, keyboard/mouse automation, and PowerShell commands.

> **Note:** This application has currently only been tested on Windows operating systems.

## Features

- **Computer Agent Control**: Claude can see and interact with your Windows desktop using Anthropic's Computer Use agent feature
- **Screenshot Capabilities**: AI vision through real-time screenshots
- **Input Automation**: Complete keyboard and mouse control
- **PowerShell Integration**: Execute system commands through PowerShell
- **Text Editing**: Claude can edit files on your system
- **Secure By Design**: Your API keys stay local and are never shared

## Why We Created This

We developed Claude Desktop Pilot because we couldn't find any existing solutions that properly integrated Claude's Computer Use capabilities with Windows in a plug-and-play manner. While Anthropic provides a reference implementation, we found that most available solutions required significant setup and configuration. This project aims to provide a simple, ready-to-use Windows implementation that works immediately after installation without complex configuration or technical expertise.

## Installation & Usage (Simple 2-Step Process)

We've made setup and running as simple as possible with two clearly labeled batch files:

### Step 1: Install

Double-click `1-Install.bat` to:
- Create a Python virtual environment if needed
- Install all required dependencies
- Set up the configuration directory

> **IMPORTANT**: You must complete the installation step before running the application!

### Step 2: Run the Application

Double-click `2-Run.bat` to:
- Activate the virtual environment
- Start the Claude Desktop Pilot application
- Open your browser to the application interface

On first run, you'll be prompted to enter your Anthropic API key (you can get one from [Anthropic's website](https://www.anthropic.com/)).

## Advanced Setup (Manual Installation)

If you prefer to set things up manually:

1. Clone this repository:
   ```
   git clone https://github.com/aprabh96/Claude-Desktop-Pilot---Computer-Control.git
   cd Claude-Desktop-Pilot---Computer-Control
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Start the application:
   ```
   streamlit run app.py
   ```

## Example Tasks

Ask Claude to perform tasks on your computer:
- "Take a screenshot"
- "Open Notepad and type Hello World"
- "Create a folder named 'Test' on my desktop"
- "Search for a file containing 'important'"

## Security Considerations

- **API Key Storage**: Your Anthropic API key is stored locally in `~/.claude-windows-control/config.json` with restricted permissions (0o600)
- **No Remote Storage**: Keys are never sent to remote servers or committed to repositories
- **Permission Controls**: The app will ask for confirmation before performing sensitive operations

## Technical Details

Claude Desktop Pilot uses:
- **Streamlit**: For the user interface
- **Anthropic API**: Uses Claude 3.7 Sonnet with Computer Use capability
- **PyAutoGUI**: For mouse and keyboard automation
- **PIL/Pillow**: For screenshot processing
- **Python Async**: For responsive, non-blocking operations

## Acknowledgments

This project may incorporate code and ideas from various open-source projects and examples. We extend our gratitude to the broader developer community whose work has inspired and contributed to this tool.

## License

This software is open source and free to use for non-commercial purposes. Commercial use is prohibited without express permission from Psynect Corp.

## Credits

Developed by [Psynect Corp](https://psynect.ai)

---

© Psynect Corp. All rights reserved. 