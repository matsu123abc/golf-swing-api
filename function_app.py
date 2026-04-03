import azure.functions as func
from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import HTMLResponse, FileResponse
from mangum import Mangum

import uuid
import shutil
import os
import cv2
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# FastAPI アプリ
# ==========================================
app = FastAPI()

# ==========================================
# 保存先はすべて /tmp（Function App の高速領域）
# ==========================================
TMP_DIR = "/tmp"

# ==========================================
# YOLO モデル（遅延ロード & /tmp に配置）
# ==========================================
yolo_model = None

def get_model():
    global yolo_model
    if yolo_model is None:
        model_path = f"{TMP_DIR}/yolov8s.pt"

        # モデルが無ければダウンロード（初回のみ）
        if not os.path.exists(model_path):
            import requests
            url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt"
            r = requests.get(url)
            with open(model_path, "wb") as f:
                f.write(r.content)

        yolo_model = YOLO(model_path)

    return yolo_model


# ==========================================
# YOLO クロップ（上下40%余白）
# ==========================================
def crop_person(image_path, margin_x=0.05, margin_y=0.40):
    img = cv2.imread(image_path)
    if img is None:
        return image_path

    model = get_model()
    results = model(img)[0]

    boxes = [b for b in results.boxes if int(b.cls[0]) == 0]
    if not boxes:
        return image_path

    boxes.sort(
        key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1]),
        reverse=True
    )
    box = boxes[0]
    x1, y1, x2, y2 = map(int, box.xyxy[0])

    h, w = img.shape[:2]

    dx = int((x2 - x1) * margin_x)
    dy = int((y2 - y1) * margin_y)

    x1 = max(0, x1 - dx)
    x2 = min(w, x2 + dx)
    y1 = max(0, y1 - dy)
    y2 = min(h, y2 + dy)

    cropped = img[y1:y2, x1:x2]
    cv2.imwrite(image_path, cropped)
    return image_path


# ==========================================
# 連続写真10枚（0〜90%）
# ==========================================
def extract_10_frames(video_path):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for i in range(10):
        p = i * 0.1
        frame_no = int(total * p)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if ret:
            img_path = f"{video_path}_seq_{i}.jpg"
            cv2.imwrite(img_path, frame)
            crop_person(img_path)

    cap.release()


# ==========================================
# mid10 抽出（任意範囲）
# ==========================================
def extract_mid10(video_path, start_ratio, end_ratio):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    for i in range(10):
        p = start_ratio + (end_ratio - start_ratio) * (i / 9)
        frame_no = int(total * p)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
        ret, frame = cap.read()
        if ret:
            img_path = f"{video_path}_mid_{i}.jpg"
            cv2.imwrite(img_path, frame)
            crop_person(img_path)

    cap.release()


