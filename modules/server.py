import asyncio
import base64
import logging
import os.path
import socket
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi_socketio import SocketManager

from env import *
from modules.runpwa import open_as_pwa

from modules.rtsp.cv2 import RTSPClient
from modules.mov.cv2 import MovRecorder

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

clients_tasks = {}


async def frame_emitter(sid):
    while True:
        webframe = RTSP.webframe

        frame = base64.b64encode(webframe).decode('utf-8') if webframe else None

        await sio.emit("frame", {
            "wifi": True,
            "stream": {
                "frame": frame,
                "state": RTSP.status.name,
                "error": RTSP.status == RTSP.status.Error
            },
            "recording": {
                "state": MOV.recording
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

    if len(clients_tasks) <= 0:
        await RTSP.stop()
        uvicorn_server.should_exit = True
        # uvicorn_server.force_exit()


@sio.on("makeShot")
async def handleMakeShot(sid, *args, **kwargs):
    try:
        if RTSP.frame is not None:
            filepath = await get_output_filename()
            await RTSP.shot(filepath)
            await sio.emit('photo', {'filename': filepath})
        else:
            raise IOError("No frame available")
    except Exception as err:
        await sio.emit('photo', {'error': err.__str__()})


@sio.on("openMedia")
async def handleOpenMedia(sid, *args, **kwargs):
    try:
        await open_output_dir()
    except Exception as err:
        await sio.emit('photo', {'error': err.__str__()})


@sio.on("toggleRecord")
async def handleToggleRecord(sid, *args, **kwargs):
    try:
        if RTSP.frame is not None and RTSP.status == RTSP.Status.Running and not MOV.recording:
            output_filename = await get_output_filename()
            await MOV.start_async_recording(output_filename)
            await sio.emit('record', {'msg': "Recording started"})
        elif MOV.recording:
            output_filename, err = await MOV.stop_recording()
            if err is not None:
                raise IOError(err)
            await sio.emit('record', {'filename': output_filename})
    except Exception as err:
        await sio.emit('record', {'error': err.__str__()})


@app.post("/api/server/stop")
async def stop_server():
    try:
        await asyncio.sleep(1)
        if len(clients_tasks) <= 0:
            logging.info("Stop request from client")
            await RTSP.stop()
            uvicorn_server.should_exit = True
            return JSONResponse({})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
