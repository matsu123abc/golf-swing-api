import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, FileResponse
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

UPLOAD_DIR = "/home/site/wwwroot/uploads"


def crop_center(image_path, x1p, x2p, y1p, y2p):
    img = cv2.imread(image_path)
    if img is None:
        return image_path

    h, w, _ = img.shape

    x1 = int(w * (x1p / 100))
    x2 = int(w * (x2p / 100))
    y1 = int(h * (y1p / 100))
    y2 = int(h * (y2p / 100))

    cropped = img[y1:y2, x1:x2]
    cv2.imwrite(image_path, cropped)

    return image_path


def create_collage_mid10(image_paths, output_path):
    images = [Image.open(p) for p in image_paths]
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

    collage.save(output_path)
    return output_path

@app.get("/tools/swing", response_class=HTMLResponse)
def swing_page():
    html = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
@media screen and (orientation: portrait) {
    h2 {
        font-size: 34px;
        text-align: center;
    }
    input[type="file"] {
        font-size: 28px;
        padding: 20px;
    }
    button {
        font-size: 32px;
        padding: 26px;
        width: 100%;
        border-radius: 14px;
    }
}
</style>
</head>

<body>

<h2>🏌️‍♂️ スイング動画アップロード</h2>

<form action="/tools/swing/upload" method="post" enctype="multipart/form-data">
    <input type="file" name="video" accept="video/mp4">
    <button type="submit">アップロード</button>
</form>

</body>
</html>
"""
    return HTMLResponse(content=html)

@app.get("/tools/swing/video/{filename}")
def get_video(filename: str):
    file_path = f"{UPLOAD_DIR}/{filename}"
    return FileResponse(file_path, media_type="video/mp4")


@app.get("/tools/swing/image/{filename}")
def get_image(filename: str):
    file_path = f"{UPLOAD_DIR}/{filename}"
    return FileResponse(file_path, media_type="image/jpeg")


@app.post("/tools/swing/upload", response_class=HTMLResponse)
async def upload_video(video: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    video_path = f"{UPLOAD_DIR}/{video.filename}"
    with open(video_path, "wb") as f:
        f.write(await video.read())

    html = """
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
/* スマホ縦画面で文字を特大にする */
@media screen and (orientation: portrait) {
    body {
        font-size: 28px;
    }
    h2, h3 {
        font-size: 32px;
    }
    button {
        font-size: 30px;
        padding: 24px;
        border-radius: 14px;
    }
    input[type="range"] {
        width: 90%;
        height: 40px;
    }
    span {
        font-size: 28px;
    }
    #videoContainer {
        transform: scale(1.2);
        transform-origin: top left;
    }
}
</style>

<h2>🏌️‍♂️ アップロード完了：{video_name}</h2>

<div id="videoContainer" style="position: relative; display: inline-block;">
    <video id="swingVideo" width="360" controls>
        <source src="/tools/swing/video/{video_name}" type="video/mp4">
    </video>

    <div id="cropPreview" style="
        position: absolute;
        border: 2px solid red;
        background-color: rgba(255,0,0,0.15);
        pointer-events: none;
    "></div>
</div>

<div style="margin-top:10px;">
    <button onclick="setSpeed(0.25)">0.25x</button>
    <button onclick="setSpeed(0.5)">0.5x</button>
    <button onclick="setSpeed(0.75)">0.75x</button>
    <button onclick="setSpeed(1.0)">1.0x</button>
</div>

<script>
function setSpeed(rate) {
    document.getElementById('swingVideo').playbackRate = rate;
}
</script>

<div style="width:360px; height:10px; background:#ddd; margin-top:10px; position:relative;">
    <div id="playProgress" style="
        position:absolute;
        top:0;
        left:0;
        height:10px;
        width:0%;
        background:#4CAF50;
    "></div>

    <div id="startMarker" style="
        position:absolute;
        top:0;
        width:2px;
        height:10px;
        background:red;
    "></div>

    <div id="endMarker" style="
        position:absolute;
        top:0;
        width:2px;
        height:10px;
        background:red;
    "></div>
</div>

<hr>

<h3>抽出範囲（%）</h3>
抽出開始（start）:
<input type="range" name="start" id="startRange" min="0" max="90" value="40" oninput="updateMarkers()"> 
<span id="startv">40%</span><br>

抽出終了（end）:
<input type="range" name="end" id="endRange" min="10" max="100" value="50" oninput="updateMarkers()"> 
<span id="endv">50%</span><br><br>

<h3>クロップ範囲（%）</h3>

<form action="/tools/swing/extract-mid10" method="post" enctype="multipart/form-data">
    <input type="hidden" name="video_name" value="{video_name}">

    左（x1）: <input type="range" name="x1" min="0" max="50" value="30" oninput="updatePreview()"> <span id="x1v">30%</span><br>
    右（x2）: <input type="range" name="x2" min="50" max="100" value="70" oninput="updatePreview()"> <span id="x2v">70%</span><br>
    上（y1）: <input type="range" name="y1" min="0" max="50" value="10" oninput="updatePreview()"> <span id="y1v">10%</span><br>
    下（y2）: <input type="range" name="y2" min="50" max="100" value="90" oninput="updatePreview()"> <span id="y2v">90%</span><br><br>

    <input type="hidden" name="start" id="startHidden" value="40">
    <input type="hidden" name="end" id="endHidden" value="50">

    <button type="submit">mid10 を抽出する</button>
