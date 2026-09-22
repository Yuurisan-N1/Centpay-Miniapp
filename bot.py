import asyncio
import html
import json
import os
import re
import signal
import ssl
import sys
import time
import urllib.parse

import aiohttp

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "CentPay Miniapp"
BASE_URL = "https://centpaytg.com"
REF_CODE = "ref_CP_6004380466"

HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/?tgWebAppStartParam={REF_CODE}",
    "user-agent": "Mozilla/5.0 (Linux; Android 13; SM-S901B; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0.0.0 Mobile Safari/537.36",
}


def log_green(msg):
    print(f"{GREEN}{BOLD}{msg}{RESET}", flush=True)


def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{msg}{RESET}", flush=True)


def log_red(msg):
    print(f"{RED}{BOLD}{msg}{RESET}", flush=True)


def signal_handler(sig, frame):
    print()
    log_red("Script stopped by user")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def clean_text(value, fallback):
    text = str(value)
    for symbol in "[]|#!@$%^&*()-":
        text = text.replace(symbol, " ")
    text = " ".join(text.split())
    return text if text else str(fallback)


def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1]
    space = cut.rfind(" ")
    return cut[:space].rstrip() if space > 0 else text[:limit].rstrip()


def number_of(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def int_of(value, fallback):
    return int(number_of(value, fallback))


def format_duration(total):
    total = max(0, int(total))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"


def countdown(seconds):
    for remaining in range(max(0, int(seconds)), 0, -1):
        sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(remaining)}{RESET}")
        sys.stdout.flush()
        time.sleep(1)
    sys.stdout.write(f"\r{YELLOW}{BOLD}Next cycle starts in {format_duration(0)}{RESET}")
    sys.stdout.flush()
    print()


def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"


def normalize_proxy(raw):
    line = raw.strip()
    if not line:
        return None
    if "://" in line:
        return line
    parts = line.split(":")
    if len(parts) == 2:
        return f"http://{parts[0]}:{parts[1]}"
    if len(parts) == 4:
        return f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
    return None


def load_config():
    if not os.path.isfile("config.json"):
        with open("config.json", "w", encoding="utf-8") as handle:
            json.dump({"settings": {"sleep_seconds": 3600}}, handle, indent=2)
            handle.write("\n")
    try:
        with open("config.json", encoding="utf-8") as handle:
            data = json.load(handle)
        return int(data.get("settings", {}).get("sleep_seconds", 3600))
    except Exception:
        return 3600


