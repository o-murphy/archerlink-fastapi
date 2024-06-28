import asyncio
import logging
import cv2
import numpy as np

_log = logging.getLogger('Recorder')
_log.setLevel(logging.DEBUG)


class MovRecorder:
    def __init__(self, rtsp, on_error):
        self.filename = None
        self.rtsp = rtsp
        self.recording = False
        self.output_container = None
        self._task = None
        self._error = None
        self.on_error = on_error

    async def start_async_recording(self, filename):
        self.filename = filename + '.mov'
        self.recording = True
        self._task = asyncio.create_task(self.record_loop())

    async def stop_recording(self):
        self.recording = False
        if self._task:
            await self._task
        return self.filename, self._error

    async def record_loop(self):
        self._error = None
        try:
            height, width, _ = self.rtsp.frame.shape
            fps = self.rtsp.fps

            self.output_container = cv2.VideoWriter(
                self.filename,
                # cv2.VideoWriter_fourcc(*'mp4v'),  # Use 'mp4v' codec for .mov files
                cv2.VideoWriter.fourcc(*'mp4v'),  # Use 'mp4v' codec for .mov files
                fps,
                (width, height)
            )

            while self.recording:
                frame = self.rtsp.frame
                if frame is None:
                    await asyncio.sleep(1 / self.rtsp.fps)
                    continue  # Skip if no frame is available

                # Write the frame to the output file
                self.output_container.write(frame)

                # Simulate a small delay to avoid blocking the event loop
                await asyncio.sleep(1 / self.rtsp.fps)

        except Exception as err:
            self._error = err
            _log.exception("Recording error")

        finally:
            if self.output_container:
                self.output_container.release()
            if self._error and callable(self.on_error):
                await self.on_error()
            if self.recording:
                self.recording = False
