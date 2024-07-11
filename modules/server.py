import asyncio
import base64
import logging
import os.path
import socket
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_socketio import SocketManager

from env import *
from modules.mov.mov_cv2 import MovRecorder
from modules.runpwa import open_as_pwa

if VIDEO_PROVIDER == 'av':
    if IMAGE_PROVIDER == 'pillow':
        from modules.rtsp.av_pil import RTSPClient
    elif IMAGE_PROVIDER == 'cv2':
        from modules.rtsp.av_cv2 import RTSPClient
    else:
        raise ImportError("Wrong image provider for PyAV backend")
elif VIDEO_PROVIDER == 'cv2' and IMAGE_PROVIDER == 'cv2':
    from modules.rtsp.cv2 import RTSPClient
else:
    raise ImportError("Wrong image provider for cv2 backend")

# origins = [
#     "http://localhost:3000",  # Replace with your frontend app's URL
#     "http://localhost:8081",  # Replace with your frontend app's URL
#     "ws://127.0.0.1:8081",  # Example origin, replace as necessary
#     "ws://127.0.0.1:15010",  # Example origin, replace as necessary
#     "ws://localhost:8081",  # Example origin, replace as necessary
#     "ws://localhost:15010",  # Example origin, replace as necessary
#     "http://127.0.0.1:3000",  # Example origin, replace as necessary
#     "http://127.0.0.1:8081",  # Example origin, replace as necessary
#     "http://localhost:15010",  # Example origin, replace as necessary
#     "http://127.0.0.1:15010",  # Example origin, replace as necessary
# ]

origins = ["*"]

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # List of allowed origins
    allow_credentials=True,
    allow_methods=["*"],  # List of allowed methods, e.g., ["GET", "POST"]
    allow_headers=["*"],  # List of allowed headers, e.g., ["Content-Type"]
)

# Serve the static files from the web-build directory
app.mount("/static", StaticFiles(directory=FRONTEND_PATH), name="static")

app.mount("/_expo", StaticFiles(directory=os.path.join(FRONTEND_PATH, "_expo")), name="_expo")
app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_PATH, "assets")), name="assets")


# Serve the index.html file at the root URL
@app.get("/")
async def serve_root():
    return FileResponse(os.path.join(FRONTEND_PATH, "index.html"))


@app.get("/favicon.ico")
async def serve_root():
    return FileResponse(os.path.join(FRONTEND_PATH, "favicon.ico"))


sio = SocketManager(
    app=app,
    socketio_path="/ws/socket.io",
)

RTSP = RTSPClient(TCP_IP, TCP_PORT, RTSP_URI, AV_OPTIONS)
MOV = MovRecorder(RTSP, lambda x: x)

CONNECTIONS_COUNT = 0

clients_tasks = {}


async def frame_emitter(sid):
    while True:
        frame = RTSP.webframe
        await sio.emit("frame", {
            "wifi": True,
            "stream": {
                "frame": base64.b64encode(frame).decode('utf-8') if frame else None,
                "state": RTSP.status.name,
                "error": None
            },
            "recording": {
                "state": False
            }
        }, to=sid)
        await asyncio.sleep(1 / RTSP.fps)


@sio.on("connect")
async def handle_connect(sid, *args, **kwargs):
    print("Connected", sid)
    clients_tasks[sid] = sio.start_background_task(frame_emitter, sid)


@sio.on("disconnect")
async def handle_disconnect(sid):
    print("Disconnected", sid)
    if sid in clients_tasks:
        task = clients_tasks.pop(sid)
        task.cancel()


@sio.on("makeShot")
async def handleMakeShot(sid, *args, **kwargs):
    try:
        if RTSP.frame:
            filepath = await get_output_filename()
            await RTSP.shot(filepath)
            sio.emit('photo', {'filename': filepath})
        else:
            sio.emit('photo', {'error': 'No frame available'})
    except:
        sio.emit('photo', {'error': 'Internal server error'})


@sio.on("openMedia")
async def handleOpenMedia(sid, *args, **kwargs):
    print('handle open media')
    await open_output_dir()


@sio.on("toggleRecord")
async def handleToggleRecord(sid, *args, **kwargs):
    print('handle toggle record')


async def check_port_available(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except socket.error as e:
            if e.errno == 10048:
                return False
            else:
                raise
    return True


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('localhost', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


async def run():
    port = CFG['uvicorn'].get('port', find_free_port())
    # port = CFG['uvicorn'].get('port', 15010)
    host = CFG['uvicorn'].get('host', '127.0.0.1')
    pwa_coro = open_as_pwa(f"{host}:{port}")

    config = uvicorn.Config(
        app, host=host, port=port
    )
    global uvicorn_server

    if not await check_port_available(host, port):
        logging.info(f"Port {port} is already in use. Please use a different port.")
        await pwa_coro
        sys.exit(1)

    uvicorn_server = uvicorn.Server(config)
    rtsp_coro = RTSP.run_in_executor()
    serv_coro = uvicorn_server.serve()
    await asyncio.gather(
        rtsp_coro,
        serv_coro, pwa_coro)
