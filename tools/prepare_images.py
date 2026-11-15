"""images/ 폴더의 원본 그림을 게임용으로 가볍게 만듭니다 → images/web/
- 투명한 여백을 잘라내고, 높이를 MAX_H 픽셀로 줄이고, PNG를 압축합니다.
- 새 그림을 올린 뒤 실행:  python3 tools/prepare_images.py
"""
import glob, json, os
from PIL import Image

MAX_H = 384
SRC, DST = 'images', 'images/web'
os.makedirs(DST, exist_ok=True)
names = []
for path in sorted(glob.glob(f'{SRC}/*.png')):
    name = os.path.splitext(os.path.basename(path))[0]
    im = Image.open(path).convert('RGBA')
    a = im.split()[-1].point(lambda v: 255 if v > 40 else 0)
    bb = a.getbbox()
    if bb:
        pad = 4
        bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(im.width, bb[2] + pad), min(im.height, bb[3] + pad))
        im = im.crop(bb)
    if im.height > MAX_H:
        im = im.resize((round(im.width * MAX_H / im.height), MAX_H), Image.LANCZOS)
    out = f'{DST}/{name}.png'
    im.save(out, optimize=True)
    names.append(name)
    print(f'{name}: {im.width}x{im.height}, {os.path.getsize(out) // 1024}KB')
with open(f'{DST}/list.json', 'w') as f:
    json.dump(names, f)
