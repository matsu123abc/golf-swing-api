import azure.functions as func
from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse
from mangum import Mangum

import uuid
import shutil
import os

app = FastAPI()
handler = Mangum(app)

# 一時保存ディレクトリ
UPLOAD_DIR = "/tmp/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# =============================
# 画像保存（OpenCVなし）
# =============================
def save_upload_file(upload_file: UploadFile, save_path: str):
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)


# =============================
# HTML UI
# =============================
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <body>
            <h2>スイング動画アップロード（テスト版）</h2>
            <form action="/upload" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept="video/*">
                <button type="submit">アップロード</button>
            </form>
        </body>
    </html>
    """


# =============================
# 動画アップロード（OpenCVなし）
# =============================
@app.post("/upload")
async def upload_video(file: UploadFile):
    video_id = str(uuid.uuid4())
    video_path = f"{UPLOAD_DIR}/{video_id}.mp4"

    save_upload_file(file, video_path)

    return {
        "message": "アップロード完了（OpenCVなしテスト）",
        "saved_path": video_path
    }


# =============================
# Azure Functions エントリポイント
# =============================
async def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return await handler(req, context)
