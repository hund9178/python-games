# -*- mode: python ; coding: utf-8 -*-
"""打包配置：字体和 uifont.py 一起带上，缺字体文件时也不会构建失败。"""
import os

# 随包携带的文件。字体文件不存在就跳过，避免换台电脑构建直接报错。
datas = []
for src, dst in (
    ('fonts/NotoSansSC.ttf', 'fonts'),
    ('fonts/NotoSansSC-Bold.ttf', 'fonts'),
    ('fonts/LICENSE.txt', 'fonts'),
    ('msyh.ttc', '.'),
    ('msyhbd.ttc', '.'),
):
    if os.path.exists(src):
        datas.append((src, dst))

hiddenimports = ['uifont', 'version']

a = Analysis(
    ['snake.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='snake',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
