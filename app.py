from flask import Flask, send_file, jsonify, request, send_from_directory
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import requests


app = Flask(__name__)

BASE_URL = "https://server1.example.xyz/uploads/myfiless/id/"
THUMBNAIL_DIR = "thumbnails"
os.makedirs(THUMBNAIL_DIR, exist_ok=True)


def url_exists(url):
    try:
        r = requests.head(url, timeout=5)
        return r.status_code == 200
    except:
        return False

def get_video_url(index):
    return f"{BASE_URL}{60674 + index}.mp4"

def get_thumbnail_path(index):
    return os.path.join(THUMBNAIL_DIR, f"thumb_{index}.jpg")

executor = ThreadPoolExecutor(max_workers=4)  # or more if your CPU can handle it

def generate_thumbnail_async(index):
    video_url = get_video_url(index)
    if not url_exists(video_url):
        # Return a dummy future that resolves to None to keep behavior consistent
        from concurrent.futures import Future
        future = Future()
        future.set_result(None)
        return future
    else:
        return executor.submit(generate_thumbnail, index)

def generate_thumbnail(index):
    thumb_path = get_thumbnail_path(index)
    if os.path.exists(thumb_path):
        return thumb_path

    video_url = get_video_url(index)
    cmd = [
        "ffmpeg",
        "-ss", "00:00:01",
        "-i", video_url,
        "-frames:v", "1",
        "-q:v", "2",
        "-y",
        thumb_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return thumb_path if os.path.exists(thumb_path) else None
    except Exception as e:
        print(f"Failed: {e}")
        return None

@app.route("/thumbnails")
def list_thumbnails():
    start = int(request.args.get("start", 0))
    count = int(request.args.get("count", 10))
    indices = list(range(start, start + count))

    # Launch generation in parallel
    futures = [generate_thumbnail_async(i) for i in indices]

    items = []
    for i, future in zip(indices, futures):
        path = future.result()
        if path:
            items.append({
                "index": i,
                "thumb": f"/thumbnail/{i}",
                "video": get_video_url(i)
            })

    return jsonify(items)


@app.route("/thumbnail/<int:index>")
def serve_thumbnail(index):
    path = get_thumbnail_path(index)
    if os.path.exists(path):
        return send_file(path, mimetype='image/jpeg')
    return "Not found", 404

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

if __name__ == "__main__":
    app.run(debug=True)
