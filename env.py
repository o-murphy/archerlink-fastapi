import os
import subprocess
import sys
from datetime import datetime
import logging

try:
    import tomllib
except ImportError:
    import tomli as tomllib

_log = logging.getLogger('archerlink')
_log.setLevel(logging.INFO)

CREATE_NO_WINDOW = 134217728

CONFIG_PATH = "config.toml"
FRONTEND_PATH = os.path.join(os.path.dirname(__file__), "pwa")
if hasattr(sys, '_MEIPASS'):
    sys.stdout = open(os.devnull, 'w')
    CONFIG_PATH = os.path.join(sys._MEIPASS, CONFIG_PATH)
    FRONTEND_PATH = os.path.join(sys._MEIPASS, "pwa")

if sys.platform == 'win32':
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ArcherLink")
else:
    OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Pictures", 'ArcherLink')
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open(CONFIG_PATH, 'rb') as fp:
    CFG = tomllib.load(fp)

DEBUG = CFG.get('DEBUG', False)

SERVER = CFG['debug-server' if DEBUG else 'server']

IMAGE_PROVIDER = CFG.get('IMAGE_PROVIDER', "cv2").lower()
VIDEO_PROVIDER = CFG.get('VIDEO_PROVIDER', "cv2").lower()

_log.info(f"{IMAGE_PROVIDER=}")
_log.info(f"{VIDEO_PROVIDER=}")

TCP_IP = SERVER['TCP_IP']
TCP_PORT = SERVER['TCP_PORT']
WS_PORT = SERVER['WS_PORT']
WS_URI = SERVER['WS_URI']
RTSP_URI = SERVER['RTSP_URI']
AV_OPTIONS = CFG['av-options']


async def get_output_filename():
    dt = datetime.now().strftime("%y%m%d-%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{dt}")


async def open_output_dir():
    if sys.platform == "win32":
        os.startfile(OUTPUT_DIR)
        subprocess.Popen(["powershell", "-Command", """
                    $shell = New-Object -ComObject Shell.Application;
                    $folder = $shell.NameSpace('{}');
                    if ($folder -ne $null) {{
                        $folder.Self.InvokeVerb('open');
                    }}
                """.format(OUTPUT_DIR)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", OUTPUT_DIR])
    else:
        subprocess.Popen(["xdg-open", OUTPUT_DIR])


async def open_file_path(filepath):
    if sys.platform == "win32":
        # Use 'explorer' with '/select,' to highlight the file
        subprocess.Popen(['explorer', '/select,', filepath])
        # Optionally, bring the window to the front (if possible)
        # This is a bit tricky in Windows and often requires additional tools or scripts.
    elif sys.platform == "darwin":
        # Use 'open' with '-R' to reveal the file in Finder
        subprocess.Popen(['open', '-R', filepath])
        # Bring Finder to the front
        subprocess.Popen(["osascript", "-e", 'tell application "Finder" to activate'])
    else:
        # On Linux, there is no standard way to highlight a file, just open the directory
        directory = os.path.dirname(filepath)
        subprocess.Popen(['xdg-open', directory])
        # You can try to bring the file manager to the front (depends on the environment)
        subprocess.Popen(
            ["xdotool", "search", "--onlyvisible", "--name", os.path.basename(directory), "windowactivate"])


__all__ = (
    'CFG',
    'OUTPUT_DIR',
    'DEBUG',
    'TCP_IP',
    'TCP_PORT',
    'WS_PORT',
    'WS_URI',
    'RTSP_URI',
    'AV_OPTIONS',
    'get_output_filename',
    'open_output_dir',
    'open_file_path',
    'CREATE_NO_WINDOW',
    'FRONTEND_PATH',
    'IMAGE_PROVIDER',
    'VIDEO_PROVIDER'
)
