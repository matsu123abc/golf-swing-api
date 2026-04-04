from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import os

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


@app.post("/tools/swing/upload")
async def upload_video(video: UploadFile = File(...)):
    save_path = f"/home/site/wwwroot/uploads/{video.filename}"

    os.makedirs("/home/site/wwwroot/uploads", exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(await video.read())

    return {"message": "アップロード成功", "filename": video.filename}
