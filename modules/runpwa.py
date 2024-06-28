import subprocess
import sys

from env import CREATE_NO_WINDOW


def get_system_browser():
    osPlatform = sys.platform

    if osPlatform == 'win32':
        # Find the default browser by interrogating the registry
        try:
            from winreg import HKEY_CLASSES_ROOT, HKEY_CURRENT_USER, OpenKey, QueryValueEx

            with OpenKey(HKEY_CURRENT_USER,
                         r'SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice') as regkey:
                # Get the user choice
                browser_choice = QueryValueEx(regkey, 'ProgId')[0]

            with OpenKey(HKEY_CLASSES_ROOT, fr'{browser_choice}\shell\open\command') as regkey:
                # Get the application the user's choice refers to in the application registrations
                browser_path_tuple = QueryValueEx(regkey, None)
                # This is a bit sketchy and assumes that the path will always be in double quotes
                browser_path = browser_path_tuple[0].split('"')[1]

        except Exception:
            raise FileNotFoundError('Failed to look up default browser in system registry. Using fallback value.')
        return browser_path


async def open_as_pwa(url):
    browser_path = get_system_browser()
    if not browser_path:
        raise FileNotFoundError("Could not detect the default browser.")
    subprocess.Popen([
        browser_path,
        f'--app=http://{url}',
        # f'--window-size={720},{540}',
        '--start-maximized'
    ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW
    )

# Open the registry key for the default HTTP handler
# def get_default_browser_command():
#     """Fetch the default browser command for HTTP URLs from the Windows registry."""
#     # Registry keys to check
#     registry_keys = [
#         (winreg.HKEY_CURRENT_USER, r"Software\Classes\http\shell\open\command"),
#         (winreg.HKEY_LOCAL_MACHINE, r"Software\Classes\http\shell\open\command")
#     ]
#
#     for hive, subkey in registry_keys:
#         try:
#             with winreg.OpenKey(hive, subkey) as key:
#                 cmd = winreg.QueryValue(key, None)
#                 return cmd
#         except FileNotFoundError:
#             continue
#     return None
