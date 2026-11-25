# -*- coding: utf-8 -*-
"""
从 Noto Sans SC 切出游戏专用的子集字体。

为什么要自己切：
  微软雅黑 msyh.ttc 是微软的版权字体，不能跟着程序一起分发给别人。
  Noto Sans SC 是 SIL OFL 开源协议，可以随便打包分发。
  完整字体 8.4MB，切完只有几十 KB。

用法：
    python tools/build_font.py
"""
from __future__ import annotations

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, 'fonts')

# 常规体和粗体分开找
REGULAR_CANDIDATES = [
    r'C:\Windows\Fonts\Noto Sans SC (TrueType).otf',
    r'C:\Windows\Fonts\NotoSansSC-Regular.ttf',
    r'C:\Windows\Fonts\NotoSansSC-VF.ttf',
    os.path.join(OUT_DIR, 'NotoSansSC-Regular.ttf'),
]
BOLD_CANDIDATES = [
    r'C:\Windows\Fonts\Noto Sans SC Bold (TrueType).otf',
    os.path.join(OUT_DIR, 'NotoSansSC-Bold.ttf'),
]


def collect_chars():
    """扫描源码里用到的所有非 ASCII 字符。"""
    chars = set()
    for name in os.listdir(ROOT):
        if not name.endswith('.py'):
            continue
        path = os.path.join(ROOT, name)
        with open(path, encoding='utf-8') as f:
            for ch in f.read():
                if ord(ch) > 0x7F:
                    chars.add(ch)

    # 界面上会动态出现的字（棋谱、结算提示、棋局存档里的中文）
    extra = (
        '红方黑方先手后手轮到你走轮到电脑走将军将死和棋胜利失败平局'
        '新局悔棋提示难度对战音效全屏保存读取上下翻页退出继续暂停'
        '帅仕相车马炮兵将士象卒一二三四五六七八九十进退平捉'
        '双方走子后第回合步着法记录棋谱当前状态选中你的棋子已无法'
        '请选择简单普通困难单人双人本地开始结束重新再来一盘确定取消'
        '是好第步轮到电脑你走想悔棋请确认覆盖读取失败文件已满'
        ' abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        '0123456789.,:;!?()[]{}<>+-*/=%$#@&_~^|`\\\'"'
        '，。、；：？！（）【】《》“”‘’—…·×÷°±→←↑↓▲▼❌'
    )
    for ch in extra:
        if ord(ch) > 0x7F:
            chars.add(ch)
    return chars


def find_source(candidates, label):
    for p in candidates:
        if os.path.isfile(p):
            return p
    raise SystemExit(
        f'找不到 Noto Sans SC {label}源字体。\n'
        '请从 https://fonts.google.com/noto/specimen/Noto+Sans+SC 下载 '
        'NotoSansSC-Regular.ttf 和 NotoSansSC-Bold.ttf，\n'
        f'放到 {OUT_DIR} 目录下再运行本脚本。')


def subset_one(src, dst, text):
    from fontTools import subset
    from fontTools.ttLib import TTFont

    font = TTFont(src, fontNumber=0)
    options = subset.Options()
    options.drop_tables += ['DSIG']
    options.layout_features = ['*']
    options.name_IDs = ['*']
    options.notdef_outline = True
    options.recalc_bounds = True
    options.glyph_names = False

    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.save(dst)
    return os.path.getsize(dst)


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    chars = collect_chars()
    text = ''.join(sorted(chars))
    print(f'字符数: {len(chars)}')

    regular = find_source(REGULAR_CANDIDATES, '常规')
    bold = find_source(BOLD_CANDIDATES, '粗体')
    print(f'常规体源: {regular}')
    print(f'粗体源:   {bold}')

    size = subset_one(regular, os.path.join(OUT_DIR, 'NotoSansSC.ttf'), text)
    print(f'  NotoSansSC.ttf       {size / 1024:.1f} KB')
    size = subset_one(bold, os.path.join(OUT_DIR, 'NotoSansSC-Bold.ttf'), text)
    print(f'  NotoSansSC-Bold.ttf  {size / 1024:.1f} KB')

    license_text = (
        'Noto Sans SC 字体子集\n'
        '=====================\n\n'
        '本目录下的 NotoSansSC.ttf / NotoSansSC-Bold.ttf 是从 Google Noto Sans SC\n'
        '裁剪而来，只保留游戏用到的字符。\n\n'
        '原字体: Noto Sans SC (Google)\n'
        '许可证: SIL Open Font License 1.1 (OFL-1.1)\n'
        '         https://scripts.sil.org/OFL\n\n'
        'OFL 1.1 允许自由使用、修改、嵌入和再分发该字体，\n'
        '要求保留本许可证和版权声明，且不得单独售卖字体本身。\n'
    )
    with open(os.path.join(OUT_DIR, 'LICENSE.txt'), 'w', encoding='utf-8') as f:
        f.write(license_text)
    print('  LICENSE.txt')


if __name__ == '__main__':
    build()
