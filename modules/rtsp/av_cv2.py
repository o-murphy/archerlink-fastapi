import asyncio
import logging
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

import av
import cv2
from aiortc.contrib.media import MediaPlayer
from aiortc.mediastreams import MediaStreamError

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
        self.__player: [MediaPlayer, None] = None
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
    def _player(self):
        return self.__player

    @property
    def _socket(self):
        return self.__socket

    async def _get_stream_fps(self):
        if self.__player:
            container = self.__player.__dict__.get("_MediaPlayer__container", None)
            if container:
                stream = container.streams.video[0]
                fps = stream.average_rate
                if fps:
                    self.__fps = fps
                else:
                    _log.warning(f"Stream FPS not available, adjusted to default")
                _log.info(f"Stream FPS: {self.__fps}")
            else:
                _log.info("No container available to retrieve FPS")

    async def _open(self):
        while not self._stop_event.is_set():
            try:
                if self.host and self.port:
                    self.__socket = init_socket(self.host, self.port)
                self.__player = MediaPlayer(file=self.rtsp_uri, format='rtsp', options=self.options, timeout=2)
                await asyncio.sleep(1)
                await self._get_stream_fps()
                break
            except (TimeoutError, ConnectionError, av.AVError) as e:
                _log.error(f"Failed to connect: {e.__class__.__name__}: {e}")
            finally:
                await asyncio.sleep(1)

    async def _close(self):
        if self.__player:
            self.__player.video.stop()
            self.__player = None
        self.__status = RTSPClient.Status.Stopped
        self.__frame = None
        if self.__socket:
            self.__socket.close()
            self.__socket = None

    async def _reconnect(self):
        if self.__player is None:
            _log.info("Connecting...")
        else:
            _log.info("Connection lost, Reconnecting...")
        await self._close()
        await self._open()

    async def run_async(self):
        try:
            _log.info("Running RTSP client")
            await self._reconnect()
            while not self._stop_event.is_set():
                try:
                    if self.__player and self.__player.video:
                        frame = await self.__player.video.recv()
                        if frame:
                            self.__status = RTSPClient.Status.Running
                            self.__frame = frame.to_ndarray(format="bgr24")
                        else:
                            _log.warning("No frame received")
                            self.__frame = None
                        await asyncio.sleep(1 / (self.fps * 2))
                        continue
                    else:
                        raise ConnectionError("No player connected")
                except (ConnectionError, av.AVError, MediaStreamError) as e:
                    self.__status = RTSPClient.Status.Error
                    _log.error(f"{e.__class__.__name__}: {e}")
                except Exception as e:
                    self.__status = RTSPClient.Status.Error
                    _log.exception(e)
                await asyncio.sleep(2)
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
            # scale_factor = 2
            # upscaled_frame = cv2.resize(frame, None, fx=scale_factor, fy=scale_factor, interpolation=cv2.INTER_LANCZOS4)
            # _, encoded_frame = cv2.imencode('.jpg', upscaled_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
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
    with subprocess.Popen(command,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          creationflags=CREATE_NO_WINDOW
                          ) as process:
        stdout, stderr = process.communicate()
        return process.returncode == 0