def load_accounts():
    if not os.path.isfile("data.txt"):
        return []
    with open("data.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    accounts = []
    for line in lines:
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        accounts.append(entry.split("|")[0].strip())
    return accounts


def load_proxies():
    if not os.path.isfile("proxy.txt"):
        return []
    with open("proxy.txt", encoding="utf-8") as handle:
        lines = handle.read().splitlines()
    proxies = []
    for line in lines:
        normalized = normalize_proxy(line)
        if normalized:
            proxies.append(normalized)
    return proxies


def telegram_profile(init_data):
    profile = {"id": "", "username": "", "first_name": ""}
    try:
        for chunk in init_data.split("&"):
            if chunk.startswith("user="):
                payload = json.loads(urllib.parse.unquote(chunk[5:]))
                profile["id"] = str(payload.get("id") or "")
                profile["username"] = str(payload.get("username") or "")
                profile["first_name"] = str(payload.get("first_name") or "")
    except Exception:
        return profile
    return profile


def task_cards(markup):
    cards = []
    for chunk in markup.split('id="task-card-')[1:]:
        found = re.match(r"(\d+)", chunk)
        if not found:
            continue
        card = {"id": found.group(1)}
        name = re.search(r"<h4[^>]*>\s*([^<]+?)\s*</h4>", chunk)
        category = re.search(r'data-category="([^"]*)"', chunk)
        reward = re.search(r"\+([\d.,]+)\s*CENT", chunk)
        wait = re.search(r"startTask\(\s*(\d+)\s*,\s*'[^']*'\s*,\s*(\d+)\s*\)", chunk)
        card["name"] = html.unescape(name.group(1)) if name else card["id"]
        card["category"] = category.group(1) if category else ""
        card["reward"] = reward.group(1) if reward else ""
        card["wait"] = int_of(wait.group(2), 0) if wait else 0
        cards.append(card)
    return cards


def airdrop_cards(markup):
    cards = []
    for chunk in markup.split('id="airdrop-card-')[1:]:
        found = re.match(r"(\d+)", chunk)
        if not found:
            continue
        card = {"id": found.group(1)}
        name = re.search(r"<h4[^>]*>\s*([^<]+?)\s*</h4>", chunk)
        reward = re.search(r"\+([\d.,]+)\s*CENT", chunk)
        wait = re.search(r"startAirdrop\(\s*(\d+)\s*,\s*'[^']*'\s*,\s*(\d+)\s*\)", chunk)
        card["name"] = html.unescape(name.group(1)) if name else card["id"]
        card["reward"] = reward.group(1) if reward else ""
        card["wait"] = int_of(wait.group(2), 0) if wait else 0
        cards.append(card)
    return cards


def milestone_rows(markup):
    start = markup.find('id="milestonesList"')
    if start < 0:
        return []
    end = markup.find("</main>", start)
    block = markup[start:end if end > start else len(markup)]
    rows = []
    for chunk in block.split('<div class="p-2 rounded-[5px] border')[1:]:
        tier = re.search(r'justify-center shrink-0 text-xs font-medium">\s*(\d+)\s*<', chunk)
        title = re.search(r"text-purple-950 truncate[^>]*>\s*([^<]+?)\s*<", chunk)
        reward = re.search(r"\+([\d.,]+)\s*CENT", chunk)
        progress = re.search(r">\s*(\d+)\s*/\s*(\d+)\s*<", chunk)
        if not tier or not progress:
            continue
        rows.append({
            "tier": int_of(progress.group(2), 0),
            "name": html.unescape(title.group(1)) if title else "milestone",
            "reward": reward.group(1) if reward else "",
            "have": int_of(progress.group(1), 0),
            "need": int_of(progress.group(2), 0),
        })
    rows.sort(key=lambda row: row["tier"])
    return rows


def mining_values(markup):
    values = {"duration": 0, "reward": 0}
    duration = re.search(r"const DURATION_SECONDS\s*=\s*(\d+)", markup)
    reward = re.search(r"const REWARD_AMOUNT\s*=\s*([\d.]+)", markup)
    values["duration"] = int_of(duration.group(1), 0) if duration else 0
    values["reward"] = number_of(reward.group(1), 0) if reward else 0
    return values


class CentAccount:
    def __init__(self, init_data, proxy_url):
        self.init_data = init_data
        self.proxy_url = proxy_url
        self.profile = telegram_profile(init_data)
        self.csrf = ""
        self.session = None
        self.connector = None
        self.last_write = 0.0

    async def open(self):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.connector = aiohttp.TCPConnector(ssl=context)
        self.session = aiohttp.ClientSession(connector=self.connector, headers=HEADERS_BASE,
                                             cookie_jar=aiohttp.CookieJar(unsafe=True))

    async def close(self):
        if self.session is not None:
            await self.session.close()
        if self.connector is not None:
            await self.connector.close()

    async def pace(self):
        gap = 1.5 - (time.monotonic() - self.last_write)
        if gap > 0:
            await asyncio.sleep(gap)
        self.last_write = time.monotonic()

    async def request(self, method, path, payload=None, params=None):
        url = f"{BASE_URL}{path}"
        body_text = None
        if payload is not None:
            body_text = json.dumps(payload, separators=(",", ":"))
        headers = {}
        if self.csrf:
            headers["x-csrf-token"] = self.csrf
        last_error = None
        throttled = False
        if method == "POST":
            await self.pace()
        for attempt in range(4):
            try:
                timeout = aiohttp.ClientTimeout(total=30)
                async with self.session.request(method, url, data=body_text, params=params, headers=headers,
                                                proxy=self.proxy_url, timeout=timeout) as response:
                    text = (await response.text()).strip()
                    if response.status == 429:
                        throttled = True
                        await asyncio.sleep(30)
                        continue
                    if not text:
                        return response.status, {}
                    try:
                        return response.status, json.loads(text)
                    except json.JSONDecodeError:
                        return response.status, {"_raw": text[:400]}
            except Exception as exc:
                last_error = exc
                await asyncio.sleep(1.5 * (attempt + 1))
        if throttled:
            raise RuntimeError("rate limited")
        raise last_error if last_error else RuntimeError("request failed")

    async def page(self, path):
        timeout = aiohttp.ClientTimeout(total=30)
        async with self.session.get(f"{BASE_URL}{path}", proxy=self.proxy_url,
                                    timeout=timeout) as response:
            return response.status, await response.text()

    async def get(self, path, params=None):
        return await self.request("GET", path, None, params)

    async def post(self, path, payload=None):
        return await self.request("POST", path, payload)

    async def handshake(self):
        status, markup = await self.page("/")
        if status != 200:
            return False
        found = re.search(r'<meta name="csrf-token" content="([^"]+)"', markup)
        self.csrf = found.group(1) if found else ""
        return bool(self.csrf)

    async def label(self):
        name = self.profile.get("username") or self.profile.get("first_name") or self.profile.get("id")
        return shorten(name, "account", 20)


async def run_force_join(account):
    code, body = await account.post("/api/force-join/verify", {"initData": account.init_data})
    if code != 200 or not isinstance(body, dict):
        log_yellow("The mandatory channel check could not be read from the server")
        return False
    channels = body.get("channels") or []
    if body.get("all_joined"):
        log_green("Mandatory channel access was verified")
        return True
    for channel in channels:
        if not isinstance(channel, dict) or channel.get("is_joined"):
            continue
        title = shorten(channel.get("title") or channel.get("username"), "channel", 20)
        log_yellow(f"Channel {clean_text(title, 'channel')} is not joined yet")
    return False


async def run_tasks(account):
    credited = 0.0
    status, markup = await account.page("/tasks")
    if status != 200:
        log_yellow("The earn task page could not be read from the server")
        return credited
    cards = task_cards(markup)
    if not cards:
        log_yellow("No earn task was listed on the server page")
        return credited
    for card in cards:
        name = shorten(card["name"], "task", 18)
        wait = card["wait"]
        code, start = await account.post(f"/api/tasks/{card['id']}/start")
        if code != 200 or not isinstance(start, dict):
            log_yellow(f"Task {clean_text(name, 'task')} could not be started by the server")
            continue
        if not start.get("success"):
            detail = shorten(start.get("message"), "no reason", 16)
            log_yellow(f"Task {clean_text(name, 'task')} was refused with {clean_text(detail, 'no reason')}")
            continue
        if start.get("status") == "completed":
            log_yellow(f"Task {clean_text(name, 'task')} was already completed earlier")
            continue
        pause = int_of(start.get("timer_seconds"), wait) + 2
        if pause > 0:
            await asyncio.sleep(min(pause, 60))
        code, body = await account.post(f"/api/tasks/{card['id']}/verify")
        if code == 200 and isinstance(body, dict) and body.get("reward") is not None:
            amount = number_of(body.get("reward"), card["reward"])
            credited += amount
            log_green(f"Task {clean_text(name, 'task')} credited {clean_text(amount, 0)} CENT")
            continue
        detail = shorten((body or {}).get("message"), "no reason", 16)
        log_yellow(f"Task {clean_text(name, 'task')} was refused with {clean_text(detail, 'no reason')}")
    return credited


async def run_airdrops(account):
    credited = 0.0
    status, markup = await account.page("/airdrops")
    if status != 200:
        log_yellow("The airdrop page could not be read from the server")
        return credited
    cards = airdrop_cards(markup)
    if not cards:
        log_yellow("No airdrop was listed on the server page")
        return credited
    for card in cards:
        name = shorten(card["name"], "airdrop", 16)
        code, start = await account.post(f"/api/airdrops/{card['id']}/start")
        if code != 200 or not isinstance(start, dict):
            log_yellow(f"Airdrop {clean_text(name, 'airdrop')} could not be started by the server")
            continue
        if not start.get("success"):
            detail = shorten(start.get("message"), "no reason", 14)
            log_yellow(f"Airdrop {clean_text(name, 'airdrop')} was refused with {clean_text(detail, 'no reason')}")
            continue
        if start.get("status") == "completed":
            log_yellow(f"Airdrop {clean_text(name, 'airdrop')} was already completed earlier")
            continue
        pause = int_of(start.get("timer_seconds"), card["wait"]) + 2
        if pause > 0:
            await asyncio.sleep(min(pause, 60))
        code, body = await account.post(f"/api/airdrops/{card['id']}/verify")
        if code == 200 and isinstance(body, dict) and body.get("reward") is not None:
            amount = number_of(body.get("reward"), card["reward"])
            credited += amount
            log_green(f"Airdrop {clean_text(name, 'airdrop')} credited {clean_text(amount, 0)} CENT")
            continue
        detail = shorten((body or {}).get("message"), "no reason", 14)
        log_yellow(f"Airdrop {clean_text(name, 'airdrop')} was refused with {clean_text(detail, 'no reason')}")
    return credited


async def run_mining(account):
    credited = 0.0
    status, markup = await account.page("/mining")
    if status != 200:
        log_yellow("The mining page could not be read from the server")
        return credited
    values = mining_values(markup)
    code, body = await account.post("/api/mining/claim", {"initData": account.init_data})
    if code == 200 and isinstance(body, dict) and body.get("success"):
        amount = number_of(body.get("reward"), values["reward"])
        credited += amount
        log_green(f"Mining cycle credited {clean_text(amount, 0)} CENT")
    else:
        remaining = int_of((body or {}).get("remaining_seconds"), 0)
        if remaining > 0:
            log_yellow(f"The mining cycle is still running and returns in {format_duration(remaining)}")
            return credited
        detail = shorten((body or {}).get("message"), "no reason", 18)
        log_yellow(f"The mining claim was refused with {clean_text(detail, 'no reason')}")
    code, started = await account.post("/api/mining/start", {"initData": account.init_data})
    if code == 200 and isinstance(started, dict) and started.get("success"):
        opened = int_of(started.get("started_at_timestamp"), 0)
        server = int_of(started.get("server_timestamp"), 0)
        left = values["duration"]
        if opened and server and server > opened:
            left = max(0, values["duration"] - (server - opened))
        log_green(f"Mining rig started and the next claim returns in {format_duration(left)}")
        return credited
    detail = shorten((started or {}).get("message"), "no reason", 18)
    log_yellow(f"The mining rig was refused with {clean_text(detail, 'no reason')}")
    return credited


async def run_milestones(account):
    credited = 0.0
    status, markup = await account.page("/referral")
    if status != 200:
        log_yellow("The referral page could not be read from the server")
        return credited
    rows = milestone_rows(markup)
    if not rows:
        log_yellow("No referral milestone was listed on the server page")
        return credited
    for row in rows:
        name = shorten(row["name"], "milestone", 18)
        if row["have"] < row["need"]:
            log_yellow(f"Milestone {clean_text(name, 'milestone')} still needs "
                       f"{clean_text(row['need'] - row['have'], 0)} more friends")
            break
        code, body = await account.post("/api/referral/claim-milestone", {"friends_tier": row["tier"]})
        if code == 200 and isinstance(body, dict) and body.get("success"):
            amount = number_of(body.get("reward") or body.get("amount"), row["reward"])
            credited += amount
            log_green(f"Milestone {clean_text(name, 'milestone')} credited {clean_text(amount, 0)} CENT")
            continue
        detail = shorten((body or {}).get("message"), "no reason", 16)
        log_yellow(f"Milestone {clean_text(name, 'milestone')} was refused with {clean_text(detail, 'no reason')}")
        break
    return credited


async def run_account(init_data, proxy_url):
    account = CentAccount(init_data, proxy_url)
    await account.open()
    try:
        if not await account.handshake():
            log_red("The account session could not be opened by the server")
            return None
        label = await account.label()
        if proxy_url is not None:
            log_yellow(f"Using proxy {mask_proxy(proxy_url)}")
        log_green(f"Account {clean_text(label, 'account')} started the cycle")
        await run_force_join(account)
        credited = 0.0
        credited += await run_tasks(account)
        credited += await run_airdrops(account)
        credited += await run_mining(account)
        credited += await run_milestones(account)
        if credited > 0:
            log_green(f"Cycle closed with {clean_text(credited, 0)} CENT credited on this run")
        else:
            log_yellow("Cycle closed without a new credit on this run")
        return credited
    finally:
        await account.close()


async def main():
    show_banner(MY_PROJECT)
    sleep_seconds = load_config()
    accounts = load_accounts()
    proxies = load_proxies()
    if not accounts:
        log_red("No account was found in data.txt")
        sys.exit(1)
    cycle = 0
    while True:
        cycle += 1
        log_green(f"Starting automation cycle number {clean_text(cycle, 0)}")
        for idx, init_data in enumerate(accounts):
            if idx > 0:
                print()
            proxy_url = proxies[idx % len(proxies)] if proxies else None
            try:
                await run_account(init_data, proxy_url)
            except Exception as exc:
                log_red(f"Request to the server failed with {clean_text(type(exc).__name__, 'error')}")
        countdown(sleep_seconds)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        signal_handler(None, None)
