# -*- coding: utf-8 -*-
"""版本号。所有游戏共用一个来源，改这里就行。"""

VERSION = '1.0.0'

# 窗口标题里显示的格式
def caption(title):
    return '%s v%s' % (title, VERSION)
