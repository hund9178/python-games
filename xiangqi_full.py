# -*- coding: utf-8 -*-
"""
象棋 (Xiangqi) — Chinese Chess
==========================================
完整规则 + 内置 AI 对手 + 双人本地模式。

    python xiangqi.py

操作
    左键点子选中，再点目标落子；右键取消选择
    侧栏：重新开始 / 悔棋 / 提示 / 难度 / 模式 / 音效
    快捷键  R 新局   U 悔棋   H 提示   M 切换模式   Esc 退出
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
from array import array

import pygame

from xiangqi_rules import (RED, BLACK, GameState, legal_moves, best_move,
                           move_notation, game_result, CHARS)

# ==========================================================================
# 布局与配色
# ==========================================================================
WIN_W, WIN_H = 1020, 676

CELL = 58
BOARD_X, BOARD_Y = 46, 42
GRID_W = CELL * 8
GRID_H = CELL * 9
PIECE_R = 26

PANEL_X = BOARD_X + GRID_W + 34
PANEL_W = WIN_W - PANEL_X - 24

C_WINDOW = (24, 22, 20)
C_BOARD = (214, 176, 124)
C_BOARD_EDGE = (146, 108, 66)
C_BOARD_DARK = (196, 158, 110)
C_LINE = (72, 48, 28)
C_RIVER = (140, 92, 48)
C_PIECE_FACE = (238, 220, 188)
C_PIECE_FACE2 = (252, 240, 214)
C_EDGE_R = (170, 36, 38)
C_EDGE_B = (46, 46, 54)
C_TEXT_R = (168, 28, 30)
C_TEXT_B = (28, 28, 34)
C_HILITE = (255, 208, 70)
C_LAST = (60, 150, 215)
C_CHECK = (232, 62, 48)
C_PANEL = (42, 38, 34)
C_PANEL_HI = (56, 51, 45)
C_TEXT = (228, 222, 212)
C_TEXT_DIM = (150, 144, 136)
C_BTN = (60, 55, 49)
C_BTN_HOVER = (88, 80, 70)
C_BTN_ACTIVE = (150, 116, 48)

# 棋盘上的“炮位/兵位”标记点（列, 行）
MARKERS = [(1, 2), (7, 2), (1, 7), (7, 7),
           (0, 3), (2, 3), (4, 3), (6, 3), (8, 3),
           (0, 6), (2, 6), (4, 6), (6, 6), (8, 6)]


def board_x(col):
    return BOARD_X + col * CELL


def board_y(row):
    return BOARD_Y + row * CELL


def col_at(px):
    c = int(round((px - BOARD_X) / CELL))
    return c if 0 <= c <= 8 else -1


def row_at(py):
    r = int(round((py - BOARD_Y) / CELL))
    return r if 0 <= r <= 9 else -1


# ==========================================================================
# 字体与音效
# ==========================================================================
class Fonts:
    def __init__(self):
        self.cache = {}

    def get(self, size, bold=False):
        key = (size, bold)
        if key not in self.cache:
            self.cache[key] = self._make(size, bold)
        return self.cache[key]

    def _make(self, size, bold):
        for name in ('simhei', 'microsoftyahei', 'msyh'):
            try:
                f = pygame.font.SysFont(name, size, bold=bold)
                if f is not None:
                    return f
            except Exception:
                pass
        base = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, 'frozen', False):
            base = getattr(sys, '_MEIPASS', base)
        for fname in ('msyh.ttc', 'msyhbd.ttc'):
            path = os.path.join(base, fname)
            if os.path.exists(path):
                try:
                    return pygame.font.Font(path, size)
                except Exception:
                    pass
        return pygame.font.Font(None, size)


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

    def start(self, state):
        work = state.copy()
        with self._lock:
            self._result = None
            self._done = False
        self._thread = threading.Thread(target=self._run, args=(work,), daemon=True)
        self._thread.start()

    def _run(self, work):
        try:
            mv = best_move(work, self.depth, self.time_limit)
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
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption('象棋 · Chinese Chess')
        self.icon = self._make_icon()
        if self.icon:
            pygame.display.set_icon(self.icon)
        self.clock = pygame.time.Clock()
        self.fonts = Fonts()
        self.sounds = Sounds()

        self.state = GameState()
        self.mode = 'ai'            # 'ai' 或 'pvp'
        self.human_color = RED
        self.difficulty = 2         # 1 简单 / 2 困难
        self.selected = None        # (r, c)
        self.legal_targets = []     # 可落子目标
        self.last_move = None
        self.history = []           # [(记谱, 记谱), ...] 每回合两项
        self.status = ''
        self.result = None
        self.flash = 0.0
        self.ai = None
        self.ai_pending = False
        self.hint_move = None
        self.buttons = []
        self.running = True
        self._build_buttons()

    # -- 初始化 ------------------------------------------------------------
    def _make_icon(self):
        try:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, (238, 220, 188), (32, 32), 30)
            pygame.draw.circle(surf, C_EDGE_R, (32, 32), 30, 3)
            f = self.fonts.get(28, bold=True)
            surf.blit(f.render('帅', True, C_TEXT_R), (0, 0))
            return surf
        except Exception:
            return None

    def _build_buttons(self):
        bw, bh = 196, 40
        gap = 12
        x0 = PANEL_X
        self.buttons = [
            {'id': 'new', 'label': '重新开始', 'rect': pygame.Rect(x0, 150, bw, bh)},
            {'id': 'undo', 'label': '悔 棋', 'rect': pygame.Rect(x0 + bw + gap, 150, bw, bh)},
            {'id': 'hint', 'label': '提 示', 'rect': pygame.Rect(x0, 150 + bh + gap, bw, bh)},
            {'id': 'sound', 'label': '音 效：开', 'rect': pygame.Rect(x0 + bw + gap, 150 + bh + gap, bw, bh)},
            {'id': 'level', 'label': '难度：困难', 'rect': pygame.Rect(x0, 150 + 2 * (bh + gap), bw, bh)},
            {'id': 'mode', 'label': '模式：人机', 'rect': pygame.Rect(x0 + bw + gap, 150 + 2 * (bh + gap), bw, bh)},
        ]

    # -- 对局控制 ----------------------------------------------------------
    def new_game(self):
        self.state = GameState()
        self.selected = None
        self.legal_targets = []
        self.last_move = None
        self.history = []
        self.status = ''
        self.result = None
        self.hint_move = None
        self.ai = None
        self.ai_pending = False

    def undo(self):
        if self.result or not self.state.history:
            return
        st = self.state
        # 人机模式：AI 已经应手时，一次撤销“自己一步 + AI 一步”
        n = 1
        if self.mode == 'ai' and st.turn == self.human_color and len(st.history) >= 2:
            n = 2
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
        self.history.append((note, mover))

        self.sounds.play('capture' if captured is not None else 'move')

        res, msg = game_result(st)
        if res != 'playing':
            self.result = (res, msg)
            self.status = msg
            self.flash = 1.0
            return
        if st.in_check(st.turn):
            self.status = '将军！'
            self.sounds.play('check')
            self.flash = 1.0
        else:
            self.status = ''

    def start_ai(self):
        if self.mode != 'ai' or self.result:
            return
        if self.state.turn == self.human_color:
            return
        if self.ai is not None and self.ai.is_running():
            return
        depth, limit = (2, 1.0) if self.difficulty == 1 else (5, 2.2)
        self.ai = AIEngine(depth, limit)
        self.ai.start(self.state)
        self.ai_pending = True

    def poll_ai(self):
        if self.ai is None:
            return
        mv, done = self.ai.poll()
        if done:
            self.ai_pending = False
            if mv is not None and not self.result:
                self.apply_move(mv, by_ai=True)
            self.ai = None

    def request_hint(self):
        if self.result:
            return
        self.status = '正在计算提示…'
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
            elif ev.key == pygame.K_m:
                self.toggle_mode()
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

        r = row_at(pos[1])
        c = col_at(pos[0])
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

    def toggle_mode(self):
        self.mode = 'pvp' if self.mode == 'ai' else 'ai'
        self.human_color = RED
        self.ai = None
        self.ai_pending = False
        self.status = '双人模式' if self.mode == 'pvp' else '人机模式（你执红先行）'

    # -- 绘制 --------------------------------------------------------------
    def draw(self):
        self.screen.fill(C_WINDOW)
        self.draw_board()
        self.draw_pieces()
        self.draw_sidebar()
        pygame.display.flip()

    def draw_board(self):
        margin = 32
        rect = pygame.Rect(BOARD_X - margin, BOARD_Y - margin,
                           GRID_W + 2 * margin, GRID_H + 2 * margin)
        pygame.draw.rect(self.screen, C_BOARD_EDGE, rect, border_radius=8)
        inner = rect.inflate(-6, -6)
        pygame.draw.rect(self.screen, C_BOARD, inner, border_radius=6)
        pygame.draw.rect(self.screen, C_BOARD_DARK, inner, border_radius=6, width=2)

        # 横线
        for r in range(10):
            y = board_y(r)
            pygame.draw.line(self.screen, C_LINE, (board_x(0), y), (board_x(8), y), 1)
        # 纵线：中间 7 条在楚河汉界处断开，两侧边框贯通
        for c in range(9):
            x = board_x(c)
            if c in (0, 8):
                pygame.draw.line(self.screen, C_LINE, (x, board_y(0)), (x, board_y(9)), 1)
            else:
                pygame.draw.line(self.screen, C_LINE, (x, board_y(0)), (x, board_y(4)), 1)
                pygame.draw.line(self.screen, C_LINE, (x, board_y(5)), (x, board_y(9)), 1)

        # 九宫斜线
        for (r0, c0, r1, c1) in ((0, 3, 2, 5), (0, 5, 2, 3), (7, 3, 9, 5), (7, 5, 9, 3)):
            pygame.draw.line(self.screen, C_LINE, (board_x(c0), board_y(r0)),
                             (board_x(c1), board_y(r1)), 1)

        # 炮位 / 兵位标记
        for (c, r) in MARKERS:
            self.draw_marker(c, r)

        # 楚河汉界
        f = self.fonts.get(30)
        left = f.render('楚  河', True, C_RIVER)
        right = f.render('漢  界', True, C_RIVER)
        mid_y = BOARD_Y + int(4.5 * CELL)
        self.screen.blit(left, left.get_rect(center=(BOARD_X + int(1.9 * CELL), mid_y)))
        self.screen.blit(right, right.get_rect(center=(BOARD_X + int(6.1 * CELL), mid_y)))

    def draw_marker(self, c, r):
        x, y = board_x(c), board_y(r)
        d, L = 6, 11
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
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0 + L, y0), 1)
                else:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0 - L, y0), 1)
                if sy < 0:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0, y0 + L), 1)
                else:
                    pygame.draw.line(self.screen, C_LINE, (x0, y0), (x0, y0 - L), 1)

    def draw_pieces(self):
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
            x, y = board_x(tc), board_y(tr)
            if st.board[tr][tc] is None:
                pygame.draw.circle(self.screen, C_HILITE, (x, y), 8)
            else:
                pygame.draw.circle(self.screen, C_HILITE, (x, y), PIECE_R + 4, 3)

        # 选中棋子
        if self.selected:
            r, c = self.selected
            x, y = board_x(c), board_y(r)
            pygame.draw.circle(self.screen, C_HILITE, (x, y), PIECE_R + 4, 3)

        # 被将军的将/帅
        for color in (RED, BLACK):
            kp = st.king_pos.get(color)
            if kp and st.in_check(color):
                x, y = board_x(kp[1]), board_y(kp[0])
                pygame.draw.circle(self.screen, C_CHECK, (x, y), PIECE_R + 6, 3)

    def draw_piece(self, p, r, c):
        x, y = board_x(c), board_y(r)
        red = p.color == RED
        edge = C_EDGE_R if red else C_EDGE_B
        text = C_TEXT_R if red else C_TEXT_B
        selected = self.selected == (r, c)

        # 阴影
        sh = pygame.Surface((PIECE_R * 2 + 6, PIECE_R * 2 + 6), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), (0, 0, PIECE_R * 2 + 6, PIECE_R * 2 + 6))
        self.screen.blit(sh, (x - PIECE_R - 3, y - PIECE_R - 1))

        pygame.draw.circle(self.screen, edge, (x, y), PIECE_R)
        pygame.draw.circle(self.screen, C_PIECE_FACE, (x, y), PIECE_R - 2)
        if selected:
            pygame.draw.circle(self.screen, C_HILITE, (x, y), PIECE_R + 3, 3)
        # 内圈
        pygame.draw.circle(self.screen, edge, (x, y), PIECE_R - 6, 1)

        f = self.fonts.get(30, bold=True)
        img = f.render(CHARS[p.color][p.kind], True, text)
        self.screen.blit(img, img.get_rect(center=(x, y - 1)))

    def draw_last(self, r, c, color=None):
        color = color or C_LAST
        x, y = board_x(c), board_y(r)
        L, T = 11, 3
        for sx in (-1, 1):
            for sy in (-1, 1):
                x0, y0 = x + sx * (PIECE_R - 2), y + sy * (PIECE_R - 2)
                if sx < 0:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0 + L, y0), 2)
                else:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0 - L, y0), 2)
                if sy < 0:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0, y0 + L), 2)
                else:
                    pygame.draw.line(self.screen, color, (x0, y0), (x0, y0 - L), 2)

    def _history_rows(self):
        """把 [(记谱, 颜色), ...] 整理成每回合的红/黑两列。"""
        rows = []
        i = 0
        while i < len(self.history):
            red_note, black_note = '', ''
            note, col = self.history[i]
            if col == RED:
                red_note = note
            else:
                black_note = note
            if i + 1 < len(self.history):
                note2, col2 = self.history[i + 1]
                if col2 == RED:
                    red_note = note2
                else:
                    black_note = note2
                i += 2
            else:
                i += 1
            rows.append((red_note, black_note))
        return rows

    # -- 侧栏 --------------------------------------------------------------
    def draw_sidebar(self):
        x = PANEL_X
        f_title = self.fonts.get(34, bold=True)
        f_sec = self.fonts.get(20, bold=True)
        f_txt = self.fonts.get(18)
        f_small = self.fonts.get(16)

        img = f_title.render('象  棋', True, C_TEXT)
        self.screen.blit(img, (x, 30))

        # 状态区
        pygame.draw.rect(self.screen, C_PANEL, pygame.Rect(x, 78, PANEL_W, 58), border_radius=6)
        turn = self.state.turn
        tname = '红方' if turn == RED else '黑方'
        if self.ai_pending:
            line = '黑方思考中…' if turn == BLACK else '红方思考中…'
        elif self.mode == 'pvp':
            line = '%s 走棋' % tname
        else:
            line = '轮到你走棋' if turn == self.human_color else '等待 AI…'
        img = f_sec.render(line, True, C_TEXT)
        self.screen.blit(img, (x + 14, 88))
        if self.status:
            img = f_txt.render(self.status, True, C_CHECK if '将军' in self.status else C_TEXT_DIM)
            self.screen.blit(img, (x + 14, 112))

        # 按钮
        for btn in self.buttons:
            rect = btn['rect']
            hover = rect.collidepoint(pygame.mouse.get_pos())
            if btn['id'] == 'sound':
                label = '音 效：%s' % ('开' if self.sounds.enabled else '关')
            elif btn['id'] == 'level':
                label = '难度：%s' % ('困难' if self.difficulty == 2 else '简单')
            elif btn['id'] == 'mode':
                label = '模式：%s' % ('人机' if self.mode == 'ai' else '双人')
            else:
                label = btn['label']
            color = C_BTN_HOVER if hover else C_BTN
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            pygame.draw.rect(self.screen, (86, 78, 68), rect, border_radius=6, width=1)
            t = f_txt.render(label, True, C_TEXT)
            self.screen.blit(t, t.get_rect(center=rect.center))

        # 走法记录
        box = pygame.Rect(x, 302, PANEL_W, 300)
        pygame.draw.rect(self.screen, C_PANEL, box, border_radius=6)
        pygame.draw.rect(self.screen, (62, 56, 49), box, border_radius=6, width=1)
        img = f_sec.render('走法记录', True, C_TEXT)
        self.screen.blit(img, (x + 14, 312))
        pygame.draw.line(self.screen, (80, 72, 63), (x + 12, 344), (x + PANEL_W - 12, 344), 1)
        hd = f_small.render('红方', True, C_TEXT_DIM)
        self.screen.blit(hd, (x + 52, 350))
        hd = f_small.render('黑方', True, C_TEXT_DIM)
        self.screen.blit(hd, (x + 158, 350))

        rows = self._history_rows()
        rows = rows[-11:]
        for i, (red_note, black_note) in enumerate(rows):
            y = 376 + i * 20
            img = f_small.render('%d.' % (i + 1), True, C_TEXT_DIM)
            self.screen.blit(img, (x + 18, y))
            if red_note:
                img = f_small.render(red_note, True, C_TEXT)
                self.screen.blit(img, (x + 52, y))
            if black_note:
                img = f_small.render(black_note, True, C_TEXT)
                self.screen.blit(img, (x + 158, y))

        # 底部提示
        tip = f_small.render('左键选中/落子  右键取消  R新局 U悔棋 H提示 M模式', True, C_TEXT_DIM)
        self.screen.blit(tip, (x, 616))

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
    app = XiangqiApp()
    app.run()
    pygame.quit()


if __name__ == '__main__':
    main()
