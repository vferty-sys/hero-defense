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
from collections import deque
import numpy as np
from PIL import Image

MAX_H = 384                 # 그림 한 장 높이
CELL_W, CELL_H = 300, 330   # 동작 시트 한 칸 크기
FIG_H = 300                 # 시트 안 캐릭터 기준 키 (서 있기·걷기 자세의 평균 키)
COLS, ROWS = 4, 3
SRC, DST = 'images', 'images/web'
os.makedirs(DST, exist_ok=True)

def remove_fake_background(im):
    """AI가 '투명 배경' 대신 회색·흰색 바둑판 무늬(또는 단색)를 그려 넣은 경우 그 배경을 지움.
    - 테두리에서 이어진, 배경 색 범위의 회색 영역을 투명하게
    - 캐릭터에 둘러싸인 회색 영역은 바둑판 칸 크기(약 23px)로 두 색이 번갈아 나올 때만 지움
      (회색 갑옷처럼 우연히 비슷한 색은 남김)"""
    a = np.array(im.convert('RGBA')).astype(np.int16)
    if a[0, 0, 3] < 250 and a[-1, -1, 3] < 250:
        return im                                                     # 이미 진짜 투명 배경
    rgb = a[:, :, :3]; H, W = rgb.shape[:2]
    bright = rgb.mean(axis=2); sat = rgb.max(axis=2) - rgb.min(axis=2)
    border = np.concatenate([bright[0], bright[-1], bright[:, 0], bright[:, -1]])
    lo, hi = np.percentile(border, 10), np.percentile(border, 90)    # 바둑판 두 색 (어두운 칸 · 밝은 칸)
    inRange = (bright >= lo - 14) & (bright <= hi + 14)
    M = (sat <= 95) & inRange                                         # 빛 효과에 물든 바둑판도 포함 (테두리와 이어진 경우만 지움)
    Mgray = (sat <= 18) & inRange                                     # 둘러싸인 영역은 순수 회색만
    light = bright > (lo + hi) / 2
    row = light[1]; edges = [x for x in range(1, W) if row[x] != row[x - 1]]
    gaps = [q - p2 for p2, q in zip(edges, edges[1:]) if q - p2 > 3]
    cs = float(np.median(gaps)) if gaps else 0                        # 칸 크기
    seen = np.zeros((H, W), bool); bg = np.zeros((H, W), bool)
    for sy in range(H):
        for sx in np.nonzero(M[sy] & ~seen[sy])[0]:
            if seen[sy, sx]: continue
            q = deque([(sy, sx)]); seen[sy, sx] = True; pts = []; touch = False
            while q:
                y, x = q.popleft(); pts.append((y, x))
                if y == 0 or x == 0 or y == H - 1 or x == W - 1: touch = True
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < H and 0 <= nx < W and M[ny, nx] and not seen[ny, nx] and (Mgray[ny, nx] or Mgray[y, x] or touch):
                        seen[ny, nx] = True; q.append((ny, nx))
            ok = touch
            if not ok and len(pts) >= 150 and cs >= 6:               # 둘러싸인 영역: 바둑판 무늬인지 확인
                ys = np.array([p3[0] for p3 in pts]); xs = np.array([p3[1] for p3 in pts])
                if not Mgray[ys, xs].mean() > 0.85: continue
                lf = light[ys, xs].mean()
                bv = bright[ys, xs]; twoTone = ((np.abs(bv - lo) <= 10) | (np.abs(bv - hi) <= 10)).mean()
                runs = []
                for y in np.unique(ys)[::3]:
                    rx = np.sort(xs[ys == y]); lv = light[y, rx]; start = 0
                    for i in range(1, len(rx) + 1):
                        if i == len(rx) or rx[i] != rx[i - 1] + 1 or lv[i] != lv[i - 1]:
                            if i - start >= 3: runs.append(i - start)
                            start = i
                med = float(np.median(runs)) if runs else 0
                ok = 0.12 <= lf <= 0.88 and (cs * 0.55 <= med <= cs * 1.3 or (twoTone >= 0.8 and med <= cs * 1.3))
            if ok:
                for y, x in pts: bg[y, x] = True
    # 가장자리 정리: 배경 바로 옆의 밝고 회색인 픽셀(번짐)도 지움
    for _ in range(2):
        nb = np.zeros_like(bg); nb[1:] |= bg[:-1]; nb[:-1] |= bg[1:]; nb[:, 1:] |= bg[:, :-1]; nb[:, :-1] |= bg[:, 1:]
        bg |= nb & (sat <= 24) & (bright >= lo - 25)
    a[:, :, 3] = np.where(bg, 0, a[:, :, 3])
    return Image.fromarray(a.astype(np.uint8), 'RGBA')

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
    im = remove_fake_background(Image.open(path).convert('RGBA'))
    bb = alpha_bbox(im)
    if bb:
        pad = 4
        im = im.crop((max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad)))
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    im.save(f'{DST}/{name}.png', optimize=True)
    return f'{im.width}x{im.height}'

def sheet(path, name):
    src = remove_fake_background(Image.open(path).convert('RGBA'))
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

for old in glob.glob(f'{DST}/*.png'):          # 예전에 만든 게임용 그림은 지우고 새로 만듦 (원본을 지우면 게임용도 사라지게)
    os.remove(old)
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
