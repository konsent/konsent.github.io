#!/usr/bin/env python3
"""
konsent.github.io Jekyll 블로그 포스트 자동 생성기

[Cowork에서 사용] 파일명만 주면 Downloads 폴더에서 자동으로 가져옵니다.
  - *thumb* 포함된 파일명 → 썸네일(preview)로 자동 지정
  - 숫자로 끝나는 파일명 → 본문 이미지로 순서대로 삽입
  파일명은 원본 그대로 /photo/ 에 복사됩니다.

[터미널에서 직접 실행]
  python new_post.py --title "제목" --category short --slug my-post \
                     --files img1.jpg imgthumb.jpg img2.jpg \
                     [--downloads-dir ~/Downloads] \
                     [--content "내용"] [--date 2026-04-11] [--no-push]

카테고리:
  short     - 짧은 포스트      (layout: post)
  long      - 긴 포스트/만화   (layout: post2)
  rules     - 규칙서            (layout: post3)
  notitles  - 제목 없는 포스트  (layout: post4)
  aar       - AAR               (layout: post5)
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# ── 카테고리 설정 ─────────────────────────────────────────────────────────────
CATEGORIES = {
    'short':    {'layout': 'post',  'folder': 'short',    'flags': ['short']},
    'long':     {'layout': 'post2', 'folder': 'long',     'flags': ['long']},
    'rules':    {'layout': 'post3', 'folder': 'rules',    'flags': ['rules']},
    'notitles': {'layout': 'post4', 'folder': 'notitles', 'flags': ['rules', 'notitles', 'short', 'long']},
    'aar':      {'layout': 'post5', 'folder': 'aar',      'flags': ['rules', 'notitles', 'aar', 'short', 'long']},
}

DOWNLOADS_DIR = os.path.expanduser('~/Downloads')


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────────────
def is_thumb(filename: str) -> bool:
    """파일명에 'thumb'가 포함되어 있으면 썸네일로 판단"""
    return 'thumb' in os.path.splitext(filename)[0].lower()


def sort_key(filename: str):
    """숫자로 끝나는 파일을 숫자 순서로 정렬 (예: img1, img2, img10)"""
    name = os.path.splitext(filename)[0]
    m = re.search(r'(\d+)$', name)
    return int(m.group(1)) if m else 0


def build_front_matter(title: str, category: str, date_str: str, preview: str) -> str:
    cfg = CATEGORIES[category]
    lines = [
        '---',
        f'layout: {cfg["layout"]}',
        f'title: "{title}"',
        f'date: {date_str} 00:00:00',
        f'preview: {preview}',
        'published: true',
    ]
    for flag in cfg['flags']:
        val = '"on"' if flag == category else 'null'
        lines.append(f'{flag}: {val}')
    lines.append('---')
    return '\n'.join(lines) + '\n'


def run(cmd, cwd=None):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'[{" ".join(str(c) for c in cmd)}]\n{result.stderr.strip()}')
    return result.stdout.strip()


# ── 핵심 로직 ─────────────────────────────────────────────────────────────────
def process_files(filenames: list, downloads_dir: str, photo_dir: str):
    """
    filenames: 파일명 목록 (경로 없이 이름만, 또는 전체 경로)
    downloads_dir: 파일명만 줬을 때 찾을 기본 폴더
    photo_dir: 복사 대상 폴더 (blog/photo)

    반환값:
      thumb_web   - 썸네일 웹 경로 (e.g. /photo/260411_thumb.jpg)  또는 ''
      img_tags    - <img> 태그 목록 (순서 정렬됨)
    """
    os.makedirs(photo_dir, exist_ok=True)

    thumb_web = ''
    content_files = []

    for fname in filenames:
        # 전체 경로면 그대로, 아니면 Downloads 에서 찾기
        if os.path.isabs(fname) or os.path.sep in fname:
            src = fname
        else:
            src = os.path.join(downloads_dir, fname)

        if not os.path.exists(src):
            print(f'  [WARN] 파일 없음: {src}')
            continue

        basename = os.path.basename(src)
        dest = os.path.join(photo_dir, basename)
        shutil.copy2(src, dest)

        if is_thumb(basename):
            thumb_web = f'/photo/{basename}'
            print(f'  썸네일 복사: {basename} → /photo/')
        else:
            content_files.append(basename)
            print(f'  이미지 복사: {basename} → /photo/')

    # 숫자 순서로 정렬
    content_files.sort(key=sort_key)

    img_tags = [f'<img src="/photo/{f}" width="1000">' for f in content_files]

    # 썸네일 없으면 첫 번째 이미지를 preview로
    if not thumb_web and content_files:
        thumb_web = f'/photo/{content_files[0]}'

    return thumb_web, img_tags


def create_post(title, category, slug, filenames, content='',
                date=None, downloads_dir=DOWNLOADS_DIR, no_push=False):
    if date is None:
        date = datetime.now()

    date_str = date.strftime('%Y-%m-%d')
    repo_root = os.path.dirname(os.path.abspath(__file__))
    photo_dir = os.path.join(repo_root, 'photo')

    # 이미지 처리
    thumb_web, img_tags = process_files(filenames, downloads_dir, photo_dir)

    if not thumb_web:
        print('[WARN] 이미지가 없어 preview 경로가 비어 있습니다.')

    # 마크다운 생성
    front_matter = build_front_matter(title, category, date_str, thumb_web)
    body = '\n'.join(img_tags)
    if img_tags:
        body += '\n\n'
    if content:
        body += content.strip() + '\n'

    folder = CATEGORIES[category]['folder']
    posts_dir = os.path.join(repo_root, '_posts', folder)
    os.makedirs(posts_dir, exist_ok=True)

    filename = f'{date_str}-{slug}.markdown'
    filepath = os.path.join(posts_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(front_matter + '\n' + body)

    print(f'  포스트 생성: _posts/{folder}/{filename}')

    # Git
    run(['git', 'add', '-A'], cwd=repo_root)
    status = run(['git', 'status', '--porcelain'], cwd=repo_root)
    if not status:
        print('[INFO] 변경사항 없음 — commit 생략')
        return filepath

    run(['git', 'commit', '-m', f'post: {title}'], cwd=repo_root)
    print(f'  커밋: post: {title}')

    if not no_push:
        run(['git', 'push'], cwd=repo_root)
        print('  푸시 완료!')

    print(f'\n✓ 업로드 성공!')
    print(f'  카테고리 : {category}')
    print(f'  파일     : _posts/{folder}/{filename}')
    print(f'  썸네일   : {thumb_web}')
    print(f'  이미지   : {len(img_tags)}장')

    return filepath


# ── CLI 엔트리포인트 ──────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Jekyll 블로그 포스트 자동 생성')
    parser.add_argument('--title',         required=True, help='포스트 제목')
    parser.add_argument('--category',      required=True, choices=CATEGORIES.keys())
    parser.add_argument('--slug',          required=True, help='URL 슬러그 (영문)')
    parser.add_argument('--files',         nargs='+', default=[],
                        help='파일명 목록 (thumb 포함된 건 썸네일, 숫자 끝은 본문 이미지)')
    parser.add_argument('--downloads-dir', default=DOWNLOADS_DIR,
                        help=f'이미지 검색 폴더 (기본: {DOWNLOADS_DIR})')
    parser.add_argument('--content',       default='', help='본문 내용')
    parser.add_argument('--date',          help='날짜 YYYY-MM-DD (기본: 오늘)')
    parser.add_argument('--no-push',       action='store_true', help='push 생략')
    args = parser.parse_args()

    date = datetime.strptime(args.date, '%Y-%m-%d') if args.date else datetime.now()

    create_post(
        title=args.title,
        category=args.category,
        slug=args.slug,
        filenames=args.files,
        content=args.content,
        date=date,
        downloads_dir=os.path.expanduser(args.downloads_dir),
        no_push=args.no_push,
    )


if __name__ == '__main__':
    main()
