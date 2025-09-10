# Reverse Shell

For educational and learning purposes only.
Created in python.

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
