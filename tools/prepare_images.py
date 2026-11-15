"""images/ 폴더의 원본 그림을 게임용으로 가볍게 만듭니다 → images/web/
새 그림을 올린 뒤 실행:  python3 tools/prepare_images.py

1) 그림 한 장 (예: hero_knight.png)
   투명한 여백을 자르고, 높이를 MAX_H 픽셀로 줄여서 images/web/hero_knight.png 로 저장

2) 동작 시트 (예: hero_knight_sheet.png) — 4칸 × 3줄, 12자세
   1줄: 서 있기, 숨쉬기, 맞음, 스킬 / 2줄: 걷기 4장 / 3줄: 공격 4장
   칸마다 캐릭터를 잘라서 모든 자세를 같은 비율로 맞추고, 발 위치를 칸 아래 가운데에 맞춰
   images/web/hero_knight_anim.png (같은 크기 칸 4×3) 로 저장
"""
import glob, json, os
from PIL import Image

MAX_H = 384                 # 그림 한 장 높이
CELL_W, CELL_H = 300, 330   # 동작 시트 한 칸 크기
FIG_H = 300                 # 시트 안 캐릭터 기준 키 (서 있기·걷기 자세의 평균 키)
COLS, ROWS = 4, 3
SRC, DST = 'images', 'images/web'
os.makedirs(DST, exist_ok=True)

def alpha_bbox(im, thr=40):
    return im.split()[-1].point(lambda v: 255 if v > thr else 0).getbbox()

def feet_x(im, bb):
    """발 위치: 캐릭터 아래쪽 12% 줄의 가로 가운데"""
    a = im.split()[-1].load(); x0, y0, x1, y1 = bb; band = max(2, (y1 - y0) // 8); xs = []
    for y in range(y1 - band, y1):
        for x in range(x0, x1, 2):
            if a[x, y] > 40: xs.append(x)
    return sum(xs) / len(xs) if xs else (x0 + x1) / 2

def single(path, name):
    im = Image.open(path).convert('RGBA')
    bb = alpha_bbox(im)
    if bb:
        pad = 4
        im = im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)))
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    im.save(f'{DST}/{name}.png', optimize=True)
    return f'{im.width}x{im.height}'

def sheet(path, name):
    src = Image.open(path).convert('RGBA')
    cw, ch = src.width / COLS, src.height / ROWS
    frames = []
    for r in range(ROWS):
        for c in range(COLS):
            cell = src.crop((round(c * cw), round(r * ch), round((c + 1) * cw), round((r + 1) * ch)))
            bb = alpha_bbox(cell)
            frames.append((cell, bb))
    # 비율 기준: 서 있기 2장 + 걷기 4장의 키 중간값 → 모든 자세에 같은 비율 적용 (웅크린 자세는 작게 유지)
    hs = sorted(bb[3] - bb[1] for i, (cell, bb) in enumerate(frames) if bb and (i < 2 or 4 <= i < 8))
    ref = hs[len(hs) // 2] if hs else ch
    scale = FIG_H / ref
    out = Image.new('RGBA', (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    for i, (cell, bb) in enumerate(frames):
        if not bb: continue
        fx = feet_x(cell, bb)
        fig = cell.crop(bb)
        w, h = max(1, round(fig.width * scale)), max(1, round(fig.height * scale))
        fig = fig.resize((w, h), Image.LANCZOS)
        ox = (i % COLS) * CELL_W + CELL_W // 2 - round((fx - bb[0]) * scale)
        oy = (i // COLS) * CELL_H + CELL_H - 8 - h
        # 칸 밖으로 넘치는 부분은 잘림 (무기를 크게 휘두르는 자세 등)
        cx0, cy0 = (i % COLS) * CELL_W, (i // COLS) * CELL_H
        part = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
        part.alpha_composite(fig, (ox - cx0, oy - cy0)) if 0 <= ox - cx0 and 0 <= oy - cy0 and ox - cx0 + w <= CELL_W else part.paste(fig, (ox - cx0, oy - cy0), fig)
        out.alpha_composite(part, (cx0, cy0))
    out.save(f'{DST}/{name}_anim.png', optimize=True)
    return f'{COLS}x{ROWS} 칸, 기준 키 {ref}px'

names, anims = [], []
for path in sorted(glob.glob(f'{SRC}/*.png')):
    base = os.path.splitext(os.path.basename(path))[0]
    if base.endswith('_sheet'):
        name = base[:-6]; info = sheet(path, name); anims.append(name)
    else:
        name = base; info = single(path, name); names.append(name)
    print(f'{base}: {info}')
with open(f'{DST}/list.json', 'w') as f:
    json.dump({'sprites': names, 'anims': anims}, f, ensure_ascii=False)
