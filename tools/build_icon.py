# -*- coding: utf-8 -*-
"""生成 xiangqi.ico：给打包出来的 exe 一个自己的图标。

用法：
    python tools/build_icon.py

画的是一个红边的「帅」棋子，和游戏里显示的图标一致。
ICO 文件用最老的那种 BMP 格式手写，Windows 98 到现在都认。
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uifont import Fonts  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'xiangqi.ico')

FACE = (246, 231, 200)
RING = (172, 38, 40)
TEXT = (172, 28, 30)


def draw_icon(size, fonts):
    """画一个 size×size 的棋子，返回 RGBA 像素。"""
    import pygame
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    radius = int(size * 0.47)

    # 棋子外圈
    pygame.draw.circle(surf, RING, center, radius)
    # 棋子内面
    pygame.draw.circle(surf, FACE, center, max(1, int(radius * 0.88)))

    # 中间的「帅」字
    fsize = max(9, int(size * 0.62))
    font = fonts.get(fsize, bold=True)
    img = font.render('帅', True, TEXT)
    if img.get_width() > size * 0.62:
        scale = (size * 0.62) / img.get_width()
        new_size = max(8, int(fsize * scale))
        font = fonts.get(new_size, bold=True)
        img = font.render('帅', True, TEXT)
    surf.blit(img, img.get_rect(center=center))
    return surf


def make_dib(surf):
    """把 pygame 表面转成 ICO 里用的 BMP 数据（BITMAPINFOHEADER + 像素 + 掩码）。"""
    import pygame
    w, h = surf.get_size()
    rgba = pygame.image.tobytes(surf, 'RGBA')

    header = struct.pack('<IiiHHIIiiII', 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)

    # 像素：转成 BGRA，并且上下颠倒（ICO 的 BMP 从下往上存）
    xor = bytearray()
    row_bytes = w * 4
    for y in range(h - 1, -1, -1):
        row = rgba[y * row_bytes:(y + 1) * row_bytes]
        for x in range(w):
            r, g, b, a = row[x * 4:x * 4 + 4]
            xor += bytes((b, g, r, a))

    # 透明掩码：32 位图标用 alpha 就行，这里按规矩补一段全 0 的
    mask_row = ((w + 31) // 32) * 4
    mask = bytes(mask_row * h)

    return header + bytes(xor) + mask


def write_ico(path, images):
    """images: [(size, dib_bytes), ...]"""
    count = len(images)
    offset = 6 + 16 * count
    out = struct.pack('<HHH', 0, 1, count)
    body = b''
    for size, dib in images:
        w = 0 if size >= 256 else size
        out += struct.pack('<BBBBHHII', w, w, 0, 0, 1, 32, len(dib), offset)
        body += dib
        offset += len(dib)
    out += body
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)


def main():
    import pygame
    pygame.init()
    fonts = Fonts()
    images = []
    for size in SIZES:
        surf = draw_icon(size, fonts)
        images.append((size, make_dib(surf)))
    total = write_ico(OUT, images)
    print('已生成 %s（%d 个尺寸，%d 字节）' % (OUT, len(images), total))


if __name__ == '__main__':
    main()
