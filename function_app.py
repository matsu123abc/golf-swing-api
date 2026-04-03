import azure.functions as func
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from mangum import Mangum

import uuid
import shutil
import os
import cv2
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()
handler = Mangum(app)

# 一時保存ディレクトリ
UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =============================
# 画像保存
# =============================
def save_upload_file(upload_file: UploadFile, save_path: str):
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


# =============================
# フレーム抽出（YOLOなし）
# =============================
def extract_frames(video_path, output_dir, interval=5):
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    saved_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % interval == 0:
            frame_path = os.path.join(output_dir, f"frame_{saved_count:03d}.jpg")
            cv2.imwrite(frame_path, frame)
            saved_count += 1

        frame_count += 1

    cap.release()
    return saved_count


# =============================
# HTML UI
# =============================
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <body>
            <h2>スイング動画アップロード（YOLOなし版）</h2>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept="video/*">
                <button type="submit">アップロード</button>
            </form>
        </body>
    </html>
    """


# =============================
# 動画アップロード
# =============================
@app.post("/upload")
async def upload_video(file: UploadFile):
    video_id = str(uuid.uuid4())
    video_path = f"{UPLOAD_DIR}/{video_id}.mp4"
    frame_dir = f"{UPLOAD_DIR}/{video_id}_frames"

    save_upload_file(file, video_path)

    # フレーム抽出（YOLOなし）
    count = extract_frames(video_path, frame_dir, interval=5)

    return {
        "message": "アップロード完了（YOLOなし）",
        "frames": count,
        "frame_dir": frame_dir
    }


# =============================
# Azure Functions エントリポイント
# =============================
async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await handler(req, context)
