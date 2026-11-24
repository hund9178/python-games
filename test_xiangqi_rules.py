# -*- coding: utf-8 -*-
"""象棋规则引擎测试。输出写入 UTF-8 文件，避免控制台编码问题。"""

import io
import os
import random
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xiangqi_rules import (RED, BLACK, GameState, legal_moves, pseudo_moves,
                           piece_moves, move_notation, best_move, game_result,
                           filter_repetition_moves, Piece)

out = io.StringIO()
fails = []


def check(name, cond, detail=''):
    out.write('%s %s%s\n' % ('[PASS]' if cond else '[FAIL]', name,
                            ('  -> ' + detail) if (detail and not cond) else ''))
    if not cond:
        fails.append(name)


def find_moves(state, r, c):
    return set((m[2], m[3]) for m in piece_moves(state, r, c))


def clear_board(state):
    for r in range(10):
        for c in range(9):
            state.board[r][c] = None
    state.king_pos = {RED: None, BLACK: None}
    state._recompute_hash()


def place(state, r, c, kind, color):
    state.board[r][c] = Piece(kind, color)
    if kind == 'K':
        state.king_pos[color] = (r, c)
    state._recompute_hash()


# --- 1. 初始局面 -----------------------------------------------------------
st = GameState()
check('初始棋子数量 32', sum(1 for r in range(10) for c in range(9) if st.board[r][c]) == 32)
check('初始红方走棋', st.turn == RED)
check('初始红帅在 (9,4)', st.king_pos[RED] == (9, 4))
check('初始黑将在 (0,4)', st.king_pos[BLACK] == (0, 4))
check('炮位置正确', st.board[2][1] and st.board[2][7] and st.board[7][1] and st.board[7][7])
lm = legal_moves(st, RED)
check('初始红方合法走法数 44', len(lm) == 44, '实际 %d' % len(lm))
lm_b = legal_moves(st, BLACK)
check('初始黑方合法走法数 44', len(lm_b) == 44, '实际 %d' % len(lm_b))

# --- 2. 蹩马腿 -------------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 4, 'N', RED)
place(st, 5, 3, 'P', BLACK)     # 蹩住朝左的马腿
mv = find_moves(st, 5, 4)
check('蹩马腿: 马不能走到 (4,2)', (4, 2) not in mv, str(sorted(mv)))
check('蹩马腿: 马不能走到 (6,2)', (6, 2) not in mv, str(sorted(mv)))
check('蹩马腿: 马可走 (4,6)', (4, 6) in mv, str(sorted(mv)))
check('蹩马腿: 马可走 (6,6)', (6, 6) in mv, str(sorted(mv)))
check('蹩马腿: 马共 6 个走法', len(mv) == 6, str(sorted(mv)))

# --- 3. 塞象眼 -------------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 7, 2, 'B', RED)      # 相
place(st, 6, 3, 'P', BLACK)    # 塞象眼
mv = find_moves(st, 7, 2)
check('塞象眼: 相不能走到 (5,4)', (5, 4) not in mv, str(sorted(mv)))
check('塞象眼: 相可走到 (5,0)', (5, 0) in mv, str(sorted(mv)))
check('塞象眼: 相可走到 (9,0)', (9, 0) in mv, str(sorted(mv)))

# --- 4. 象不可过河 ---------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 2, 'B', RED)      # 位于河界
mv = find_moves(st, 5, 2)
check('象不可过河: (3,0)/(3,4) 不可达',
      (3, 0) not in mv and (3, 4) not in mv, str(sorted(mv)))

# --- 5. 炮需炮架 -----------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 9, 1, 'C', RED)
place(st, 7, 1, 'P', BLACK)    # 炮架
place(st, 5, 1, 'P', BLACK)    # 目标
mv = find_moves(st, 9, 1)
check('炮: 隔一子可吃 (5,1)', (5, 1) in mv, str(sorted(mv)))
check('炮: 不可直接吃炮架 (7,1)', (7, 1) not in mv, str(sorted(mv)))
check('炮: 可移动到空位 (8,1)', (8, 1) in mv, str(sorted(mv)))

