import os
import sys
import time
import platform
import subprocess
import traceback
import psutil

from watcher.logger import setup_logger
from watcher.config_loader import config

logger = setup_logger()

IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

def get_python_command(script_path=None):
    python_exe = sys.executable
    if script_path is None:
        script_path = os.path.abspath(__file__)
    return f'"{python_exe}" "{script_path}"'

def get_pid_file():
    return os.path.expanduser(config.pid_file)

def is_process_alive(pid):
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False

def write_pid():
    pid_file = get_pid_file()
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))
    logger.info(f"[Watcher] PID written: {os.getpid()}")

def clear_pid():
    pid_file = get_pid_file()
    try:
        if os.path.exists(pid_file):
            with open(pid_file, "w") as f:
                f.write("")
            logger.info("[Watcher] PID file cleared.")
    except Exception as e:
        logger.warning(f"[Watcher] Failed to clear PID file: {e}")

def is_already_running():
    pid_file = get_pid_file()
    if not os.path.exists(pid_file):
        return False
    try:
        with open(pid_file, "r") as f:
            if not f.read().strip():
                return False
            pid = int(f.read().strip()) if f.read().strip().isdigit() else None
        if pid is None:
            return False
        if is_process_alive(pid):
            logger.info(f"[Watcher] Already running with PID {pid}. Skipping duplicate start.")
            return True
    except Exception as e:
        logger.warning(f"[Watcher] Failed to check existing PID file: {e}")
    return False

def register_autostart():
    try:
        if IS_WINDOWS:
            register_windows()
        # elif IS_MAC:
        #     register_macos()
        # elif IS_LINUX:
        #     register_linux()
    except Exception as e:
        logger.error(f"[AUTOSTART] Failed to register autostart: {e}")
        traceback.print_exc()
        
def register_windows():
    startup_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    executable_path = os.path.join(startup_dir, os.path.basename(config.exe_file))
    if not os.path.exists(executable_path):
        try:
            import shutil
            shutil.copy(config.exe_file, executable_path)
            logger.info(f"[AUTOSTART] Registered Windows autostart: {executable_path}")
        except Exception as e:
            logger.error(f"[AUTOSTART] Failed to register Windows autostart: {e}")

# def register_macos():
#     plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{config.app_name}.plist")
#     if os.path.exists(plist_path):
#         logger.info(f"[AUTOSTART] Already registered in macOS: {plist_path}")
#         return
#     script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner", "start.py")
#     plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
# <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
#     "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
# <plist version="1.0">
# <dict>
#     <key>Label</key><string>{config.app_name}</string>
#     <key>ProgramArguments</key>
#     <array>
#         <string>{sys.executable}</string>
#         <string>{script_path}</string>
#     </array>
#     <key>RunAtLoad</key><true/>
#     <key>KeepAlive</key><true/>
# </dict>
# </plist>
# """
#     with open(plist_path, "w") as f:
#         f.write(plist_content)
#     subprocess.run(["launchctl", "load", plist_path])
#     logger.info(f"[AUTOSTART] Registered macOS autostart: {plist_path}")

# def register_linux():
#     autostart_dir = os.path.expanduser("~/.config/autostart")
#     os.makedirs(autostart_dir, exist_ok=True)
#     desktop_file = os.path.join(autostart_dir, f"{config.app_name}.desktop")

#     if os.path.exists(desktop_file):
#         logger.info(f"[AUTOSTART] Already registered in Linux: {desktop_file}")
#         return

#     script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner", "start.py")
#     content = f"""[Desktop Entry]
# Type=Application
# Exec={get_python_command(script_path)}
# Hidden=false
# NoDisplay=false
# X-GNOME-Autostart-enabled=true
# Name={config.app_name}
# """
#     with open(desktop_file, "w") as f:
#         f.write(content)
#     logger.info(f"[AUTOSTART] Registered Linux autostart: {desktop_file}")

def start():
    logger.info("[Watcher] Initializing...")

    if is_already_running():
        return

    write_pid()
    register_autostart()

    current_dir = os.path.dirname(os.path.abspath(sys.modules[__name__].__file__))
    runner_dir = os.path.join(current_dir, "runner")
    run_api_py = os.path.join(runner_dir, "run_api.py")
    run_watcher_py = os.path.join(runner_dir, "run_watcher.py")

    python_exe = sys.executable

    api_cmd = [python_exe, run_api_py]
    watcher_cmd = [python_exe, run_watcher_py]

    try:
        # api_proc = subprocess.Popen(api_cmd, creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0)
        api_proc = subprocess.Popen(api_cmd)
    except Exception as e:
        logger.error(f"[Watcher] Failed to start API server: {e}")
        sys.exit(1)
        
    try:
        # watcher_proc = subprocess.Popen(watcher_cmd, creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0)
        watcher_proc = subprocess.Popen(watcher_cmd)
    except Exception as e:
        logger.error(f"[Watcher] Failed to start Watcher: {e}")
        sys.exit(1)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("[Watcher] Shutting down gracefully...")
        api_proc.terminate()
        watcher_proc.terminate()
        clear_pid()
        sys.exit(0)
    except Exception as e:
        logger.error(f"[Watcher] Exception: {e}")
        clear_pid()
        raise
    finally:
        clear_pid()

if __name__ == "__main__":
    logger.info(f"[OS] Detected: {platform.system()}")
    start()