</form>

<script>
function updatePreview() {
    const video = document.getElementById("swingVideo");
    const preview = document.getElementById("cropPreview");

    const x1 = document.querySelector("input[name='x1']").value;
    const x2 = document.querySelector("input[name='x2']").value;
    const y1 = document.querySelector("input[name='y1']").value;
    const y2 = document.querySelector("input[name='y2']").value;

    document.getElementById("x1v").innerText = x1 + "%";
    document.getElementById("x2v").innerText = x2 + "%";
    document.getElementById("y1v").innerText = y1 + "%";
    document.getElementById("y2v").innerText = y2 + "%";

    const vw = video.clientWidth;
    const vh = video.clientHeight;

    preview.style.left = (vw * x1 / 100) + "px";
    preview.style.top = (vh * y1 / 100) + "px";
    preview.style.width = (vw * (x2 - x1) / 100) + "px";
    preview.style.height = (vh * (y2 - y1) / 100) + "px";
}

function updateMarkers() {
    const start = document.getElementById("startRange").value;
    const end = document.getElementById("endRange").value;

    document.getElementById("startv").innerText = start + "%";
    document.getElementById("endv").innerText = end + "%";

    document.getElementById("startHidden").value = start;
    document.getElementById("endHidden").value = end;

    const barWidth = 360;

    document.getElementById("startMarker").style.left = (barWidth * start / 100) + "px";
    document.getElementById("endMarker").style.left = (barWidth * end / 100) + "px";
}

function updatePlayProgress() {
    const video = document.getElementById("swingVideo");
    const progress = document.getElementById("playProgress");

    if (!video.duration) {
        requestAnimationFrame(updatePlayProgress);
        return;
    }

    const percent = (video.currentTime / video.duration) * 100;
    progress.style.width = percent + "%";

    requestAnimationFrame(updatePlayProgress);
}

window.onload = function() {
    updatePreview();
    updateMarkers();
    updatePlayProgress();
};
</script>
"""

    return HTMLResponse(content=html.format(video_name=video.filename))



@app.post("/tools/swing/extract-mid10", response_class=HTMLResponse)
async def extract_mid10(
    video_name: str = Form(...),
    x1: int = Form(...),
    x2: int = Form(...),
    y1: int = Form(...),
    y2: int = Form(...),
    start: int = Form(...),
    end: int = Form(...)
):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    video_path = f"{UPLOAD_DIR}/{video_name}"
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    start_frame = int(total_frames * (start / 100))
    end_frame = int(total_frames * (end / 100))

    indices = np.linspace(start_frame, max(start_frame, end_frame - 1), 10, dtype=int)

    extracted_paths = []

    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if not ret:
            continue

        frame_path = f"{UPLOAD_DIR}/mid10_{idx}.jpg"
        cv2.imwrite(frame_path, frame)

        crop_center(frame_path, x1, x2, y1, y2)
        extracted_paths.append(frame_path)

    cap.release()

    collage_path = f"{UPLOAD_DIR}/mid10_collage.jpg"
    create_collage_mid10(extracted_paths, collage_path)

    html = "<h2>mid10 コラージュ画像</h2>"
    html += f'<img src="/tools/swing/image/mid10_collage.jpg" width="600"><br><br>'

    html += f'''
    <a href="/tools/swing/image/mid10_collage.jpg" download="mid10_collage.jpg">
        <button>コラージュ画像をダウンロード</button>
    </a>
    '''

    html += """
    <hr>
    <h3>Chat に投げるプロンプト（コピペ用）</h3>

    <textarea id="promptArea" style="width:700px; height:260px;">
以下はゴルフスイングの mid10（任意設定）の連続写真（1〜10番）です。
クラブの動き・フェース向き・手元の軌道・クラブパスのみを分析してください。
人物の身体的特徴には触れないでください。

【分析内容】
1. 球筋から推測されるクラブの動き
2. どの局面（1〜10番）で問題が起きているか
3. その局面で起きているクラブの動作
4. その動作が球筋にどう影響したか
5. 局面番号ごとの改善ポイント（クラブの動きのみ）
6. 局面番号ごとの練習ドリル（クラブ軌道・フェース向きに限定）

【球筋】
（ここに球筋を入力）

【画像】
（上のコラージュ画像を Chat に貼ってください）
    </textarea>

    <button onclick="copyPrompt()" style="margin-top:10px;">コピー</button>

    <script>
    function copyPrompt() {
        const textarea = document.getElementById("promptArea");
        textarea.select();
        textarea.setSelectionRange(0, 99999);

        navigator.clipboard.writeText(textarea.value)
            .then(() => {
                alert("コピーしました！");
            })
            .catch(err => {
                alert("コピーに失敗しました");
            });
    }
    </script>
    """

    return html
