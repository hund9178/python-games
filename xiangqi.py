# -*- coding: utf-8 -*-
"""
象棋 · 简易版（棋谱 + 存档）
==========================================
界面清爽直观：整块棋盘占满画面，上方一行大字提示当前该谁走，
棋盘下方是能上下翻的棋谱记录，底部两排大按钮。
默认全屏显示，布局随屏幕分辨率自动放大。

    python xiangqi.py

操作
    左键点自己的棋子（会出现黄色圆圈），再点目标位置落子
    右键取消选择
    大按钮：新 局 / 悔 棋 / 提 示 / 难度 / 对战 / 音效 / 全屏
    棋谱面板右上角：保存 / 读取 / 上下翻页
    快捷键  R 新局   U 悔棋   H 提示   S 保存   L 读取
              M 切换模式   F 全屏   Esc 退出
"""

from __future__ import annotations

import json
import math
import os
import sys
import threading
import time
from array import array

import pygame

from xiangqi_rules import (RED, BLACK, GameState, legal_moves, best_move,
                           move_notation, game_result, CHARS)
from uifont import Fonts, chinese_font_available, font_source

# ==========================================================================
# 布局与配色
# ==========================================================================
WINDOW_W, WINDOW_H = 660, 1000     # 窗口模式下的窗口大小

C_WINDOW = (228, 222, 208)
C_CARD = (247, 243, 234)
C_CARD_LINE = (208, 199, 182)
C_BOARD = (222, 186, 132)
C_BOARD_EDGE = (150, 112, 68)
C_BOARD_DARK = (205, 167, 116)
C_LINE = (78, 52, 30)
C_RIVER = (146, 98, 50)
C_PIECE_FACE = (246, 231, 200)
C_EDGE_R = (172, 38, 40)
C_EDGE_B = (44, 44, 52)
C_TEXT_R = (172, 28, 30)
C_TEXT_B = (30, 30, 38)
C_HILITE = (255, 192, 32)
C_LAST = (46, 138, 208)
C_CHECK = (222, 48, 38)
C_BANNER = (252, 248, 238)
C_BANNER_LINE = (198, 186, 166)
C_TEXT_DARK = (46, 40, 34)
C_TEXT_DIM = (116, 108, 96)
C_BTN = (58, 98, 136)
C_BTN_HOVER = (76, 126, 168)
C_BTN2 = (104, 114, 80)
C_BTN2_HOVER = (126, 138, 100)
C_BTN_LINE = (36, 40, 46)
C_BUTTON_TEXT = (255, 255, 255)
C_REC_BG = (250, 247, 239)
C_REC_LINE = (206, 196, 178)
C_REC_BTN = (128, 116, 92)
C_REC_BTN_HOVER = (150, 137, 110)
C_REC_SCROLL = (186, 176, 156)

# 棋盘上的“炮位/兵位”标记点（列, 行）
MARKERS = [(1, 2), (7, 2), (1, 7), (7, 7),
           (0, 3), (2, 3), (4, 3), (6, 3), (8, 3),
           (0, 6), (2, 6), (4, 6), (6, 6), (8, 6)]


# ==========================================================================
# 存档目录
# ==========================================================================
def app_root():
    """程序所在的大目录：源码运行时是「乐乐」，打包后是 exe 上两级。"""
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.dirname(exe_dir))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def save_folder():
    """棋局存档文件夹，优先放在「乐乐」目录下的 棋局存档 文件夹。"""
    candidates = [os.path.join(app_root(), '棋局存档')]
    if getattr(sys, 'frozen', False):
        candidates.append(os.path.join(
            os.path.dirname(os.path.abspath(sys.executable)), '棋局存档'))
    candidates.append(os.path.join(os.path.expanduser('~'), '棋局存档'))
    for d in candidates:
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, '.write_test')
            with open(probe, 'w', encoding='utf-8') as f:
                f.write('ok')
            os.remove(probe)
            return d
        except Exception:
            continue
    return None


