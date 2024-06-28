import asyncio
import logging
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from enum import Enum
import cv2

from env import CREATE_NO_WINDOW

logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger('RTSP')
_log.setLevel(logging.DEBUG)


class RTSPClient:
    class Status(Enum):
        Running = "Running"
        Stopped = "Stopped"
        Error = "Error"

    def __init__(self, host: str = None, port: int = None, uri: str = None, options: dict = None) -> None:
        self.host = host
        self.port = port
        self.rtsp_uri = uri
        self.options = options
        self.__cap: [cv2.VideoCapture, None] = None
        self.__socket: [socket.socket, None] = None
        self.__fps = 50  # default
        self.__frame = None
        self.__status = RTSPClient.Status.Stopped
        self._stop_event = asyncio.Event()
        self._executor = None
        self._task = None

    @property
    def frame(self):
        return self.__frame

    @property
    def status(self):
        return self.__status

    @property
    def fps(self):
        return self.__fps

    @property
    def _cap(self):
        return self.__cap

    @property
    def _socket(self):
        return self.__socket

    async def _get_stream_fps(self):
        if self.__cap:
            self.__fps = self.__cap.get(cv2.CAP_PROP_FPS) or self.__fps
            _log.info(f"Stream FPS: {self.__fps}")

    async def _open(self):
        while not self._stop_event.is_set():
            try:
                if self.host and self.port:
                    self.__socket = init_socket(self.host, self.port)
                self.__cap = cv2.VideoCapture(self.rtsp_uri)
                await asyncio.sleep(1)
                await self._get_stream_fps()
                if not self.__cap.isOpened():
                    raise ConnectionError("Failed to open capture")
                break
            except (TimeoutError, ConnectionError) as e:
                _log.error(f"Failed to connect: {e.__class__.__name__}: {e}")
            finally:
                await asyncio.sleep(1)

    async def _close(self):
        if self.__cap:
            self.__cap.release()
            self.__cap = None
        self.__status = RTSPClient.Status.Stopped
        self.__frame = None
        if self.__socket:
            self.__socket.close()
            self.__socket = None

    async def _reconnect(self):
        if self.__cap is None:
            _log.info("Connecting...")
        else:
            _log.info("Connection lost, Reconnecting...")
        await self._close()
        await self._open()

    def _read_frame(self):
        ret, frame = self.__cap.read()
        if not ret:
            raise ConnectionError("Failed to read frame")
        return frame

    async def _read_frame_with_timeout(self, timeout=2):
        loop = asyncio.get_event_loop()
        try:
            frame = await loop.run_in_executor(self._executor, self._read_frame)
            return frame
        except FuturesTimeoutError:
            raise ConnectionError("Read frame timeout")

    async def run_async(self):
        try:
            _log.info("Running RTSP client")
            await self._reconnect()
            while not self._stop_event.is_set():
                try:
                    if self.__cap and self.__cap.isOpened():
                        frame = await asyncio.wait_for(self._read_frame_with_timeout(), timeout=1)
                        self.__status = RTSPClient.Status.Running
                        self.__frame = frame
                        await asyncio.sleep(1 / (self.fps * 2))
                    else:
                        raise ConnectionError("Capture not opened")
                except (ConnectionError, FuturesTimeoutError) as e:
                    self.__status = RTSPClient.Status.Error
                    _log.error(f"{e.__class__.__name__}: {e}")
                    await self._reconnect()
                except Exception as e:
                    self.__status = RTSPClient.Status.Error
                    _log.exception(e)
                    await self._reconnect()
        except asyncio.CancelledError:
            _log.debug("RTSP client canceled")
        finally:
            await self._close()
            _log.debug("RTSP client finalized")

    def _run_async_in_thread(self):
        asyncio.run(self.run_async())

    async def stop(self):
        _log.info("RTSP client stop event set: True")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        await self._close()
        if self._executor:
            self._executor.shutdown(wait=True)

    async def run_in_executor(self):
        loop = asyncio.get_running_loop()
        self._executor = ThreadPoolExecutor()
        self._task = loop.run_in_executor(self._executor, self._run_async_in_thread)

    @staticmethod
    async def resize_frame(frame, width, height):
        frame_height, frame_width = frame.shape[:2]
        aspect_ratio = frame_width / frame_height

        if width / height > aspect_ratio:
            new_height = int(height)
            new_width = int(height * aspect_ratio)
        else:
            new_width = int(width)
            new_height = int(width / aspect_ratio)

        resized_frame = cv2.resize(frame, (new_width, new_height))
        return resized_frame

    async def shot(self, filename):
        if (frame := self.frame) is not None:
            cv2.imwrite(filename + '.png', frame)
            return filename + '.png'

    @property
    def webframe(self):
        if (frame := self.frame) is not None:
            _, encoded_frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
            return encoded_frame.tobytes()
        return None


def send_command_receive_response(command, socket):
    socket.sendall(command.encode())
    response = socket.recv(1024)
    return response.decode()


def init_socket(host, port):
    if not ping(host):
        raise ConnectionError("Host is not reachable")
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.connect((host, port))
    init_command = "CMD_RTSP_TRANS_START"
    init_response = send_command_receive_response(init_command, soc)
    _log.info(f"Response: {init_response}")
    if "CMD_ACK_START_RTSP_LIVE" in init_response:
        return soc
    raise Exception("Soc err")


def ping(host):
    param = '-n' if sys.platform == 'win32' else '-c'
    command = ['ping', param, '1', host]
    with subprocess.Popen(command, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          creationflags=CREATE_NO_WINDOW) as process:
        stdout, stderr = process.communicate()
        return process.returncode == 0
