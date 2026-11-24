# -*- coding: utf-8 -*-
"""
象棋核心规则引擎 (Xiangqi Rules Engine)
========================================
纯 Python 实现，不依赖 pygame，可单独测试。

实现内容
    · 全部棋子走法：车马炮相仕帅兵 / 将士象卒
    · 特殊限制：蹩马腿、塞象眼、炮需炮架、象士不可过河、兵过河可横走且不可后退
    · 将帅限九宫，飞将（照面）判定
    · 将军 / 将死 / 困毙（无棋可走同样判负）
    · 三次重复局面、60 回合无吃子判和
    · 中文着法记谱（前/后/中 + 进/退/平）
    · Alpha-Beta 搜索 AI（迭代加深 + 时间控制 + 静态评估）
"""

from __future__ import annotations

import random
import time

RED, BLACK = 'r', 'b'
ROWS, COLS = 10, 9

ORTHO = ((-1, 0), (1, 0), (0, -1), (0, 1))
DIAG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
HORSE = ((-2, -1), (-2, 1), (2, -1), (2, 1),
         (-1, -2), (-1, 2), (1, -2), (1, 2))

# 棋子字母 -> 中文
CHARS = {
    RED:   {'K': '帅', 'A': '仕', 'B': '相', 'N': '马', 'R': '车', 'C': '炮', 'P': '兵'},
    BLACK: {'K': '将', 'A': '士', 'B': '象', 'N': '马', 'R': '车', 'C': '炮', 'P': '卒'},
}

# 基础子力价值
VALUE = {'R': 900, 'C': 460, 'N': 420, 'B': 220, 'A': 220, 'P': 100, 'K': 10000}

CN_NUM = '一二三四五六七八九'

MATE = 100000
INF = 1000000
REP_PENALTY = 60        # 重复局面的扣分（越小越不喜欢重复）

# Zobrist 哈希键
_Z = {}


def _init_zobrist():
    if _Z:
        return
    rnd = random.Random(20261123)
    for r in range(ROWS):
        for c in range(COLS):
            for k in 'KABNRCP':
                for col in (RED, BLACK):
                    _Z[(r, c, k, col)] = rnd.getrandbits(64)
    _Z['side'] = rnd.getrandbits(64)


_init_zobrist()


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def opposite(color):
    return BLACK if color == RED else RED


def in_board(r, c):
    return 0 <= r < ROWS and 0 <= c < COLS


def in_palace(r, c, color):
    """九宫：红方 7-9 行，黑方 0-2 行，列固定 3-5。"""
    if not (3 <= c <= 5):
        return False
    return 7 <= r <= 9 if color == RED else 0 <= r <= 2


def own_half(r, color):
    """象士的活动范围（不可过河）。"""
    return r >= 5 if color == RED else r <= 4


def crossed_river(r, color):
    """兵/卒是否已过河。"""
    return r <= 4 if color == RED else r >= 5


class Piece:
    __slots__ = ('kind', 'color')

    def __init__(self, kind, color):
        self.kind = kind
        self.color = color

    def copy(self):
        return Piece(self.kind, self.color)

    def char(self):
        return CHARS[self.color][self.kind]

    def __repr__(self):
        return '<%s%s>' % (self.color, self.kind)


