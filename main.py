import asyncio
import threading
from modules import server, webview
from env import CFG


def main():
    # port = CFG['uvicorn'].get('port', 15010)
    port = CFG['uvicorn'].get('port', server.find_free_port())
    host = CFG['uvicorn'].get('host', '127.0.0.1')

    async_thread = threading.Thread(target=server.run, args=(host, port))
    async_thread.start()
    webview.open(f"{host}:{port}")
    async_thread.join()


if __name__ == '__main__':
    main()
