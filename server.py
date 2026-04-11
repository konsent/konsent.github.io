#!/usr/bin/env python3
"""
블로그 업로드 웹서버
실행: python3 server.py
브라우저: http://localhost:5555
"""

import glob
import os
import sys
from datetime import datetime
from flask import Flask, jsonify, request, send_file, send_from_directory

# new_post.py 와 같은 폴더에 있어야 함
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from new_post import CATEGORIES, create_post

app = Flask(__name__)
REPO_ROOT   = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS   = os.path.expanduser('~/Downloads')
IMAGE_EXTS  = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'PNG', 'JPG', 'JPEG'}


# ─── 라우트 ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(REPO_ROOT, 'uploader.html')


@app.route('/api/images')
def list_images():
    """Downloads 폴더의 최근 이미지 60개"""
    files = []
    for ext in IMAGE_EXTS:
        files += glob.glob(os.path.join(DOWNLOADS, f'*.{ext}'))
    files.sort(key=os.path.getmtime, reverse=True)
    return jsonify([os.path.basename(f) for f in files[:60]])


@app.route('/dl/<path:filename>')
def serve_download(filename):
    """Downloads 폴더의 파일을 썸네일로 제공"""
    safe = os.path.basename(filename)
    path = os.path.join(DOWNLOADS, safe)
    if not os.path.exists(path):
        return '', 404
    return send_file(path)


@app.route('/api/create', methods=['POST'])
def api_create():
    data = request.get_json()
    try:
        # git lock 파일 자동 정리
        lock = os.path.join(REPO_ROOT, '.git', 'index.lock')
        if os.path.exists(lock):
            os.remove(lock)

        date = datetime.strptime(data['date'], '%Y-%m-%d') if data.get('date') else None
        create_post(
            title=data['title'].strip(),
            category=data['category'],
            slug=data['slug'].strip(),
            filenames=data.get('files', []),
            content=data.get('content', '').strip(),
            links=data.get('links', []),
            date=date,
            no_push=data.get('no_push', False),
        )
        return jsonify({'ok': True})
    except RuntimeError as e:
        return jsonify({'ok': False, 'error': str(e)})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


# ─── 실행 ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = 5555
    print(f'\n  블로그 업로더 실행 중')
    print(f'  → http://localhost:{port}\n')
    app.run(debug=False, port=port)
