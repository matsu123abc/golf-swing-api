import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

def crop_person(image_path):
    img = cv2.imread(image_path)
    if img is None:
        return image_path

    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    rects, _ = hog.detectMultiScale(img, winStride=(8, 8))

    if len(rects) == 0:
        return image_path  # 検出できない場合は元画像のまま

    # 最初の人物を採用
    (x, y, w, h) = rects[0]

    # 少し余白をつけてクロップ
    pad = 20
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img.shape[1], x + w + pad)
    y2 = min(img.shape[0], y + h + pad)

    cropped = img[y1:y2, x1:x2]
    cv2.imwrite(image_path, cropped)

    return image_path

def create_collage_mid10(image_paths, output_path):
    # 画像を読み込み
    images = [Image.open(p) for p in image_paths]

    # 幅300pxに統一
    resized = [img.resize((300, int(img.height * 300 / img.width))) for img in images]

    # 横5 × 縦2 のコラージュ
    w, h = resized[0].size
    collage = Image.new("RGB", (w * 5, h * 2), (0, 0, 0))

    # フォント設定
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    for idx, img in enumerate(resized):
        x = (idx % 5) * w
        y = (idx // 5) * h
        collage.paste(img, (x, y))

        # 番号描画（白文字＋黒縁取り）
        draw = ImageDraw.Draw(collage)
        num = str(idx + 1)
        draw.text((x + 10, y + 10), num, font=font, fill="black")
        draw.text((x + 12, y + 12), num, font=font, fill="white")

    collage.save(output_path)
    return output_path

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

    video_path = f"{save_dir}/{video.filename}"
    with open(video_path, "wb") as f:
        f.write(await video.read())

    return f"""
    <h2>🏌️‍♂️ アップロード完了：{video.filename}</h2>

    <video id="swingVideo" width="360" controls>
        <source src="/tools/swing/video/{video.filename}" type="video/mp4">
    </video>

    <div style="margin-top:10px;">
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

    <hr>

    <h3>mid10 抽出</h3>
    <form action="/tools/swing/extract-mid10" method="post" enctype="multipart/form-data">
        <input type="file" name="video" accept="video/mp4">
        <button type="submit">mid10 を抽出する</button>
    </form>
    """

@app.post("/tools/swing/extract-mid10", response_class=HTMLResponse)
async def extract_mid10(video: UploadFile = File(...)):
    save_dir = "/home/site/wwwroot/uploads"
    os.makedirs(save_dir, exist_ok=True)

    video_path = f"{save_dir}/{video.filename}"
    with open(video_path, "wb") as f:
        f.write(await video.read())

    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # mid10 = 40%〜50%
    start = int(total_frames * 0.40)
    end = int(total_frames * 0.50)

    # 10枚だけ均等に抽出
    indices = np.linspace(start, end - 1, 10, dtype=int)

    extracted_paths = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        frame_path = f"{save_dir}/mid10_{idx}.jpg"
        cv2.imwrite(frame_path, frame)

        # 人物クロップ
        crop_person(frame_path)

        extracted_paths.append(frame_path)

    cap.release()

    # コラージュ生成
    collage_path = f"{save_dir}/mid10_collage.jpg"
    create_collage_mid10(extracted_paths, collage_path)

    # HTML（10枚は表示しない）
    html = "<h2>mid10 コラージュ画像</h2>"
    html += f'<img src="/tools/swing/image/mid10_collage.jpg" width="600"><br><br>'

    # ダウンロードボタン
    html += f'''
    <a href="/tools/swing/image/mid10_collage.jpg" download="mid10_collage.jpg">
        <button>コラージュ画像をダウンロード</button>
    </a>
    '''

    return html

@app.get("/tools/swing/image/{filename}")
def get_image(filename: str):
    file_path = f"/home/site/wwwroot/uploads/{filename}"
    return FileResponse(file_path, media_type="image/jpeg")
