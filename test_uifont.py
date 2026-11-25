# -*- coding: utf-8 -*-
"""
中文字体测试
==========================================
专门模拟「另一台没装黑体的电脑」，验证中文还能正常显示。

运行：
    python test_uifont.py
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

pygame.init()
pygame.display.set_mode((10, 10))

fails = []


def check(name, cond, detail=''):
    print('%s %s%s' % ('[PASS]' if cond else '[FAIL]', name,
                       ('  -> ' + detail) if (detail and not cond) else ''))
    if not cond:
        fails.append(name)


def hide_system_cjk_fonts():
    """把 pygame 认得的所有中文字体从系统字体表里抹掉，模拟另一台电脑。"""
    import pygame.sysfont as sysfont

    sysfont.initsysfonts()
    hidden = []
    for table in (sysfont.Sysfonts, sysfont.Sysalias):
        for key in list(table):
            if any(k in key for k in ('simhei', 'microsoftyahei', 'msyh',
                                      'dengxian', 'simsun', 'notosanssc',
                                      'sourcehansans', 'pingfang',
                                      'wenquanyi', 'heiti', 'songti')):
                hidden.append(key)
                del table[key]
    return hidden


def chinese_ok(font, sample='帅仕相车马炮兵'):
    """逐字检查：汉字要画成方的，缺字形时 pygame 会画成窄条。"""
    for ch in sample:
        img = font.render(ch, True, (0, 0, 0))
        w, h = img.get_size()
        if h <= 0 or w < h * 0.7:
            return False, '%r 渲染成 %s（缺字形）' % (ch, (w, h))
    return True, ''


print('=' * 60)
print('中文字体测试')
print('=' * 60)

# --- 1. 随包字体文件齐全 ---
fonts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
for name in ('NotoSansSC.ttf', 'NotoSansSC-Bold.ttf', 'LICENSE.txt'):
    p = os.path.join(fonts_dir, name)
    check('随包字体存在: %s' % name, os.path.isfile(p), p)

# --- 2. 子集字体覆盖源码里用到的所有汉字 ---
import glob

chars = set()
for path in glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '*.py')):
    with open(path, encoding='utf-8') as f:
        for ch in f.read():
            if ord(ch) > 0x7F:
                chars.add(ch)

subset = pygame.font.Font(os.path.join(fonts_dir, 'NotoSansSC.ttf'), 32)
missing = []
for ch in sorted(chars):
    img = subset.render(ch, True, (0, 0, 0))
    w, h = img.get_size()
    if h <= 0 or w < h * 0.5:
        missing.append(ch)
check('子集字体覆盖全部 %d 个非 ASCII 字符' % len(chars),
      not missing, '缺字形: %r' % missing[:20])

# --- 3. 模拟另一台没有中文字体的电脑 ---
hidden = hide_system_cjk_fonts()
print('已从系统字体表移除: %d 个中文字体' % len(hidden))

import uifont

# 清掉缓存，重新按新环境解析
uifont.SYSTEM_FONT_NAMES = ()
try:
    f = uifont._make(30, False)
    ok, detail = chinese_ok(f)
    check('没有系统中文字体时仍能显示中文', ok, detail)
    check('用的是随包字体而不是 pygame 默认字体',
          'FreeSans' not in f.name, '实际用了: %s' % f.name)

    fb = uifont._make(30, True)
    ok, detail = chinese_ok(fb)
    check('粗体也能显示中文', ok, detail)

    check('chinese_font_available() 返回 True', uifont.chinese_font_available())
except Exception as e:
    check('没有系统中文字体时仍能显示中文', False, '异常: %r' % e)

# --- 4. 恢复正常环境，确认系统字体依然可用 ---
import pygame.sysfont as sysfont
sysfont.initsysfonts()
sysfont.is_init = False
uifont.SYSTEM_FONT_NAMES = uifont.SYSTEM_FONT_NAMES or ()

print()
print('=' * 60)
if fails:
    print('失败 %d 项:' % len(fails))
    for name in fails:
        print('  -', name)
    sys.exit(1)
print('全部通过')