st2 = GameState()
clear_board(st2)
place(st2, 9, 4, 'K', RED)
place(st2, 0, 4, 'K', BLACK)
place(st2, 9, 1, 'C', RED)
place(st2, 7, 1, 'P', BLACK)
place(st2, 6, 1, 'P', BLACK)   # 两个炮架
place(st2, 5, 1, 'P', BLACK)
mv2 = find_moves(st2, 9, 1)
check('炮: 两个炮架则不可吃 (5,1)', (5, 1) not in mv2, str(sorted(mv2)))

# --- 6. 兵/卒规则 ----------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 6, 4, 'P', RED)
mv = find_moves(st, 6, 4)
check('兵未过河: 只能直进 (5,4)', mv == {(5, 4)}, str(sorted(mv)))

st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 4, 4, 'P', RED)
mv = find_moves(st, 4, 4)
check('兵过河: 可直进 (3,4)', (3, 4) in mv, str(sorted(mv)))
check('兵过河: 可横走 (4,3)', (4, 3) in mv, str(sorted(mv)))
check('兵过河: 可横走 (4,5)', (4, 5) in mv, str(sorted(mv)))
check('兵不可后退: (5,4) 不在走法中', (5, 4) not in mv, str(sorted(mv)))

st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 3, 4, 'P', BLACK)
mv = find_moves(st, 3, 4)
check('卒未过河: 只能直进 (4,4)', mv == {(4, 4)}, str(sorted(mv)))

st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 7, 4, 'P', BLACK)    # 已过河
mv = find_moves(st, 7, 4)
check('卒过河: 可横走 (7,3)', (7, 3) in mv, str(sorted(mv)))
check('卒过河: 可横走 (7,5)', (7, 5) in mv, str(sorted(mv)))
check('卒不可后退: (6,4) 不在走法中', (6, 4) not in mv, str(sorted(mv)))

# --- 7. 将帅限九宫 ---------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
mv = find_moves(st, 9, 4)
check('帅在九宫: 可走 (8,4)', (8, 4) in mv, str(sorted(mv)))
check('帅在九宫: 可走 (9,3)', (9, 3) in mv, str(sorted(mv)))
check('帅不能出宫 (9,2)', (9, 2) not in mv, str(sorted(mv)))
check('帅不能出宫 (8,5)', (8, 5) not in mv, str(sorted(mv)))

# --- 8. 飞将（照面）-------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
check('飞将: 红帅被攻击', st.in_check(RED))
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 4, 'R', RED)
check('飞将: 有子阻隔则不被攻击', not st.in_check(RED))

# --- 9. 攻击判定 -----------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 0, 'R', BLACK)
check('车横线攻击: 红帅被攻击', st.in_check(RED))
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 0, 'C', BLACK)
place(st, 7, 0, 'R', RED)
check('炮隔一子攻击: 红帅被攻击', st.in_check(RED))
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 7, 6, 'N', BLACK)
check('马攻击: 红帅被攻击', st.in_check(RED))

# --- 10. 不可自陷将军 ------------------------------------------------------
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 4, 'R', BLACK)
place(st, 7, 4, 'R', RED)
lmv = set(legal_moves(st, RED))
check('不可自陷: 红车不能横移离开 (7,4)',
      (7, 4, 7, 3) not in lmv and (7, 4, 7, 5) not in lmv, str(sorted(lmv)))
check('可换: 红车仍可沿纵线走 (6,4)', (7, 4, 6, 4) in lmv, str(sorted(lmv)))
check('伪合法 >= 合法', len(pseudo_moves(st, RED)) >= len(lmv),
      'pseudo=%d legal=%d' % (len(pseudo_moves(st, RED)), len(lmv)))

# 将军着法必须保留在合法走法中
st = GameState()
lmv = set(legal_moves(st, RED))
check('将军着法被保留: 炮八平五', (7, 1, 7, 4) in lmv, str(sorted(lmv)))

# --- 11. 将死检测 ----------------------------------------------------------
# 黑将 (0,4)；红车 (0,0) 封锁底线，红车 (2,4) 封锁 (1,4)
st = GameState()
clear_board(st)
place(st, 0, 4, 'K', BLACK)
place(st, 9, 4, 'K', RED)
place(st, 0, 0, 'R', RED)
place(st, 2, 4, 'R', RED)
st.turn = BLACK
check('将死局面: 黑方已被将军', st.in_check(BLACK))
res, msg = game_result(st)
check('将死: 黑方被判负', res == 'red_win', '%s / %s' % (res, msg))
out.write('将死提示: %s\n' % msg)