# ---------------------------------------------------------------------------
# 局面
# ---------------------------------------------------------------------------
class GameState:
    """棋局状态。所有搜索操作通过 do_move / undo_move 原地完成。"""

    def __init__(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.turn = RED
        self.king_pos = {RED: (9, 4), BLACK: (0, 4)}
        self.hash = 0
        self.history = []          # [(move, captured, turn, hash, halfmoves), ...]
        self.halfmoves = 0
        self.pos_counts = {}
        self.setup()

    # -- 初始化 ------------------------------------------------------------
    def setup(self):
        back = 'RNBAKABNR'
        for i, k in enumerate(back):
            self.board[0][i] = Piece(k, BLACK)
            self.board[9][i] = Piece(k, RED)
        # 炮：双方第 3 行的第 2、8 个纵线
        self.board[2][1] = Piece('C', BLACK)
        self.board[2][7] = Piece('C', BLACK)
        self.board[7][1] = Piece('C', RED)
        self.board[7][7] = Piece('C', RED)
        # 兵 / 卒
        for i in range(0, COLS, 2):
            self.board[3][i] = Piece('P', BLACK)
            self.board[6][i] = Piece('P', RED)
        self.turn = RED
        self.history = []
        self.halfmoves = 0
        self.king_pos = {RED: (9, 4), BLACK: (0, 4)}
        self._recompute_hash()
        self.pos_counts = {self.hash: 1}

    def copy(self):
        s = GameState.__new__(GameState)
        s.board = [[(p.copy() if p is not None else None) for p in row] for row in self.board]
        s.turn = self.turn
        s.king_pos = dict(self.king_pos)
        s.hash = self.hash
        s.history = []
        s.halfmoves = self.halfmoves
        s.pos_counts = dict(self.pos_counts)
        return s

    def _recompute_hash(self):
        h = 0
        for r in range(ROWS):
            for c in range(COLS):
                p = self.board[r][c]
                if p is not None:
                    h ^= _Z[(r, c, p.kind, p.color)]
        if self.turn == BLACK:
            h ^= _Z['side']
        self.hash = h

    # -- 走子 --------------------------------------------------------------
    def do_move(self, move):
        """执行一步棋，返回被吃掉的棋子（没有则返回 None）。"""
        fr, fc, tr, tc = move
        piece = self.board[fr][fc]
        captured = self.board[tr][tc]
        turn_before = self.turn
        hash_before = self.hash
        halfmoves_before = self.halfmoves

        if captured is not None:
            self.hash ^= _Z[(tr, tc, captured.kind, captured.color)]
        self.hash ^= _Z[(fr, fc, piece.kind, piece.color)]
        self.hash ^= _Z[(tr, tc, piece.kind, piece.color)]

        self.board[fr][fc] = None
        self.board[tr][tc] = piece
        if piece.kind == 'K':
            self.king_pos[piece.color] = (tr, tc)

        self.turn = opposite(self.turn)
        self.hash ^= _Z['side']
        self.halfmoves = 0 if captured is not None else self.halfmoves + 1

        self.history.append((move, captured, turn_before, hash_before, halfmoves_before))
        self.pos_counts[self.hash] = self.pos_counts.get(self.hash, 0) + 1
        return captured

    def undo_move(self):
        """撤销一步棋，返回被撤销的走法。"""
        if not self.history:
            return None
        move, captured, turn_before, hash_before, halfmoves_before = self.history.pop()
        fr, fc, tr, tc = move
        piece = self.board[tr][tc]
        self.board[fr][fc] = piece
        self.board[tr][tc] = captured
        if piece.kind == 'K':
            self.king_pos[piece.color] = (fr, fc)

        # 离开的那个局面计数减一
        cnt = self.pos_counts.get(self.hash, 0) - 1
        if cnt <= 0:
            self.pos_counts.pop(self.hash, None)
        else:
            self.pos_counts[self.hash] = cnt

        self.turn = turn_before
        self.hash = hash_before
        self.halfmoves = halfmoves_before
        return move

    # -- 查询 --------------------------------------------------------------
    def in_check(self, color):
        kp = self.king_pos.get(color)
        if kp is None:
            return True
        return is_attacked(self, kp[0], kp[1], opposite(color))

    def repetition_count(self):
        return self.pos_counts.get(self.hash, 0)

    def is_draw(self):
        """三次重复局面 或 60 回合（120 半步）无吃子 判和。"""
        if self.repetition_count() >= 3:
            return True
        if self.halfmoves >= 120:
            return True
        return False


# ---------------------------------------------------------------------------
# 走法生成
# ---------------------------------------------------------------------------
def _can_land(state, tr, tc, color):
    """目标格是否可落子。"""
    t = state.board[tr][tc]
    if t is None:
        return True
    if t.color == color:
        return False
    if t.kind == 'K':
        # 不直接吃将，胜负由将死判定
        return False
    return True


def piece_moves(state, r, c):
    """生成单枚棋子的走法（不含自陷将军检查）。"""
    p = state.board[r][c]
    kind, color = p.kind, p.color
    out = []

    if kind == 'K':
        for dr, dc in ORTHO:
            tr, tc = r + dr, c + dc
            if in_palace(tr, tc, color) and _can_land(state, tr, tc, color):
                out.append((r, c, tr, tc))

    elif kind == 'A':
        for dr, dc in DIAG:
            tr, tc = r + dr, c + dc
            if in_palace(tr, tc, color) and _can_land(state, tr, tc, color):
                out.append((r, c, tr, tc))

    elif kind == 'B':
        for dr, dc in DIAG:
            tr, tc = r + 2 * dr, c + 2 * dc
            if not in_board(tr, tc):
                continue
            if not own_half(tr, color):      # 象不可过河
                continue
            if state.board[r + dr][c + dc] is not None:   # 塞象眼
                continue
            if _can_land(state, tr, tc, color):
                out.append((r, c, tr, tc))

    elif kind == 'N':
        for dr, dc in HORSE:
            tr, tc = r + dr, c + dc
            if not in_board(tr, tc):
                continue
            if abs(dr) == 2:
                lr, lc = r + dr // 2, c
            else:
                lr, lc = r, c + dc // 2
            if state.board[lr][lc] is not None:             # 蹩马腿
                continue
            if _can_land(state, tr, tc, color):
                out.append((r, c, tr, tc))

    elif kind == 'R':
        for dr, dc in ORTHO:
            tr, tc = r + dr, c + dc
            while in_board(tr, tc):
                if state.board[tr][tc] is None:
                    out.append((r, c, tr, tc))
                else:
                    if _can_land(state, tr, tc, color):
                        out.append((r, c, tr, tc))
                    break
                tr += dr
                tc += dc

    elif kind == 'C':
        for dr, dc in ORTHO:
            tr, tc = r + dr, c + dc
            # 第一段：空位，可任意移动（不吃子）
            while in_board(tr, tc) and state.board[tr][tc] is None:
                out.append((r, c, tr, tc))
                tr += dr
                tc += dc
            if not in_board(tr, tc):
                continue
            # 跳过炮架
            tr += dr
            tc += dc
            while in_board(tr, tc) and state.board[tr][tc] is None:
                tr += dr
                tc += dc
            # 第二段：越过炮架后的第一个棋子
            if in_board(tr, tc) and _can_land(state, tr, tc, color):
                out.append((r, c, tr, tc))

    elif kind == 'P':
        step = -1 if color == RED else 1
        tr, tc = r + step, c
        if in_board(tr, tc) and _can_land(state, tr, tc, color):
            out.append((r, c, tr, tc))
        if crossed_river(r, color):          # 过河后可横走，仍不可后退
            for dc in (-1, 1):
                tc = c + dc
                if in_board(r, tc) and _can_land(state, r, tc, color):
                    out.append((r, c, r, tc))

    return out


def pseudo_moves(state, color):
    """生成全部伪合法走法。"""
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            p = state.board[r][c]
            if p is not None and p.color == color:
                out.extend(piece_moves(state, r, c))
    return out


def is_legal(state, move):
    """走法是否合法（走后己方不被将军）。"""
    mover = state.turn
    state.do_move(move)
    ok = not state.in_check(mover)
    state.undo_move()
    return ok


def legal_moves(state, color=None):
    """生成全部合法走法。"""
    if color is None:
        color = state.turn
    out = []
    for mv in pseudo_moves(state, color):
        state.do_move(mv)
        ok = not state.in_check(color)
        state.undo_move()
        if ok:
            out.append(mv)
    return out


def capture_moves(state, color):
    """仅生成吃子走法（用于静态搜索）。"""
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            p = state.board[r][c]
            if p is not None and p.color == color:
                for mv in piece_moves(state, r, c):
                    if state.board[mv[2]][mv[3]] is not None:
                        out.append(mv)
    return out


# ---------------------------------------------------------------------------
# 攻击判定
# ---------------------------------------------------------------------------
def is_attacked(state, r, c, by_color):
    """格 (r,c) 是否被 by_color 一方攻击。"""
    # 1. 兵 / 卒
    if by_color == RED:
        if r + 1 < ROWS:
            p = state.board[r + 1][c]
            if p is not None and p.color == RED and p.kind == 'P':
                return True
        if r <= 4:
            for cc in (c - 1, c + 1):
                if 0 <= cc < COLS:
                    p = state.board[r][cc]
                    if p is not None and p.color == RED and p.kind == 'P':
                        return True
    else:
        if r - 1 >= 0:
            p = state.board[r - 1][c]
            if p is not None and p.color == BLACK and p.kind == 'P':
                return True
        if r >= 5:
            for cc in (c - 1, c + 1):
                if 0 <= cc < COLS:
                    p = state.board[r][cc]
                    if p is not None and p.color == BLACK and p.kind == 'P':
                        return True

    # 2. 将 / 帅（相邻）
    for dr, dc in ORTHO:
        rr, cc = r + dr, c + dc
        if in_board(rr, cc):
            p = state.board[rr][cc]
            if p is not None and p.color == by_color and p.kind == 'K':
                return True

    # 3. 仕 / 士（斜邻）
    for dr, dc in DIAG:
        rr, cc = r + dr, c + dc
        if in_board(rr, cc):
            p = state.board[rr][cc]
            if p is not None and p.color == by_color and p.kind == 'A':
                return True

    # 4. 相 / 象（2 步斜，需无塞象眼）
    for dr in (-2, 2):
        for dc in (-2, 2):
            rr, cc = r + dr, c + dc
            if not in_board(rr, cc):
                continue
            p = state.board[rr][cc]
            if p is None or p.color != by_color or p.kind != 'B':
                continue
            if state.board[r + dr // 2][c + dc // 2] is None:
                return True

    # 5. 马（需无蹩马腿）
    for dr, dc in HORSE:
        rr, cc = r + dr, c + dc
        if not in_board(rr, cc):
            continue
        p = state.board[rr][cc]
        if p is None or p.color != by_color or p.kind != 'N':
            continue
        if abs(dr) == 2:
            lr, lc = rr + dr // 2, cc
        else:
            lr, lc = rr, cc + dc // 2
        if state.board[lr][lc] is None:
            return True

    # 6. 车 / 炮 / 飞将（四方向扫描）
    for dr, dc in ORTHO:
        rr, cc = r + dr, c + dc
        first = None
        while in_board(rr, cc):
            p = state.board[rr][cc]
            if p is not None:
                first = p
                break
            rr += dr
            cc += dc
        if first is None:
            continue
        if first.color == by_color:
            if first.kind == 'R':
                return True
            if first.kind == 'K' and dc == 0:
                # 飞将：同一纵线中间无子
                return True
        # 炮：需要恰好一个炮架
        rr2, cc2 = rr + dr, cc + dc
        second = None
        while in_board(rr2, cc2):
            p = state.board[rr2][cc2]
            if p is not None:
                second = p
                break
            rr2 += dr
            cc2 += dc
        if second is not None and second.color == by_color and second.kind == 'C':
            return True

    return False


# ---------------------------------------------------------------------------
# 中文着法记谱
# ---------------------------------------------------------------------------
def file_label(col, color):
    """纵线编号：红方从右向左用汉字一~九，黑方从右向左用阿拉伯 1~9。"""
    if color == RED:
        return CN_NUM[COLS - 1 - col]
    return str(col + 1)


def _piece_prefix(state, fr, fc, color, kind):
    """同列存在多个同类棋子时，用 前/中/后 区分。"""
    same = []
    for r in range(ROWS):
        p = state.board[r][fc]
        if p is not None and p.color == color and p.kind == kind:
            same.append(r)
    if len(same) <= 1:
        return ''
    same.sort(reverse=(color == BLACK))
    idx = same.index(fr)
    if len(same) == 2:
        return '前' if idx == 0 else '后'
    if len(same) == 3:
        return ('前', '中', '后')[idx]
    if idx == 0:
        return '前'
    if idx == len(same) - 1:
        return '后'
    return '中'


def move_notation(state, move):
    """
    生成中文着法记谱。

    格式：棋种[前/后/中][起始纵线]进/退/平[目标]
        · 平：目标写纵线编号，        例 炮二平五
        · 车炮兵将 进/退：写移动行数，例 兵七进一
        · 马象仕 进/退：写目标纵线，  例 马二进三
    """
    fr, fc, tr, tc = move
    piece = state.board[fr][fc]
    if piece is None:
        return ''
    kind, color = piece.kind, piece.color
    name = piece.char()

    prefix = _piece_prefix(state, fr, fc, color, kind)
    # 有 前/后/中 修饰时省略起始纵线，否则写明
    head = prefix + name if prefix else name + file_label(fc, color)

    if fr == tr:
        return '%s平%s' % (head, file_label(tc, color))

    forward = -1 if color == RED else 1
    word = '进' if (tr - fr) * forward > 0 else '退'
    if kind in ('N', 'B', 'A'):
        # 马/象/仕：写目标纵线
        target = file_label(tc, color)
    else:
        # 车/炮/兵/将：写移动行数
        steps = abs(tr - fr)
        target = CN_NUM[steps - 1] if color == RED else str(steps)
    return '%s%s%s' % (head, word, target)


# ---------------------------------------------------------------------------
# 静态评估
# ---------------------------------------------------------------------------
def piece_attacks(state, r, c, tr, tc):
    """位于 (r,c) 的棋子是否攻击 (tr,tc)。用于评估函数统计攻子力量。"""
    p = state.board[r][c]
    if p is None:
        return False
    dr = tc - r
    dc = tc - c
    kind = p.kind

    if kind == 'R':
        if dr != 0 and dc != 0:
            return False
        step_r = 1 if dr > 0 else (-1 if dr < 0 else 0)
        step_c = 1 if dc > 0 else (-1 if dc < 0 else 0)
        rr, cc = r + step_r, c + step_c
        while (rr, cc) != (tr, tc):
            if not in_board(rr, cc) or state.board[rr][cc] is not None:
                return False
            rr += step_r
            cc += step_c
        return True

    if kind == 'C':
        if dr != 0 and dc != 0:
            return False
        step_r = 1 if dr > 0 else (-1 if dr < 0 else 0)
        step_c = 1 if dc > 0 else (-1 if dc < 0 else 0)
        rr, cc = r + step_r, c + step_c
        screen = False
        while (rr, cc) != (tr, tc):
            if not in_board(rr, cc):
                return False
            if state.board[rr][cc] is not None:
                if screen:
                    return False
                screen = True
            rr += step_r
            cc += step_c
        return screen

    if kind == 'N':
        if abs(dr) == 2 and abs(dc) == 1:
            leg = (r + dr // 2, c)
        elif abs(dr) == 1 and abs(dc) == 2:
            leg = (r, c + dc // 2)
        else:
            return False
        return state.board[leg[0]][leg[1]] is None

    if kind == 'B':
        if abs(dr) != 2 or abs(dc) != 2:
            return False
        return state.board[r + dr // 2][c + dc // 2] is None

    if kind == 'A':
        return abs(dr) == 1 and abs(dc) == 1

    if kind == 'K':
        if abs(dr) + abs(dc) != 1:
            return False
        # 飞将
        if dc == 0:
            step = 1 if dr > 0 else -1
            rr = r + step
            while rr != tr:
                if state.board[rr][c] is not None:
                    return False
                rr += step
        return True

    if kind == 'P':
        step = -1 if p.color == RED else 1
        if dr == step and dc == 0:
            return True
        if crossed_river(r, p.color) and dr == 0 and abs(dc) == 1:
            return True
        return False

    return False


def _king_attackers(state, color):
    """统计 color 一方有多少棋子攻击对方将/帅。"""
    kp = state.king_pos.get(opposite(color))
    if kp is None:
        return 0
    n = 0
    for r in range(ROWS):
        for c in range(COLS):
            p = state.board[r][c]
            if p is not None and p.color == color and piece_attacks(state, r, c, kp[0], kp[1]):
                n += 1
    return n


def piece_value(p, r, c):
    kind = p.kind
    v = VALUE[kind]
    if kind == 'P':
        if crossed_river(r, p.color):
            v = 180
            if (p.color == RED and r <= 2) or (p.color == BLACK and r >= 7):
                v += 20
        else:
            v = 100
    elif kind == 'N':
        v += (4 - abs(c - 4)) * 10
    elif kind == 'C':
        v += (4 - abs(c - 4)) * 6
    elif kind == 'R':
        v += (4 - abs(c - 4)) * 5
    elif kind in ('A', 'B'):
        v += 15
    return v


def evaluate(state):
    """局面评估，返回值以当前走子方为正。"""
    raw = 0
    for r in range(ROWS):
        for c in range(COLS):
            p = state.board[r][c]
            if p is None:
                continue
            v = piece_value(p, r, c)
            raw += v if p.color == RED else -v

    # 攻守：将受到的攻击数量
    raw += 25 * (_king_attackers(state, RED) - _king_attackers(state, BLACK))
    # 将军
    if state.in_check(BLACK):
        raw += 40
    if state.in_check(RED):
        raw -= 40

    if state.turn == RED:
        return raw
    return -raw


# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------
class _Timeout(Exception):
    pass


def _order_moves(state, moves, killers=None):
    """走法排序：吃子优先（MVV-LVA），其次杀手着法。"""
    scored = []
    for mv in moves:
        fr, fc, tr, tc = mv
        victim = state.board[tr][tc]
        score = 0
        if victim is not None:
            score = 10000 + VALUE[victim.kind] * 12 - VALUE[state.board[fr][fc].kind]
        if killers and mv in killers:
            score += 9000
        scored.append((-score, mv))
    scored.sort(key=lambda x: x[0])
    return [mv for _, mv in scored]


def _quiesce(state, alpha, beta, deadline):
    if time.time() > deadline:
        raise _Timeout
    stand = evaluate(state)
    if stand >= beta:
        return beta
    if stand > alpha:
        alpha = stand

    caps = capture_moves(state, state.turn)
    for mv in _order_moves(state, caps):
        state.do_move(mv)
        try:
            score = -_quiesce(state, -beta, -alpha, deadline)
        finally:
            state.undo_move()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def _negamax(state, depth, alpha, beta, deadline, killers):
    if time.time() > deadline:
        raise _Timeout
    if state.repetition_count() >= 3:
        return 0                      # 同一局面第三次出现，判和
    if depth <= 0:
        return _quiesce(state, alpha, beta, deadline)

    moves = legal_moves(state, state.turn)
    if not moves:
        # 将死或困毙均为负
        return -MATE

    moves = _order_moves(state, moves, killers)
    best = -INF
    for mv in moves:
        state.do_move(mv)
        try:
            score = -_negamax(state, depth - 1, -beta, -alpha, deadline, killers)
            if state.repetition_count() >= 2:
                # 这一手把局面走到了之前出现过的局面，扣分避免来回重复
                score -= REP_PENALTY
        finally:
            state.undo_move()
        if score > best:
            best = score
            if score > alpha:
                alpha = score
            if alpha >= beta:
                break
    return best


def _result_hashes(state, moves):
    """算出每个走法走完之后的新局面哈希。"""
    out = []
    for mv in moves:
        state.do_move(mv)
        out.append(state.hash)
        state.undo_move()
    return out


def filter_repetition_moves(state, moves):
    """
    过滤掉会让局面重复的走法。

    AI 老是「这步走完、下步又退回来」就是这个原因：它走到了之前出现过的局面。
    这里只保留能走到全新局面的走法；如果所有走法都会重复，则优先选能吃子的。
    """
    if not moves or not state.pos_counts:
        return moves
    fresh = []
    for mv, h in zip(moves, _result_hashes(state, moves)):
        if h not in state.pos_counts:
            fresh.append(mv)
    if fresh:
        return fresh
    caps = [mv for mv in moves if state.board[mv[2]][mv[3]] is not None]
    return caps or moves


def best_move(state, depth=4, time_limit=2.0, avoid_repetition=True, forbid=None):
    """
    搜索最佳走法。返回 (fr,fc,tr,tc) 或 None。

    avoid_repetition : 避开会让局面重复的走法，防止 AI 来回走同一手
    forbid           : 指定不要走的一手（悔棋后让 AI 换个走法）
    """
    deadline = time.time() + time_limit
    moves = legal_moves(state, state.turn)
    if not moves:
        return None

    if forbid is not None:
        rest = [mv for mv in moves if tuple(mv) != tuple(forbid)]
        if rest:
            moves = rest
    if avoid_repetition:
        moves = filter_repetition_moves(state, moves)
    best = moves[0]
    try:
        for d in range(1, depth + 1):
            alpha = -INF
            scored = []
            for mv in _order_moves(state, moves):
                state.do_move(mv)
                try:
                    if alpha == -INF:
                        score = -_negamax(state, d - 1, -INF, INF, deadline, [])
                    else:
                        score = -_negamax(state, d - 1, -INF, -alpha, deadline, [])
                        if score > alpha:
                            # 复搜一次拿到准确分数，免得被剪枝的假分数带偏
                            score = -_negamax(state, d - 1, -INF, INF, deadline, [])
                    if score > alpha:
                        alpha = score
                finally:
                    state.undo_move()
                scored.append((score, mv))
                if time.time() > deadline:
                    raise _Timeout
            # 只有完整搜索完一层才采用该层结果
            scored.sort(key=lambda x: -x[0])
            moves = [mv for _, mv in scored]
            best = moves[0]
            if alpha >= MATE - 100:
                break
    except _Timeout:
        pass
    except RecursionError:
        pass
    return best


# ---------------------------------------------------------------------------
# 对局结果
# ---------------------------------------------------------------------------
def game_result(state):
    """
    返回 (状态, 说明)
        状态: 'playing' / 'red_win' / 'black_win' / 'draw'
    """
    if not legal_moves(state, state.turn):
        loser = state.turn
        if state.in_check(loser):
            msg = '%s被将死，%s胜' % ('红方' if loser == RED else '黑方',
                                     '黑方' if loser == RED else '红方')
        else:
            msg = '%s无子可动（困毙），%s胜' % ('红方' if loser == RED else '黑方',
                                            '黑方' if loser == RED else '红方')
        return ('black_win' if loser == RED else 'red_win'), msg
    if state.is_draw():
        return 'draw', '和棋（局面重复或久未吃子）'
    return 'playing', ''
