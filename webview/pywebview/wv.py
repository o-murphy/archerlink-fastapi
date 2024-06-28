import webview

# URL to load
url = 'http://127.0.0.1:15010'

# Create a webview window
webview.create_window('My Webview App', url=url)

# Start the webview application
webview.start()
# webview.start(gui='gtk')