# ==========================================
# mid10 コラージュ生成
# ==========================================
def create_collage_mid10(file_id):
    images = [Image.open(f"{TMP_DIR}/{file_id}.mp4_mid_{i}.jpg") for i in range(10)]
    resized = [img.resize((300, int(img.height * 300 / img.width))) for img in images]

    w, h = resized[0].size
    collage = Image.new("RGB", (w * 5, h * 2), (0, 0, 0))

    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()

    for idx, img in enumerate(resized):
        x = (idx % 5) * w
        y = (idx // 5) * h
        collage.paste(img, (x, y))

        draw = ImageDraw.Draw(collage)
        num = str(idx + 1)
        draw.text((x + 10, y + 10), num, font=font, fill="black")
        draw.text((x + 12, y + 12), num, font=font, fill="white")

    out = f"{TMP_DIR}/{file_id}.mp4_mid10_collage.jpg"
    collage.save(out)
    return out


# ==========================================
# 画面①：アップロード画面
# ==========================================
@app.get("/tools/swing/upload")
def upload_page():
    return HTMLResponse("""
        <h2>スイング動画をアップロード</h2>
        <form action="/tools/swing/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="video" accept="video/mp4">
            <button type="submit">アップロード</button>
        </form>
    """)


# ==========================================
# 画面①：アップロード → 連続写真表示
# ==========================================
@app.post("/tools/swing/upload")
async def upload(video: UploadFile):
    file_id = str(uuid.uuid4())
    save_path = f"{TMP_DIR}/{file_id}.mp4"

    with open(save_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    extract_10_frames(save_path)

    return HTMLResponse(f"""
        <h2>動画アップロード完了</h2>

        <video width="480" controls>
            <source src="/tools/swing/video/{file_id}.mp4">
        </video>

        <h3>連続写真（0〜90%）</h3>
        <div style="display:flex; gap:10px;">
            {''.join([f"<img id='seq_{i}' src='/tools/swing/video/{file_id}.mp4_seq_{i}.jpg' width='120' style='border:1px solid #ccc;'>" for i in range(10)])}
        </div>

        <h3>mid10 抽出範囲（スライダー）</h3>
        開始: <input type="range" id="mid10_start" min="0" max="1" step="0.01" value="0.40">
        <span id="mid10_start_val">0.40</span><br>

        終了: <input type="range" id="mid10_end" min="0" max="1" step="0.01" value="0.50">
        <span id="mid10_end_val">0.50</span><br><br>

        <form action="/tools/swing/extract_mid10" method="post">
            <input type="hidden" name="file_id" value="{file_id}">
            <input type="hidden" id="mid10_start_form" name="mid10_start" value="0.40">
            <input type="hidden" id="mid10_end_form" name="mid10_end" value="0.50">
            <button type="submit">mid10 を抽出する</button>
        </form>

        <script>
        function updateHighlight() {{
            const start = parseFloat(document.getElementById("mid10_start").value);
            const end   = parseFloat(document.getElementById("mid10_end").value);

            for (let i = 0; i < 10; i++) {{
                const ratio = i * 0.1;
                const img = document.getElementById("seq_" + i);
                if (ratio >= start && ratio <= end) {{
                    img.style.border = "4px solid red";
                }} else {{
                    img.style.border = "1px solid #ccc";
                }}
            }}

            document.getElementById("mid10_start_val").innerText = start.toFixed(2);
            document.getElementById("mid10_end_val").innerText = end.toFixed(2);

            document.getElementById("mid10_start_form").value = start;
            document.getElementById("mid10_end_form").value = end;
        }}

        document.getElementById("mid10_start").oninput = updateHighlight;
        document.getElementById("mid10_end").oninput = updateHighlight;

        updateHighlight();
        </script>
    """)


# ==========================================
# 画面②：mid10 抽出結果
# ==========================================
@app.post("/tools/swing/extract_mid10")
async def extract_mid10_page(
    file_id: str = Form(...),
    mid10_start: float = Form(...),
    mid10_end: float = Form(...)
):
    video_path = f"{TMP_DIR}/{file_id}.mp4"

    extract_mid10(video_path, mid10_start, mid10_end)
    create_collage_mid10(file_id)

    return HTMLResponse("""
        <h2>mid10 抽出結果</h2>

        <h3>mid10（10枚）</h3>
        <div style="display:flex; flex-wrap:wrap; gap:10px;">
""" +
            ''.join([f"<img src='/tools/swing/video/{file_id}.mp4_mid_{i}.jpg' width='200'>" for i in range(10)]) +
"""
        </div>

        <h3>mid10 コラージュ画像</h3>
        <img src="/tools/swing/video/""" + file_id + """.mp4_mid10_collage.jpg" width="700"><br>
        <a href="/tools/swing/video/""" + file_id + """.mp4_mid10_collage.jpg" download>
            <button>コラージュ画像をダウンロード</button>
        </a>

        <br><br>
        <form action="/tools/swing/upload" method="get">
            <button>mid10 の範囲を再調整する</button>
        </form>
""")


# ==========================================
# 動画・画像配信
# ==========================================
@app.get("/tools/swing/video/{path}")
def serve_file(path: str):
    full_path = os.path.join(TMP_DIR, path)
    return FileResponse(full_path)


@app.get("/tools/swing")
def swing_top():
    return HTMLResponse("""
        <h2>🏌️‍♂️ スイング動画アップロード</h2>

        <form action="/tools/swing/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="video" accept="video/mp4">
            <button type="submit">アップロード</button>
        </form>

        <p>※ アップロード後に連続写真10枚と mid10 抽出設定が表示されます</p>
    """)


# ==========================================
# Azure Function App エントリポイント
# ==========================================
handler = Mangum(app)

async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await func.AsgiMiddleware(app).handle_async(req, context)
