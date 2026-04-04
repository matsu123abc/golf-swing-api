import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
import cv2
import numpy as np
from PIL import Image

app = FastAPI()

@app.get("/tools/swing", response_class=HTMLResponse)
def swing_page():
    return """
    <h2>🏌️‍♂️ スイング動画アップロード</h2>

    <form action="/tools/swing/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="video" accept="video/mp4">
        <button type="submit">アップロード</button>
    </form>
    """

@app.get("/tools/swing/video/{filename}")
def get_video(filename: str):
    file_path = f"/home/site/wwwroot/uploads/{filename}"
    return FileResponse(file_path, media_type="video/mp4")

@app.post("/tools/swing/upload", response_class=HTMLResponse)
async def upload_video(video: UploadFile = File(...)):
    save_dir = "/home/site/wwwroot/uploads"
    os.makedirs(save_dir, exist_ok=True)

    save_path = f"{save_dir}/{video.filename}"
    with open(save_path, "wb") as f:
        f.write(await video.read())

    return f"""
    <h2>🏌️‍♂️ アップロード完了：{video.filename}</h2>

    <video id="swingVideo" width="360" controls>
        <source src="/tools/swing/video/{video.filename}" type="video/mp4">
    </video>

    <div>
        <button onclick="setSpeed(0.25)">0.25x</button>
        <button onclick="setSpeed(0.5)">0.5x</button>
        <button onclick="setSpeed(0.75)">0.75x</button>
        <button onclick="setSpeed(1.0)">1.0x</button>
    </div>

    <script>
    function setSpeed(rate) {{
        document.getElementById('swingVideo').playbackRate = rate;
    }}
    </script>
    """

@app.post("/tools/swing/extract-mid10", response_class=HTMLResponse)
async def extract_mid10(video: UploadFile = File(...)):
    # 保存先
    save_dir = "/home/site/wwwroot/uploads"
    os.makedirs(save_dir, exist_ok=True)

    video_path = f"{save_dir}/{video.filename}"
    with open(video_path, "wb") as f:
        f.write(await video.read())

    # 動画読み込み
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # mid10 = 40%〜50%
    start = int(total_frames * 0.40)
    end = int(total_frames * 0.50)

    extracted_paths = []

    for i in range(start, end):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if not ret:
            continue

        # 保存
        frame_path = f"{save_dir}/mid10_{i}.jpg"
        cv2.imwrite(frame_path, frame)
        extracted_paths.append(frame_path)

    cap.release()

    # HTML で一覧表示
    html = "<h2>mid10 抽出フレーム</h2>"
    for p in extracted_paths:
        filename = p.split("/")[-1]
        html += f'<img src="/tools/swing/image/{filename}" width="200"><br>'

    return html

@app.get("/tools/swing/image/{filename}")
def get_image(filename: str):
    file_path = f"/home/site/wwwroot/uploads/{filename}"
    return FileResponse(file_path, media_type="image/jpeg")