# --- 12. 困毙（无棋可走但未被将军）-----------------------------------------
# 黑将 (0,4) 独自无子可动；红马 (2,2) 封 (0,3)/(1,4)，红马 (2,6) 封 (0,5)/(1,4)。
# 红帅放在 (9,3) 而非 (9,4)，避免与黑将同列造成飞将。
st = GameState()
clear_board(st)
place(st, 0, 4, 'K', BLACK)
place(st, 9, 3, 'K', RED)
place(st, 2, 2, 'N', RED)      # 封 (0,3) 与 (1,4)
place(st, 2, 6, 'N', RED)      # 封 (0,5) 与 (1,4)
st.turn = BLACK
check('困毙局面: 黑方未被将军', not st.in_check(BLACK))
res2, msg2 = game_result(st)
check('困毙: 同样判负', res2 == 'red_win', '%s / %s' % (res2, msg2))
out.write('困毙提示: %s\n' % msg2)

# --- 13. 中文记谱 ----------------------------------------------------------
st = GameState()
check('记谱 炮二平五', move_notation(st, (7, 7, 7, 4)) == '炮二平五',
      move_notation(st, (7, 7, 7, 4)))
check('记谱 炮八平五', move_notation(st, (7, 1, 7, 4)) == '炮八平五',
      move_notation(st, (7, 1, 7, 4)))
check('记谱 马二进三', move_notation(st, (9, 7, 7, 6)) == '马二进三',
      move_notation(st, (9, 7, 7, 6)))
check('记谱 车九平八', move_notation(st, (9, 0, 9, 1)) == '车九平八',
      move_notation(st, (9, 0, 9, 1)))
check('记谱 兵七进一', move_notation(st, (6, 2, 5, 2)) == '兵七进一',
      move_notation(st, (6, 2, 5, 2)))
check('记谱 兵三进一', move_notation(st, (6, 6, 5, 6)) == '兵三进一',
      move_notation(st, (6, 6, 5, 6)))
check('记谱 黑卒 1 进 1', move_notation(st, (3, 0, 4, 0)) == '卒1进1',
      move_notation(st, (3, 0, 4, 0)))
check('记谱 黑车 1 平 2', move_notation(st, (0, 0, 0, 1)) == '车1平2',
      move_notation(st, (0, 0, 0, 1)))
check('记谱 黑马 8 进 7', move_notation(st, (0, 7, 2, 6)) == '马8进7',
      move_notation(st, (0, 7, 2, 6)))

# 同列双兵用前/后区分：构造两个红兵位于同一纵线
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 4, 1, 'P', RED)      # 前兵
place(st, 6, 1, 'P', RED)      # 后兵
check('记谱 前兵进一', move_notation(st, (4, 1, 3, 1)) == '前兵进一',
      move_notation(st, (4, 1, 3, 1)))
check('记谱 后兵进一', move_notation(st, (6, 1, 5, 1)) == '后兵进一',
      move_notation(st, (6, 1, 5, 1)))

# --- 14. 撤销走法完整性 ----------------------------------------------------
st = GameState()
before = [[(p.kind, p.color) if p else None for p in row] for row in st.board]
lm = legal_moves(st, RED)
st.do_move(lm[0])
st.undo_move()
after = [[(p.kind, p.color) if p else None for p in row] for row in st.board]
check('撤销后局面完全还原', before == after)
check('撤销后哈希还原', st.hash == GameState().hash)

# --- 15. AI 合法性 ---------------------------------------------------------
st = GameState()
t0 = time.time()
mv = best_move(st, depth=2, time_limit=3.0)
dt = time.time() - t0
legal = set(legal_moves(st, RED))
check('AI 返回合法走法', mv in legal, str(mv))
check('AI 搜索在时间限制内', dt < 8.0, '%.2fs' % dt)
out.write('AI depth2 用时 %.2fs, 走法=%s\n' % (dt, mv))

