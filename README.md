<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Cent%20Pay%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Channels%7CEarn%20Tasks%7CAirdrops%7CCENT%20Mining%7CMilestones&descAlign=50&descAlignY=58"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Mandatory%20channel%20check;Earn%20task%20runner;Airdrop%20runner;CENT%20mining%20management;Referral%20milestone%20claims"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-CentPay%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>CentPay Bot</b> is a full automation bot for the CentPay Telegram Miniapp.<br/>
  It walks the complete daily cycle for every account: the mandatory channel check, the earn task board, the airdrop board, the CENT mining rig and the referral milestones, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.12+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Centpay-Miniapp.git
cd Centpay-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening CentPay on Telegram Web.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Mandatory Channels
Runs the channel membership check the app requires before anything else is unlocked. A pass is reported as verified, and every channel that is still missing is listed on its own line instead of blocking silently.

### Earn Tasks
Reads the earn task board straight from the server page, then walks every task in order: the bot opens the task, waits the wait time the server itself returns for that task, and settles it. Each task is logged with its own outcome, so a credited task, a task that was already settled before, a capped task and a task the server refused are all separate visible lines.

### Airdrops
Reads the airdrop board the same way and settles every airdrop that is still open, logging the credited amount from the server answer. Airdrops that were already taken are reported as such.

### CENT Mining
Reads the mining rig state and the rig configuration from the server page, then claims a finished cycle and immediately starts the next one, logging the amount credited and the exact time until the next claim. A cycle that is still filling is reported with its remaining time instead of being forced.

### Referral Milestones
Reads the milestone ladder with the live friend progress of the account, claims every milestone that is already unlocked, and reports the reward the server credited. The first milestone that is still short is reported with the exact number of friends still missing.

### Multi Account
All accounts in `data.txt` are processed sequentially within every cycle. Each account is logged with its profile name, its own phase lines and the total credited on that run. The cycle number is tracked and logged at the start of each round.

### Proxy Support
Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown
After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
CentPay-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    ├── banner.py   # Banner using yuurisan module
    └── __init__.py # Package marker
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