# ==========================================================================
# 布局
# ==========================================================================
class Layout:
    """按画布尺寸算出的全部排版数值，窗口/全屏通用。"""

    def __init__(self, w, h):
        self.w, self.h = w, h
        big = h >= 900
        pad = 16
        banner_h = 92 if big else 80
        tip_h = 30 if big else 24
        btn_h1 = 64 if big else 58
        btn_h2 = 56 if big else 50
        btn_gap = 12
        gap = 16

        # 棋谱面板先按比例留位置
        rec_h = int(min(150, max(96, h * 0.13)))

        # 除棋盘和棋谱面板外必须占用的高度
        fixed = (pad + banner_h + gap + gap + gap + btn_h1 + btn_gap
                 + btn_h2 + gap // 2 + tip_h + pad)
        cell = (h - fixed - rec_h) // 10
        cell_w = (w - 2 * pad) // 9
        cell = max(30, min(cell, cell_w))

        self.cell = cell
        self.margin = max(8, cell // 2)
        self.frame_w = 8 * cell + 2 * self.margin
        self.frame_h = 9 * cell + 2 * self.margin
        self.frame_x = (w - self.frame_w) // 2
        self.frame_y = pad + banner_h + gap
        self.board_x0 = self.frame_x + self.margin
        self.board_y0 = self.frame_y + self.margin
        self.piece_r = int(cell * 0.44)

        self.banner = pygame.Rect(self.frame_x, pad, self.frame_w, banner_h)
        self.banner_h = banner_h

        # 棋谱面板：紧贴棋盘下方
        self.rec = pygame.Rect(self.frame_x, self.frame_y + self.frame_h + gap,
                               self.frame_w, rec_h)
        self.row1_y = self.rec.bottom + gap
        self.row2_y = self.row1_y + btn_h1 + btn_gap
        self.tip_y = self.row2_y + btn_h2 + gap // 2
        self.btn_gap = btn_gap
        self.btn_h1 = btn_h1
        self.btn_h2 = btn_h2
        # 按钮排比棋盘略宽一点，保证字大、点得准
        self.btn_row_w = int(max(self.frame_w, min(w - 2 * pad, 620)))
        self.btn_x = (w - self.btn_row_w) // 2
        self.btn_w = (self.btn_row_w - 2 * btn_gap) // 3
        self.btn_w4 = (self.btn_row_w - 3 * btn_gap) // 4

        # 棋谱面板里剩余的高度补给面板本身
        rest = h - (fixed + self.frame_h)
        self.rec.height = int(max(56, min(190, rest)))
        self.row1_y = self.rec.bottom + gap
        self.row2_y = self.row1_y + btn_h1 + btn_gap
        self.tip_y = self.row2_y + btn_h2 + gap // 2

        # 字号随格子大小缩放
        self.f_piece = max(22, int(cell * 0.52))
        self.f_river = max(20, int(cell * 0.48))
        self.f_turn = max(28, int(banner_h * 0.40))
        self.f_sub = max(20, int(banner_h * 0.26))
        self.f_btn = max(20, int(btn_h1 * 0.42))
        self.f_btn2 = max(18, int(btn_h2 * 0.42))
        self.f_tip = max(16, min(24, int(h * 0.024)))

        # 棋谱文字
        self.f_rec = max(17, int(cell * 0.40))
        self.f_rec_head = max(18, int(self.f_rec * 1.02))
        self.rec_head_h = int(self.f_rec_head * 1.30) + 6
        self.rec_row_h = int(self.f_rec * 1.34)

        # 宽屏时给整列加一块卡片底衬，避免画面两边空荡荡
        self.wide = (w / float(max(1, h))) >= 1.25
        self.card = pygame.Rect(0, 0, 0, 0)
        if self.wide:
            cw = max(self.frame_w + 56, self.btn_row_w + 28)
            ch = (self.tip_y + 20) - (pad - 14)
            self.card = pygame.Rect((w - cw) // 2, pad - 14, cw, ch)

    def board_x(self, col):
        return self.board_x0 + col * self.cell

    def board_y(self, row):
        return self.board_y0 + row * self.cell


# ==========================================================================
# 字体与音效
# ==========================================================================
class Sounds:
    """程序生成的轻量音效（无音频设备时自动降级）。"""

    def __init__(self):
        self.enabled = True
        self.move = None
        self.capture = None
        self.check = None
        self.ok = False
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.move = self._tone(660, 0.06, 0.18)
            self.capture = self._tone(330, 0.10, 0.28)
            self.check = self._tone(880, 0.16, 0.30)
            self.ok = True
        except Exception:
            self.ok = False

    @staticmethod
    def _tone(freq, dur, vol):
        rate = 22050
        n = int(rate * dur)
        buf = array('h')
        for i in range(n):
            t = i / rate
            env = math.exp(-9.0 * t)
            buf.append(int(math.sin(2 * math.pi * freq * t) * env * 32767 * vol))
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, which):
        if not (self.enabled and self.ok):
            return
        snd = getattr(self, which, None)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


# ==========================================================================
# AI 后台线程
# ==========================================================================
class AIEngine:
    """在独立线程里搜索，避免卡住界面。"""

    def __init__(self, depth=4, time_limit=2.0):
        self.depth = depth
        self.time_limit = time_limit
        self._lock = threading.Lock()
        self._thread = None
        self._result = None
        self._done = False

    def start(self, state, avoid=None):
        work = state.copy()
        with self._lock:
            self._result = None
            self._done = False
        self._thread = threading.Thread(target=self._run, args=(work, avoid),
                                        daemon=True)
        self._thread.start()

    def _run(self, work, avoid=None):
        try:
            mv = best_move(work, self.depth, self.time_limit, forbid=avoid)
        except Exception:
            mv = None
        with self._lock:
            self._result = mv
            self._done = True

    def poll(self):
        with self._lock:
            if self._done:
                return self._result, True
        return None, False

    def is_running(self):
        with self._lock:
            return not self._done


# ==========================================================================
# 游戏应用
# ==========================================================================
class XiangqiApp:
    def __init__(self, fullscreen=True):
        pygame.init()
        self.fonts = Fonts()
        self.font_warning = '' if chinese_font_available() else (
            '未找到中文字体，界面文字可能显示为方框。'
            '请确认程序目录下有 fonts 文件夹。')
        self.fullscreen = fullscreen
        self.screen = None
        self.layout = None
        self.icon = self._make_icon()
        self.buttons = []
        self.rec_buttons = []
        self.apply_display()
        self.clock = pygame.time.Clock()
        self.sounds = Sounds()

        self.state = GameState()
        self.mode = 'ai'            # 'ai' 或 'pvp'
        self.human_color = RED
        self.difficulty = 2         # 1 简单 / 2 困难
        self.selected = None        # (r, c)
        self.legal_targets = []     # 可落子目标
        self.last_move = None
        self.history = []           # [(记谱, 颜色, 吃子), ...]
        self.status = ''
        self.notice = ''
        self.result = None
        self.flash = 0.0
        self.ai = None
        self.ai_pending = False
        self.ai_avoid = None        # 悔棋后不想再走的一手
        self.hint_move = None
        self.running = True

        # 棋谱面板
        self.panel_mode = 'record'  # 'record' 棋谱 / 'saves' 存档列表
        self.record_scroll = 0
        self.save_items = []
        self.save_dir = save_folder()
        self.refresh_save_list()

    # -- 显示模式 ----------------------------------------------------------
    def apply_display(self):
        if self.fullscreen:
            try:
                w, h = pygame.display.get_desktop_sizes()[0]
            except Exception:
                w, h = WINDOW_W, WINDOW_H
            self.screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption('象棋')
        if self.icon:
            pygame.display.set_icon(self.icon)
        self.set_layout(self.screen.get_size())

    def set_layout(self, size):
        self.layout = Layout(*size)
        self._build_buttons()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.apply_display()
        self.status = '已切换到全屏' if self.fullscreen else '已退出全屏'

    # -- 坐标 --------------------------------------------------------------
    def board_x(self, col):
        return self.layout.board_x(col)

    def board_y(self, row):
        return self.layout.board_y(row)

    def col_at(self, px):
        c = int(round((px - self.layout.board_x0) / self.layout.cell))
        return c if 0 <= c <= 8 else -1

    def row_at(self, py):
        r = int(round((py - self.layout.board_y0) / self.layout.cell))
        return r if 0 <= r <= 9 else -1

    # -- 初始化 ------------------------------------------------------------
    def _make_icon(self):
        try:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, (246, 231, 200), (32, 32), 30)
            pygame.draw.circle(surf, C_EDGE_R, (32, 32), 30, 3)
            f = self.fonts.get(30, bold=True)
            surf.blit(f.render('帅', True, C_TEXT_R), (0, 0))
            return surf
        except Exception:
            return None

    def _build_buttons(self):
        L = self.layout
        self.buttons = []
        row1 = [('new', '新 局'), ('undo', '悔 棋'), ('hint', '提 示')]
        for i, (bid, label) in enumerate(row1):
            x = L.btn_x + i * (L.btn_w + L.btn_gap)
            self.buttons.append({'id': bid, 'label': label,
                                 'rect': pygame.Rect(x, L.row1_y, L.btn_w, L.btn_h1),
                                 'big': True})
        row2 = [('level', ''), ('mode', ''), ('sound', ''), ('full', '')]
        for i, (bid, label) in enumerate(row2):
            x = L.btn_x + i * (L.btn_w4 + L.btn_gap)
            self.buttons.append({'id': bid, 'label': label,
                                 'rect': pygame.Rect(x, L.row2_y, L.btn_w4, L.btn_h2),
                                 'big': False})

        # 棋谱面板右上角的小按钮：保存 / 读取 / 上翻 / 下翻
        self.rec_buttons = []
        bw = int(max(46, min(62, L.rec.width * 0.125)))
        bh = max(24, L.rec_head_h - 8)
        gap = 5
        x = L.rec.right - 12 - (4 * bw + 3 * gap)
        for bid, label in (('save', '保存'), ('load', '读取'),
                           ('up', '▲'), ('down', '▼')):
            self.rec_buttons.append({'id': bid, 'label': label,
                                     'rect': pygame.Rect(x, L.rec.y + 6, bw, bh)})
            x += bw + gap

    # -- 对局控制 ----------------------------------------------------------
    def new_game(self):
        self.state = GameState()
        self.selected = None
        self.legal_targets = []
        self.last_move = None
        self.history = []
        self.status = ''
        self.notice = ''
        self.result = None
        self.hint_move = None
        self.ai = None
        self.ai_pending = False
        self.ai_avoid = None
        self.panel_mode = 'record'
        self.record_scroll = 0

    def undo(self):
        if self.result or not self.state.history:
            return
        st = self.state
        # 人机模式：AI 已经应手时，一次撤销“自己一步 + AI 一步”
        n = 1
        if self.mode == 'ai' and st.turn == self.human_color and len(st.history) >= 2:
            n = 2
            # 记住 AI 上次走的那手，悔棋后让它换个走法，避免原地打转
            self.ai_avoid = st.history[-2][0]
        for _ in range(n):
            if st.history:
                st.undo_move()
                if self.history:
                    self.history.pop()
        self.selected = None
        self.legal_targets = []
        self.last_move = None
        self.hint_move = None
        self.status = '已悔棋'
        self.notice = ''
        self.ai = None
        self.ai_pending = False

    def apply_move(self, mv, by_ai=False):
        st = self.state
        mover = st.turn
        note = move_notation(st, mv)
        captured = st.board[mv[2]][mv[3]]
        st.do_move(mv)
        self.last_move = mv
        self.selected = None
        self.legal_targets = []
        self.hint_move = None
        self.history.append((note, mover, captured.char() if captured else ''))

        self.sounds.play('capture' if captured is not None else 'move')

        res, msg = game_result(st)
        if res != 'playing':
            self.result = (res, msg)
            self.status = msg
            self.notice = ''
            self.flash = 1.0
            return
        if st.in_check(st.turn):
            self.status = '将军！'
            self.notice = ''
            self.sounds.play('check')
            self.flash = 1.0
        else:
            self.status = ''
            self.notice = ''
        rep = st.repetition_count()
        if rep >= 2:
            self.notice = '这个局面第 %d 次出现了，别再重复走' % rep

    def start_ai(self):
        if self.mode != 'ai' or self.result:
            return
        if self.state.turn == self.human_color:
            return
        if self.ai is not None and self.ai.is_running():
            return
        depth, limit = (2, 1.0) if self.difficulty == 1 else (5, 2.2)
        self.ai = AIEngine(depth, limit)
        self.ai.start(self.state, avoid=self.ai_avoid)
        self.ai_pending = True
        self.ai_avoid = None

    def poll_ai(self):
        if self.ai is None:
            return
        mv, done = self.ai.poll()
        if done:
            self.ai_pending = False
            if mv is not None and not self.result:
                self.apply_move(mv, by_ai=True)
            elif mv is None and not self.result:
                # AI 无棋可走：可能是将死或困毙
                res, msg = game_result(self.state)
                if res != 'playing':
                    self.result = (res, msg)
                    self.status = msg
            self.ai = None

    def request_hint(self):
        if self.result:
            return
        self.status = '正在算提示…'

        def work():
            mv = best_move(self.state.copy(), 3, 1.5)
            self.hint_move = mv
            self.status = '提示：%s' % (move_notation(self.state, mv) if mv else '无')
        threading.Thread(target=work, daemon=True).start()

    # -- 输入 --------------------------------------------------------------
    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
            return
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self.running = False
            elif ev.key == pygame.K_r:
                self.new_game()
            elif ev.key == pygame.K_u:
                self.undo()
            elif ev.key == pygame.K_h:
                self.request_hint()
            elif ev.key == pygame.K_s:
                self.save_game()
            elif ev.key == pygame.K_l:
                self.toggle_save_list()
            elif ev.key == pygame.K_m:
                self.toggle_mode()
            elif ev.key == pygame.K_f:
                self.toggle_fullscreen()
            return
        if ev.type == pygame.MOUSEWHEEL:
            if self.layout.rec.collidepoint(pygame.mouse.get_pos()):
                self.scroll_record(-ev.y)
            return
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                self.on_left_click(ev.pos)
            elif ev.button == 3:
                self.selected = None
                self.legal_targets = []
                self.hint_move = None

    def on_left_click(self, pos):
        for btn in self.buttons:
            if btn['rect'].collidepoint(pos):
                self.on_button(btn['id'])
                return
        for btn in self.rec_buttons:
            if btn['rect'].collidepoint(pos):
                self.on_rec_button(btn['id'])
                return
        # 点击棋谱里的存档条目
        if self.panel_mode == 'saves':
            rects = self.panel_row_rects()
            for i, rect in enumerate(rects):
                if rect.collidepoint(pos) and i < len(self.save_items):
                    self.load_game(self.save_items[i]['path'])
                    return

        r = self.row_at(pos[1])
        c = self.col_at(pos[0])
        if r < 0 or c < 0:
            return
        if self.result:
            return
        if self.mode == 'ai' and self.state.turn != self.human_color:
            return

        piece = self.state.board[r][c]
        if self.selected is not None:
            sr, sc = self.selected
            if (sr, sc) == (r, c):
                self.selected = None
                self.legal_targets = []
                return
            if (r, c) in self.legal_targets:
                self.apply_move((sr, sc, r, c))
                return
            # 点到己方其它棋子 → 改选
            if piece is not None and piece.color == self.state.turn:
                self.select(r, c)
            else:
                self.selected = None
                self.legal_targets = []
            return

        if piece is not None and piece.color == self.state.turn:
            self.select(r, c)

    def select(self, r, c):
        self.selected = (r, c)
        self.legal_targets = []
        for mv in legal_moves(self.state, self.state.turn):
            if mv[0] == r and mv[1] == c:
                self.legal_targets.append((mv[2], mv[3]))
        self.hint_move = None

    def on_button(self, bid):
        if bid == 'new':
            self.new_game()
        elif bid == 'undo':
            self.undo()
        elif bid == 'hint':
            self.request_hint()
        elif bid == 'sound':
            self.sounds.enabled = not self.sounds.enabled
        elif bid == 'level':
            self.difficulty = 1 if self.difficulty == 2 else 2
        elif bid == 'mode':
            self.toggle_mode()
        elif bid == 'full':
            self.toggle_fullscreen()

    def on_rec_button(self, bid):
        if bid == 'save':
            self.save_game()
        elif bid == 'load':
            self.toggle_save_list()
        elif bid == 'up':
            self.scroll_record(-1)
        elif bid == 'down':
            self.scroll_record(1)

    def toggle_mode(self):
        self.mode = 'pvp' if self.mode == 'ai' else 'ai'
        self.human_color = RED
        self.ai = None
        self.ai_pending = False
        self.status = '双人下棋' if self.mode == 'pvp' else '人机下棋（你执红先行）'

    # -- 棋谱面板 ----------------------------------------------------------
    def panel_items(self):
        """面板当前显示的条目：棋谱记录或存档列表。"""
        if self.panel_mode == 'saves':
            return list(self.save_items)
        out = []
        for i, item in enumerate(self.history):
            note, mover, cap = item
            out.append({'kind': 'move', 'num': i + 1, 'side': mover,
                        'note': note, 'cap': cap})
        return out

    def panel_body(self):
        L = self.layout
        head = L.rec_head_h
        avail = max(L.rec_row_h, L.rec.height - head - 8)
        rows = max(1, avail // L.rec_row_h)
        return pygame.Rect(L.rec.x + 8, L.rec.y + head,
                           max(10, L.rec.width - 16),
                           rows * L.rec_row_h)

    def panel_row_rects(self):
        L = self.layout
        body = self.panel_body()
        rects = []
        y = body.y - self.record_scroll
        for i in range(len(self.panel_items())):
            rects.append(pygame.Rect(body.x, y, body.width, L.rec_row_h))
            y += L.rec_row_h
        return rects

    def scroll_record(self, rows):
        L = self.layout
        body = self.panel_body()
        total = len(self.panel_items()) * L.rec_row_h
        max_scroll = max(0, total - body.height)
        self.record_scroll = max(0, min(max_scroll,
                                        self.record_scroll + rows * L.rec_row_h))

    # -- 保存 / 读取 --------------------------------------------------------
    def refresh_save_list(self):
        items = []
        folder = self.save_dir
        if folder and os.path.isdir(folder):
            try:
                names = os.listdir(folder)
            except Exception:
                names = []
            for fn in names:
                if not fn.lower().endswith('.json'):
                    continue
                path = os.path.join(folder, fn)
                label, moves = fn, 0
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    label = data.get('saved_at', fn)
                    moves = len(data.get('moves') or [])
                except Exception:
                    pass
                items.append({'kind': 'save', 'path': path, 'label': label,
                              'info': '共 %d 手' % moves})
        items.sort(key=lambda it: it['label'], reverse=True)
        self.save_items = items

    def toggle_save_list(self):
        if self.panel_mode == 'saves':
            self.panel_mode = 'record'
            self.record_scroll = 0
        else:
            self.refresh_save_list()
            self.panel_mode = 'saves'
            self.record_scroll = 0

    def save_game(self):
        folder = self.save_dir
        if not folder:
            self.status = '找不到存档文件夹，保存失败'
            return False
        moves = [list(mv[0]) for mv in self.state.history]
        data = {
            'version': 1,
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'mode': self.mode,
            'difficulty': self.difficulty,
            'human_color': self.human_color,
            'moves': moves,
            'result': (self.result[1] if self.result else ''),
        }
        stamp = time.strftime('%Y-%m-%d_%H-%M-%S')
        path = os.path.join(folder, '棋局_%s.json' % stamp)
        n = 2
        while os.path.exists(path):
            path = os.path.join(folder, '棋局_%s_%d.json' % (stamp, n))
            n += 1
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        except Exception as e:
            self.status = '保存失败：%s' % e
            return False
        self.status = '已保存：%s' % os.path.basename(path)
        self.refresh_save_list()
        return True

    def load_game(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            self.status = '读取失败：%s' % e
            return False
        moves = data.get('moves') or []
        self.new_game()
        self.mode = data.get('mode', 'ai')
        try:
            self.difficulty = int(data.get('difficulty', 2))
        except Exception:
            self.difficulty = 2
        self.human_color = data.get('human_color', RED)
        st = self.state
        for raw in moves:
            try:
                mv = tuple(int(x) for x in raw)
            except Exception:
                break
            if len(mv) != 4 or mv not in legal_moves(st, st.turn):
                break
            mover = st.turn
            note = move_notation(st, mv)
            captured = st.board[mv[2]][mv[3]]
            st.do_move(mv)
            self.history.append((note, mover, captured.char() if captured else ''))
            self.last_move = mv
        res, msg = game_result(st)
        if res != 'playing':
            self.result = (res, msg)
        self.panel_mode = 'record'
        self.record_scroll = 0
        self.ai = None
        self.ai_pending = False
        self.status = '已读取：%s（%d 手）' % (os.path.basename(path),
                                             len(self.history))
        return True

    # -- 文字内容 ----------------------------------------------------------
    def turn_text(self):
        if self.result:
            return '本局结束'
        turn = self.state.turn
        if self.ai_pending:
            return '电脑思考中，请稍候'
        if self.mode == 'pvp':
            return '轮到%s走棋' % ('红方' if turn == RED else '黑方')
        if turn == self.human_color:
            return '你的回合（红方）'
        return '电脑回合（黑方）'

    def sub_text(self):
        if self.status:
            return self.status
        if self.notice:
            return self.notice
        steps = len(self.state.history)
        if steps == 0:
            return '点自己的棋子，再点要去的位置'
        return '已走 %d 手' % steps

    def button_label(self, bid, label):
        if bid == 'level':
            return '难度：%s' % ('困难' if self.difficulty == 2 else '简单')
        if bid == 'mode':
            return '对战：%s' % ('人机' if self.mode == 'ai' else '双人')
        if bid == 'sound':
            return '音效：%s' % ('开' if self.sounds.enabled else '关')
        if bid == 'full':
            return '全屏：%s' % ('开' if self.fullscreen else '关')
        return label

    def rec_button_label(self, bid, label):
        if bid == 'load':
            return '取消' if self.panel_mode == 'saves' else '读取'
        return label

    # -- 绘制 --------------------------------------------------------------
    def draw(self):
        self.screen.fill(C_WINDOW)
        self.draw_card()
        self.draw_banner()
        self.draw_board()
        self.draw_pieces()
        self.draw_record()
        self.draw_buttons()
        self.draw_tip()
        self.draw_overlay()
        self.draw_font_warning()
        pygame.display.flip()

    def draw_font_warning(self):
        """没找到中文字体时，在屏幕顶部挂一条提示。"""
        if not self.font_warning:
            return
        L = self.layout
        f = self.fonts.get(max(14, min(20, int(L.w * 0.016))), bold=True)
        img = f.render(self.font_warning, True, (255, 240, 220))
        box = pygame.Rect(0, 0, L.w, img.get_height() + 10)
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        layer.fill((150, 30, 26, 225))
        self.screen.blit(layer, (0, 0))
        self.screen.blit(img, img.get_rect(center=(L.w // 2, box.height // 2)))

    def draw_card(self):
        """宽屏时在棋盘这一列后面垫一块卡片。"""
        card = self.layout.card
        if card.width <= 0:
            return
        shadow = pygame.Surface((card.width + 24, card.height + 24), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 26),
                         shadow.get_rect(), border_radius=18)
        self.screen.blit(shadow, (card.x - 12, card.y - 6))
        pygame.draw.rect(self.screen, C_CARD, card, border_radius=16)
        pygame.draw.rect(self.screen, C_CARD_LINE, card, border_radius=16, width=2)

    def draw_banner(self):
        L = self.layout
        rect = L.banner
        pygame.draw.rect(self.screen, C_BANNER, rect, border_radius=12)
        pygame.draw.rect(self.screen, C_BANNER_LINE, rect, border_radius=12, width=2)

        f1 = self.fonts.get(L.f_turn, bold=True)
        img = f1.render(self.turn_text(), True, C_TEXT_DARK)
        self.screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + L.banner_h * 0.38)))

        f2 = self.fonts.get(L.f_sub)
        sub = self.sub_text()
        if '将军' in sub or '将死' in sub or '胜' in sub or '和' in sub:
            color = C_CHECK
        elif '出现' in sub:
            color = (186, 120, 20)
        else:
            color = C_TEXT_DIM
        img = f2.render(sub, True, color)
        self.screen.blit(img, img.get_rect(center=(rect.centerx, rect.y + L.banner_h * 0.76)))

    def draw_board(self):
        L = self.layout
        rect = pygame.Rect(L.frame_x, L.frame_y, L.frame_w, L.frame_h)
        pygame.draw.rect(self.screen, C_BOARD_EDGE, rect, border_radius=10)
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(self.screen, C_BOARD, inner, border_radius=8)
        pygame.draw.rect(self.screen, C_BOARD_DARK, inner, border_radius=8, width=2)

        w = max(1, L.cell // 33)
        # 横线
        for r in range(10):
            y = self.board_y(r)
            pygame.draw.line(self.screen, C_LINE, (self.board_x(0), y),
                             (self.board_x(8), y), w)
        # 纵线：中间 7 条在楚河汉界处断开，两侧边框贯通
        for c in range(9):
            x = self.board_x(c)
            if c in (0, 8):
                pygame.draw.line(self.screen, C_LINE, (x, self.board_y(0)),
                                 (x, self.board_y(9)), w)
            else:
                pygame.draw.line(self.screen, C_LINE, (x, self.board_y(0)),
                                 (x, self.board_y(4)), w)
                pygame.draw.line(self.screen, C_LINE, (x, self.board_y(5)),
                                 (x, self.board_y(9)), w)

        # 九宫斜线
        for (r0, c0, r1, c1) in ((0, 3, 2, 5), (0, 5, 2, 3), (7, 3, 9, 5), (7, 5, 9, 3)):
            pygame.draw.line(self.screen, C_LINE, (self.board_x(c0), self.board_y(r0)),
                             (self.board_x(c1), self.board_y(r1)), w)

        # 炮位 / 兵位标记
        for (c, r) in MARKERS:
            self.draw_marker(c, r)

        # 楚河汉界
        f = self.fonts.get(L.f_river)
        left = f.render('楚  河', True, C_RIVER)
        right = f.render('漢  界', True, C_RIVER)
        mid_y = L.board_y0 + int(4.5 * L.cell)
        self.screen.blit(left, left.get_rect(center=(L.board_x0 + int(1.9 * L.cell), mid_y)))
        self.screen.blit(right, right.get_rect(center=(L.board_x0 + int(6.1 * L.cell), mid_y)))

    def draw_marker(self, c, r):
        L = self.layout
        x, y = self.board_x(c), self.board_y(r)
        d, Ln = int(L.cell * 0.11), int(L.cell * 0.19)
        for sx in (-1, 1):
            for sy in (-1, 1):
                if c == 0 and sx < 0:
                    continue
                if c == 8 and sx > 0:
                    continue
                if r == 0 and sy < 0:
                    continue
                if r == 9 and sy > 0:
                    continue
                x0 = x + sx * d
                y0 = y + sy * d
                if sx < 0:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0 + Ln, y0), 2)
                else:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0 - Ln, y0), 2)
                if sy < 0:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0, y0 + Ln), 2)
                else:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0, y0 - Ln), 2)

    def draw_pieces(self):
        L = self.layout
        st = self.state
        # 上一步的起止格
        if self.last_move:
            self.draw_last(self.last_move[0], self.last_move[1])
            self.draw_last(self.last_move[2], self.last_move[3])
        # 提示着法
        if self.hint_move:
            self.draw_last(self.hint_move[0], self.hint_move[1], C_HILITE)
            self.draw_last(self.hint_move[2], self.hint_move[3], C_HILITE)

        for r in range(10):
            for c in range(9):
                p = st.board[r][c]
                if p is None:
                    continue
                self.draw_piece(p, r, c)

        # 可落子提示
        for (tr, tc) in self.legal_targets:
            x, y = self.board_x(tc), self.board_y(tr)
            if st.board[tr][tc] is None:
                pygame.draw.circle(self.screen, C_HILITE, (x, y), int(L.cell * 0.17))
                pygame.draw.circle(self.screen, (176, 128, 12), (x, y),
                                   int(L.cell * 0.17), 2)
            else:
                pygame.draw.circle(self.screen, C_HILITE, (x, y), L.piece_r + 5, 4)

        # 选中棋子
        if self.selected:
            r, c = self.selected
            x, y = self.board_x(c), self.board_y(r)
            pygame.draw.circle(self.screen, C_HILITE, (x, y), L.piece_r + 4, 4)

        # 被将军的将/帅
        for color in (RED, BLACK):
            kp = st.king_pos.get(color)
            if kp and st.in_check(color):
                x, y = self.board_x(kp[1]), self.board_y(kp[0])
                pygame.draw.circle(self.screen, C_CHECK, (x, y), L.piece_r + 7, 4)

    def draw_piece(self, p, r, c):
        L = self.layout
        x, y = self.board_x(c), self.board_y(r)
        R = L.piece_r
        red = p.color == RED
        edge = C_EDGE_R if red else C_EDGE_B
        text = C_TEXT_R if red else C_TEXT_B
        selected = self.selected == (r, c)

        # 阴影
        sh = pygame.Surface((R * 2 + 6, R * 2 + 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, R * 2 + 6, R * 2 + 6))
        self.screen.blit(sh, (x - R - 3, y - R - 1))

        pygame.draw.circle(self.screen, edge, (x, y), R)
        pygame.draw.circle(self.screen, C_PIECE_FACE, (x, y), R - 2)
        if selected:
            pygame.draw.circle(self.screen, C_HILITE, (x, y), R + 4, 4)
        # 内圈
        pygame.draw.circle(self.screen, edge, (x, y), max(6, R - 7), 2)

        f = self.fonts.get(L.f_piece, bold=True)
        img = f.render(CHARS[p.color][p.kind], True, text)
        self.screen.blit(img, img.get_rect(center=(x, y - 1)))

    def draw_last(self, r, c, color=None):
        L = self.layout
        color = color or C_LAST
        x, y = self.board_x(c), self.board_y(r)
        R = L.piece_r
        Ln, T = int(L.cell * 0.2), max(2, L.cell // 22)
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, y0 = x + sx * (R - 3), y + sy * (R - 3)
                if sx < 0:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0 + Ln, y0), T)
                else:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0 - Ln, y0), T)
                if sy < 0:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0, y0 + Ln), T)
                else:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0, y0 - Ln), T)

    # -- 棋谱 / 存档列表 ----------------------------------------------------
    def draw_record(self):
        L = self.layout
        rec = L.rec
        if rec.width <= 0 or rec.height <= 0:
            return
        pygame.draw.rect(self.screen, C_REC_BG, rec, border_radius=10)
        pygame.draw.rect(self.screen, C_REC_LINE, rec, border_radius=10, width=2)

        # 标题
        title = '棋谱记录' if self.panel_mode == 'record' else '选择棋局'
        f = self.fonts.get(L.f_rec_head, bold=True)
        img = f.render(title, True, C_TEXT_DARK)
        self.screen.blit(img, (rec.x + 12, rec.y + 5))

        # 右上角小按钮
        for btn in self.rec_buttons:
            rect = btn['rect']
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen, C_REC_BTN_HOVER if hover else C_REC_BTN,
                             rect, border_radius=6)
            fb = self.fonts.get(max(15, int(L.f_rec * 0.82)), bold=True)
            label = self.rec_button_label(btn['id'], btn['label'])
            t = fb.render(label, True, (255, 255, 255))
            self.screen.blit(t, t.get_rect(center=rect.center))

        # 内容
        body = self.panel_body()
        clip = self.screen.get_clip()
        self.screen.set_clip(body)
        items = self.panel_items()
        if not items:
            f2 = self.fonts.get(L.f_rec)
            txt = '还没有保存的棋局' if self.panel_mode == 'saves' else '还没有走棋'
            img = f2.render(txt, True, C_TEXT_DIM)
            self.screen.blit(img, img.get_rect(center=(body.centerx,
                                                       body.y + L.rec_row_h // 2)))
        else:
            for i, it in enumerate(items):
                y = body.y - self.record_scroll + i * L.rec_row_h
                if y + L.rec_row_h < body.y or y > body.bottom:
                    continue
                if it['kind'] == 'move':
                    self.draw_move_row(it, body, y)
                else:
                    self.draw_save_row(it, body, y)
        self.screen.set_clip(clip)

        # 滚动条
        total = len(items) * L.rec_row_h
        if total > body.height:
            track = pygame.Rect(body.right - 6, body.y, 5, body.height)
            pygame.draw.rect(self.screen, C_REC_SCROLL, track, border_radius=3)
            th = max(24, int(body.height * body.height / float(total)))
            ty = body.y + int((body.height - th) * self.record_scroll /
                              float(max(1, total - body.height)))
            pygame.draw.rect(self.screen, (140, 128, 108),
                             pygame.Rect(track.x, ty, track.width, th),
                             border_radius=3)

    def draw_move_row(self, it, body, y):
        L = self.layout
        row_h = L.rec_row_h
        fnum = self.fonts.get(max(15, int(L.f_rec * 0.82)))
        img = fnum.render('%d.' % it['num'], True, C_TEXT_DIM)
        self.screen.blit(img, (body.x + 4, y + (row_h - img.get_height()) // 2))

        red = it['side'] == RED
        tag = pygame.Rect(body.x + 44, y + 3, 32, row_h - 6)
        pygame.draw.rect(self.screen, C_EDGE_R if red else C_EDGE_B,
                         tag, border_radius=6)
        ft = self.fonts.get(max(14, int(L.f_rec * 0.74)), bold=True)
        timg = ft.render('红' if red else '黑', True, (255, 255, 255))
        self.screen.blit(timg, timg.get_rect(center=tag.center))

        f = self.fonts.get(L.f_rec, bold=True)
        img = f.render(it['note'], True, C_TEXT_R if red else C_TEXT_B)
        self.screen.blit(img, (body.x + 86, y + (row_h - img.get_height()) // 2))
        if it['cap']:
            fc = self.fonts.get(max(14, int(L.f_rec * 0.8)))
            cimg = fc.render('吃%s' % it['cap'], True, C_TEXT_DIM)
            self.screen.blit(cimg, (body.x + 90 + img.get_width(),
                                    y + (row_h - cimg.get_height()) // 2))

    def draw_save_row(self, it, body, y):
        L = self.layout
        row_h = L.rec_row_h
        f = self.fonts.get(L.f_rec)
        img = f.render(it['label'], True, C_TEXT_DARK)
        self.screen.blit(img, (body.x + 8, y + (row_h - img.get_height()) // 2))
        fc = self.fonts.get(max(14, int(L.f_rec * 0.82)))
        cimg = fc.render(it['info'], True, C_TEXT_DIM)
        self.screen.blit(cimg, (body.x + 14 + img.get_width(),
                                y + (row_h - cimg.get_height()) // 2))

    def draw_buttons(self):
        L = self.layout
        for btn in self.buttons:
            rect = btn['rect']
            hover = rect.collidepoint(pygame.mouse.get_pos())
            if btn['big']:
                fill = C_BTN_HOVER if hover else C_BTN
                f = self.fonts.get(L.f_btn, bold=True)
            else:
                fill = C_BTN2_HOVER if hover else C_BTN2
                f = self.fonts.get(L.f_btn2)
            pygame.draw.rect(self.screen, fill, rect, border_radius=10)
            pygame.draw.rect(self.screen, C_BTN_LINE, rect, border_radius=10, width=2)
            label = self.button_label(btn['id'], btn['label'])
            t = f.render(label, True, C_BUTTON_TEXT)
            self.screen.blit(t, t.get_rect(center=rect.center))

    def tip_surface(self):
        """底部提示文字，字号自动缩小以适应画布宽度。"""
        L = self.layout
        text = ('左键选子落子 · 右键取消 · R新局 · U悔棋 · H提示 · '
                'S保存 · L读取 · F全屏 · Esc退出')
        size = L.f_tip
        img = self.fonts.get(size).render(text, True, C_TEXT_DIM)
        limit = L.w - 24
        if L.card.width > 0:
            limit = min(limit, L.card.width - 24)
        while img.get_width() > limit and size > 12:
            size -= 1
            img = self.fonts.get(size).render(text, True, C_TEXT_DIM)
        return img

    def draw_tip(self):
        L = self.layout
        img = self.tip_surface()
        self.screen.blit(img, img.get_rect(center=(L.w // 2, L.tip_y)))

    def draw_overlay(self):
        if not self.result:
            return
        L = self.layout
        res, msg = self.result
        if res == 'red_win':
            title = '红方胜利'
        elif res == 'black_win':
            title = '黑方胜利'
        else:
            title = '和棋'
        cx, cy = self.board_x(4), self.board_y(4)
        w, h = int(L.cell * 7), int(L.cell * 3)
        panel = pygame.Rect(cx - w // 2, cy - h // 2, w, h)
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(layer, (30, 26, 22, 225), layer.get_rect(), border_radius=14)
        pygame.draw.rect(layer, (250, 244, 232), layer.get_rect(), border_radius=14, width=3)
        self.screen.blit(layer, panel.topleft)

        f1 = self.fonts.get(max(28, int(L.cell * 0.78)), bold=True)
        img = f1.render(title, True, (255, 236, 200))
        self.screen.blit(img, img.get_rect(center=(cx, cy - int(L.cell * 0.4))))
        f2 = self.fonts.get(max(20, int(L.cell * 0.38)))
        img = f2.render(msg, True, (238, 228, 212))
        self.screen.blit(img, img.get_rect(center=(cx, cy + int(L.cell * 0.45))))
        f3 = self.fonts.get(max(18, int(L.cell * 0.35)))
        img = f3.render('点“新 局”再来一盘', True, (196, 206, 214))
        self.screen.blit(img, img.get_rect(center=(cx, cy + int(L.cell * 1.05))))

    # -- 主循环 ------------------------------------------------------------
    def run(self):
        while self.running:
            for ev in pygame.event.get():
                self.handle_event(ev)
            self.poll_ai()
            self.start_ai()
            self.draw()
            self.clock.tick(60)


def main():
    app = XiangqiApp(fullscreen=True)
    app.run()
    pygame.quit()


if __name__ == '__main__':
    main()