st = GameState()
t0 = time.time()
mv = best_move(st, depth=4, time_limit=5.0)
dt = time.time() - t0
check('AI depth4 返回合法走法', mv in set(legal_moves(st, RED)), str(mv))
check('AI depth4 用时合理', dt < 12.0, '%.2fs' % dt)
out.write('AI depth4 用时 %.2fs, 走法=%s\n' % (dt, mv))

# AI 必须能吃掉白送的车（红车 (5,0) 吃黑车 (5,4)）
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 0, 'R', RED)
place(st, 5, 4, 'R', BLACK)
st.turn = RED
mv = best_move(st, depth=2, time_limit=2.0)
check('AI 会吃子', mv is not None and mv[2] == 5 and mv[3] == 4, str(mv))

# AI 能找到将军（红车走到能将军黑将的位置）
st = GameState()
clear_board(st)
place(st, 9, 4, 'K', RED)
place(st, 0, 4, 'K', BLACK)
place(st, 5, 0, 'R', RED)
st.turn = RED
mv = best_move(st, depth=2, time_limit=2.0)
if mv:
    st.do_move(mv)
    check('AI 走子后局面合法', not st.in_check(RED))
    st.undo_move()

# --- 16. 完整对局不会崩溃 --------------------------------------------------
st = GameState()
random.seed(7)
plies = 0
while plies < 200:
    lm = legal_moves(st, st.turn)
    if not lm:
        break
    st.do_move(random.choice(lm))
    plies += 1
check('随机对局 200 手无异常', plies > 0, '%d 手' % plies)
out.write('随机对局 %d 手后结果: %s\n' % (plies, game_result(st)))

# AI 自对弈，检查全程无异常且终局合法
st = GameState()
plies = 0
while plies < 60:
    lm = legal_moves(st, st.turn)
    if not lm:
        break
    mv = best_move(st, depth=2, time_limit=1.0)
    if mv is None:
        break
    st.do_move(mv)
    plies += 1
res3, msg3 = game_result(st)
check('AI 自对弈全程无异常', res3 in ('playing', 'red_win', 'black_win', 'draw'),
      '%s' % (res3,))
check('AI 自对弈终局状态合法', st.in_check(st.turn) or res3 in ('red_win', 'black_win', 'draw'),
      '终局 %s' % (res3,))
out.write('AI 自对弈 %d 手后结果: %s %s\n' % (plies, res3, msg3))

# --- 17. AI 不会来回走重复的棋 --------------------------------------------
st = GameState()
for mv in ((7, 1, 7, 4), (2, 7, 2, 4), (7, 4, 7, 1), (2, 4, 2, 7)):
    st.do_move(mv)
before = dict(st.pos_counts)
mv = best_move(st.copy(), depth=3, time_limit=2.0)
st.do_move(mv)
check('AI 不会走到重复局面', st.hash not in before, '走法 %s' % (mv,))

st2 = GameState()
st2.do_move((7, 1, 7, 4))
st2.do_move((2, 7, 2, 4))
st2.do_move((7, 4, 7, 1))        # 红炮退回原位
fresh = filter_repetition_moves(st2, legal_moves(st2, st2.turn))
repeat = []
for m in fresh:
    seen = dict(st2.pos_counts)
    st2.do_move(m)
    repeat.append(st2.hash in seen)
    st2.undo_move()
check('过滤后没有重复走法', repeat and not any(repeat), str(repeat))

st3 = GameState()
first = best_move(st3.copy(), depth=3, time_limit=2.0)
second = best_move(st3.copy(), depth=3, time_limit=2.0, forbid=first)
check('悔棋后 AI 换招', second != first or len(legal_moves(st3)) == 1,
      '%s / %s' % (first, second))

st4 = GameState()
for _ in range(2):
    for mv in ((7, 1, 7, 4), (2, 7, 2, 4), (7, 4, 7, 1), (2, 4, 2, 7)):
        st4.do_move(mv)
res4, msg4 = game_result(st4)
check('三次重复局面判和', res4 == 'draw', '%s %s' % (res4, msg4))

out.write('\n总计失败: %d\n' % len(fails))
if fails:
    out.write('失败项: %s\n' % ', '.join(fails))

path = os.path.join(tempfile.gettempdir(), 'xiangqi_rules_report.txt')
with open(path, 'w', encoding='utf-8') as fh:
    fh.write(out.getvalue())
print('report written:', path, 'fails=', len(fails))
