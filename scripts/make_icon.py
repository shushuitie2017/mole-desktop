# -*- coding: utf-8 -*-
"""生成 assets/icon.ico —— Mole 配色 (橙 #f0883e on 暗底) 的圆角图标。"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "icon.ico"
OUT.parent.mkdir(parents=True, exist_ok=True)

SIZE = 256
BG = (13, 17, 23, 255)        # #0d1117
ACCENT = (240, 136, 62, 255)  # #f0883e
ACCENT2 = (219, 109, 40, 255) # #db6d28


def rounded(img, radius):
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, img.size[0], img.size[1]], radius=radius, fill=255)
    img.putalpha(mask)
    return img


def make():
    im = Image.new("RGBA", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(im)
    # 外环
    d.ellipse([40, 40, 216, 216], outline=ACCENT, width=14)
    # 中央字母 M
    try:
        font = ImageFont.truetype("arialbd.ttf", 130)
    except Exception:
        font = ImageFont.load_default()
    text = "M"
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((SIZE - w) / 2 - bbox[0], (SIZE - h) / 2 - bbox[1]), text,
           font=font, fill=ACCENT)
    # 底部强调点
    d.ellipse([118, 188, 138, 208], fill=ACCENT2)

    im = rounded(im, 52)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    im.save(OUT, format="ICO", sizes=sizes)
    print("saved", OUT)


if __name__ == "__main__":
    make()
