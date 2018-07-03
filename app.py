import cv2
import asyncio
from starlette import Response, Router, Path


with open("index.html", "r") as f:
    content = f.read()


class Home:
    def __init__(self, scope):
        self.scope = scope

    async def __call__(self, receive, send):
        response = Response(content, media_type="text/html")
        await response(receive, send)


class Camera:
    def __init__(self):
        self.video_source = "sample.mp4"

    async def frames(self):
        video = cv2.VideoCapture(self.video_source)
        if not video.isOpened():
            raise RuntimeError("Could not start video.")

        frame_total = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0

        while True:
            if frame_count == frame_total:
                frame_count = 0
                video = cv2.VideoCapture(self.video_source)
            ret, frame = video.read()
            frame_count += 1

            frame_bytes = cv2.imencode(".jpg", frame)[1].tobytes()
            yield frame_bytes
            await asyncio.sleep(0.01)


class Stream:
    def __init__(self, scope):
        self.scope = scope
        self.camera = Camera()

    async def __call__(self, receive, send):
        message = await receive()

        if message["type"] == "http.request":

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"Content-Type", b"multipart/x-mixed-replace; boundary=frame"]
                    ],
                }
            )
            while True:
                async for frame in self.camera.frames():
                    data = b"".join(
                        [
                            b"--frame\r\n",
                            b"Content-Type: image/jpeg\r\n\r\n",
                            frame,
                            b"\r\n",
                        ]
                    )

                    await send(
                        {"type": "http.response.body", "body": data, "more_body": True}
                    )


app = Router(
    [
        Path("/", app=Home, methods=["GET"]),
        Path("/stream/", app=Stream, methods=["GET"]),
    ]
)
