# -*- coding: utf-8 -*-
"""
中文字体解析
==========================================
pygame 自带的 SysFont 在找不到字体时不会报错，而是悄悄用英文字体顶替，
导致中文全变成方框。这里统一按可靠顺序找字体，并逐个验证「真能画出汉字」。

    from uifont import Fonts
    fonts = Fonts()
    img = fonts.get(30, bold=True).render('帅', True, (0, 0, 0))
"""

from __future__ import annotations

import os
import sys

import pygame

# 系统里常见的中文字体名，作为找不到随包字体时的备选。
SYSTEM_FONT_NAMES = (
    'microsoftyaheiui', 'microsoftyahei', 'simhei', 'dengxian', 'simsun',
    'notosanssc', 'sourcehansanssc', 'pingfangsc', 'heitisc', 'songtisc',
    'wenquanyizenhei', 'notosanscjk', 'arialunicodems',
)

# 随程序携带的字体文件。放在 fonts/ 子目录里，打包后原样带过去。
# Noto Sans SC 是 SIL OFL 协议，可以自由分发；微软雅黑不能，所以不进仓库。
BUNDLED_FONT_FILES = (
    'fonts/NotoSansSC.ttf',
    'fonts/NotoSansSC-Bold.ttf',
    'fonts/msyh.ttc',
    'fonts/msyhbd.ttc',
    'NotoSansSC.ttf',
    'NotoSansSC-Bold.ttf',
    'msyh.ttc',
    'msyhbd.ttc',
)

# 粗体优先用这些文件
BOLD_FIRST = (
    'fonts/NotoSansSC-Bold.ttf',
    'fonts/msyhbd.ttc',
    'NotoSansSC-Bold.ttf',
    'msyhbd.ttc',
)

# 用来验证字体的汉字。挑的是最常见的几个，任何中文字体都必须有。
PROBE_CHARS = '帅仕相车马炮兵将士象卒'


def _app_dirs():
    """程序可能存放字体的目录，按优先级排好。"""
    dirs = []
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，附带的数据文件解压在 _MEIPASS
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            dirs.append(meipass)
        dirs.append(os.path.dirname(os.path.abspath(sys.executable)))
    here = os.path.dirname(os.path.abspath(__file__))
    dirs.append(here)
    # uifont.py 可能在 fonts/ 的上一级，所以父目录也要找
    dirs.append(os.path.dirname(here))

    seen = set()
    out = []
    for d in dirs:
        if d and d not in seen and os.path.isdir(d):
            seen.add(d)
            out.append(d)
    return out


def _bundled_path(name):
    """在程序目录里找随包字体，返回完整路径或 None。"""
    rel = name.replace('/', os.sep)
    for d in _app_dirs():
        p = os.path.join(d, rel)
        if os.path.isfile(p):
            return p
    return None


def _renders_chinese(font):
    """这个字体真的能画出汉字吗？空方框不算。"""
    try:
        img = font.render(PROBE_CHARS, True, (0, 0, 0))
    except Exception:
        return False
    if img.get_width() <= 0 or img.get_height() <= 0:
        return False

    # 逐字渲染：真正的汉字是方形的，宽度接近高度；
    # 缺字形时 pygame 会画成窄条，宽度明显小于高度。
    for ch in PROBE_CHARS:
        try:
            one = font.render(ch, True, (0, 0, 0))
        except Exception:
            return False
        w, h = one.get_size()
        if h <= 0 or w < h * 0.7:
            return False
    return True


def _load_file(path, size, bold):
    """从字体文件加载，失败返回 None。"""
    try:
        f = pygame.font.Font(path, size)
    except Exception:
        return None
    if bold:
        try:
            f.set_bold(True)
        except Exception:
            pass
    return f


def _make(size, bold):
    """按可靠顺序找一个真能显示中文的字体。"""
    # 一、随程序携带的字体。放在最前面，保证在任何电脑上显示效果一致。
    names = list(BOLD_FIRST) + list(BUNDLED_FONT_FILES) if bold \
        else list(BUNDLED_FONT_FILES)
    for name in names:
        path = _bundled_path(name)
        if not path:
            continue
        f = _load_file(path, size, bold)
        if f is not None and _renders_chinese(f):
            return f

    # 二、系统里装的中文字体
    for name in SYSTEM_FONT_NAMES:
        path = None
        for bold_arg in (bold, False):
            try:
                path = pygame.font.match_font(name, bold=bold_arg)
            except Exception:
                path = None
            if path:
                break
        if not path:
            continue
        f = _load_file(path, size, bold)
        if f is not None and _renders_chinese(f):
            return f

    # 三、系统字体目录里直接按文件名找
    win_fonts = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
    for d in (win_fonts, '/usr/share/fonts', '/Library/Fonts'):
        if not d or not os.path.isdir(d):
            continue
        for fname in ('msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'simsun.ttc',
                      'NotoSansSC-Regular.otf', 'Noto Sans SC (TrueType).otf'):
            p = os.path.join(d, fname)
            if not os.path.isfile(p):
                continue
            f = _load_file(p, size, bold)
            if f is not None and _renders_chinese(f):
                return f

    # 四、实在找不到：退回 pygame 默认字体，交给上层显示提示
    return pygame.font.Font(None, size)


def chinese_font_available():
    """当前有没有能用的中文字体？"""
    try:
        f = _make(24, False)
    except Exception:
        return False
    return _renders_chinese(f)


def font_source():
    """当前用的是哪个字体文件？排查问题时用。"""
    for name in BUNDLED_FONT_FILES:
        p = _bundled_path(name)
        if p:
            return p
    for name in SYSTEM_FONT_NAMES:
        try:
            p = pygame.font.match_font(name)
        except Exception:
            p = None
        if p:
            return p
    return None


class Fonts:
    """按字号缓存字体的小工具，用法跟原来的 Fonts 一致。"""

    def __init__(self):
        self.cache = {}

    def get(self, size, bold=False):
        key = (size, bold)
        if key not in self.cache:
            self.cache[key] = _make(size, bold)
        return self.cache[key]
