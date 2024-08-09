import subprocess
import sys

from env import CREATE_NO_WINDOW

import platform
import os


def get_os_info():
    os_name = platform.system()
    os_version = platform.version()
    os_release = platform.release()
    return os_name, os_version, os_release


def get_webview_renderer_code():
    os_name, os_version, os_release = get_os_info()
    print(os_name, os_version, os_release)
    if os_name == 'Windows':
        if int(os_release) >= 10:
            renderer = 'edgechromium'
        elif int(os_release) >= 7:
            renderer = 'qt'
        else:
            renderer = 'mshtml'
    elif os_name == 'Linux':
        renderer = 'qt'  # or 'gtk' depending on what is available and preferred
    elif os_name == 'Darwin':  # macOS
        renderer = 'webkit'
    else:
        raise NotImplementedError('Unsupported platform')
    return renderer


def get_system_browser():
    os_platform = sys.platform

    if os_platform == 'win32':
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

    elif os_platform == 'linux' or os_platform == 'linux2':
        # Use xdg-settings to find the default browser on Linux
        try:
            browser_path = subprocess.check_output(['xdg-settings', 'get', 'default-web-browser']).decode().strip()
            browser_path = subprocess.check_output(['which', browser_path.split('.')[0]]).decode().strip()
        except Exception:
            raise FileNotFoundError('Failed to look up default browser using xdg-settings. Using fallback value.')
        return browser_path

    elif os_platform == 'darwin':
        # Use the open command to find the default browser on macOS
        try:
            browser_path = subprocess.check_output(['open', '-Ra', 'Google Chrome']).decode().strip()
            if not browser_path:
                browser_path = subprocess.check_output(['open', '-Ra', 'Safari']).decode().strip()
            if not browser_path:
                raise FileNotFoundError('Failed to find default browser using open command. Using fallback value.')
        except Exception:
            raise FileNotFoundError('Failed to look up default browser on macOS. Using fallback value.')
        return browser_path

    else:
        raise NotImplementedError('Unsupported platform')


def run_in_system_webview(code, url):
    import webview
    print("Running webview")
    window = webview.create_window('ArcherLink', url=f'http://{url}')
    webview.start(gui=code, debug=False)
    return window


def run_in_webbrowser(browser_path, url):
    if not browser_path:
        raise FileNotFoundError("Could not detect the default browser.")
    subprocess.Popen([
        browser_path,
        f'--app=http://{url}',
        # f'--window-size={720},{540}',
        # '--start-maximized'
    ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        creationflags=CREATE_NO_WINDOW
    )


def open(url):
    try:
        code = get_webview_renderer_code()
        run_in_system_webview(code, url)
    except Exception as e:
        print(e)
        browser_path = get_system_browser()
        run_in_webbrowser(browser_path, url)


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
