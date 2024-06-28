from cefpython3 import cefpython as cef
import sys

def main():
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    settings = {
        "cache_path": "webcache/"  # Optional: persist cache
    }
    cef.Initialize(settings)
    create_browser()
    cef.MessageLoop()
    cef.Shutdown()

def create_browser():
    # browser_settings = {
    #     "windowless_rendering_enabled": False
    # }
    url = "http://127.0.0.1:15010"  # Replace with your URL
    cef.CreateBrowserSync(url=url,
                          window_title="CEF Python Browser",
                          # settings=browser_settings
                          )

if __name__ == "__main__":
    main()
