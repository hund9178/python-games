# -*- coding: utf-8 -*-
"""象棋界面交互测试：无头模式驱动，输出截图到临时目录。"""

import os
import shutil
import sys
import tempfile
import time

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
import xiangqi
from xiangqi_rules import RED, BLACK, Piece, legal_moves

TMP = tempfile.gettempdir()
fails = []


def check(name, cond, detail=''):
    print('%s %s%s' % ('[PASS]' if cond else '[FAIL]', name,
                       ('  -> ' + detail) if (detail and not cond) else ''))
    if not cond:
        fails.append(name)


def setpos(app, placements, turn=RED):
    st = app.state
    st.board = [[None] * 9 for _ in range(10)]
    st.king_pos = {RED: None, BLACK: None}
    for (r, c, kind, color) in placements:
        st.board[r][c] = Piece(kind, color)
        if kind == 'K':
            st.king_pos[color] = (r, c)
    st.turn = turn
    st._recompute_hash()
    return st


app = xiangqi.XiangqiApp(fullscreen=False)
BX = app.board_x
BY = app.board_y

check('窗口尺寸', app.screen.get_size() == (660, 1000), str(app.screen.get_size()))
check('没有右侧栏', not hasattr(xiangqi, 'PANEL_X'))
check('大按钮 7 个', len(app.buttons) == 7, str(len(app.buttons)))
check('按钮尺寸够大', all(b['rect'].width >= 130 and b['rect'].height >= 54
                          for b in app.buttons))
check('初始 32 枚棋子',
      sum(1 for r in range(10) for c in range(9) if app.state.board[r][c]) == 32)
app.draw(); pygame.image.save(app.screen, os.path.join(TMP, 'xq_start.png'))

# --- 布局自适应 -----------------------------------------------------------
lay_big = xiangqi.Layout(1920, 1080)
check('全屏布局不超出屏幕',
      lay_big.frame_y + lay_big.frame_h <= 1080 and lay_big.frame_x >= 0,
      '%d %d' % (lay_big.frame_y, lay_big.frame_h))
check('全屏时格子变大', lay_big.cell > app.layout.cell,
      '%d vs %d' % (lay_big.cell, app.layout.cell))
lay_small = xiangqi.Layout(1366, 768)
check('小屏布局不超出屏幕',
      lay_small.frame_y + lay_small.frame_h <= 768,
      '%d %d' % (lay_small.frame_y, lay_small.frame_h))
check('小屏时格子缩小', lay_small.cell < lay_big.cell,
      '%d vs %d' % (lay_small.cell, lay_big.cell))

# --- 棋谱面板的位置（不能压住棋盘和按钮）---------------------------------
check('全屏：棋谱在棋盘下方',
      lay_big.rec.y >= lay_big.frame_y + lay_big.frame_h,
      '%d %d' % (lay_big.rec.y, lay_big.frame_y + lay_big.frame_h))
check('全屏：棋谱不遮第一排按钮', lay_big.rec.bottom <= lay_big.row1_y,
      '%d %d' % (lay_big.rec.bottom, lay_big.row1_y))
check('全屏：棋谱不出屏', lay_big.rec.bottom < 1080, str(lay_big.rec.bottom))
check('全屏：按钮不出屏', lay_big.row2_y + lay_big.btn_h2 <= 1080,
      str(lay_big.row2_y + lay_big.btn_h2))
check('小屏：棋谱不遮第一排按钮', lay_small.rec.bottom <= lay_small.row1_y,
      '%d %d' % (lay_small.rec.bottom, lay_small.row1_y))
check('小屏：按钮不出屏', lay_small.row2_y + lay_small.btn_h2 <= 768,
      str(lay_small.row2_y + lay_small.btn_h2))
check('窗口：棋谱不遮第一排按钮', app.layout.rec.bottom <= app.layout.row1_y,
      '%d %d' % (app.layout.rec.bottom, app.layout.row1_y))

# --- 双人模式：点击选中 -> 点击落子 ---------------------------------------
app.mode = 'pvp'
app.on_left_click((BX(1), BY(7)))          # 红炮 (7,1)
check('点击炮后被选中', app.selected == (7, 1), str(app.selected))
check('炮的可落点 12 个', len(app.legal_targets) == 12, str(len(app.legal_targets)))
app.on_left_click((BX(4), BY(7)))          # 平到中路
check('点击目标后完成走子', app.last_move == (7, 1, 7, 4), str(app.last_move))
check('走法已记录', app.history == [('炮八平五', RED, '')], str(app.history))
check('轮到黑方', app.state.turn == BLACK)

# --- 右键取消 -------------------------------------------------------------
app.on_left_click((BX(7), BY(2)))          # 黑炮 (2,7)，此时轮到黑方
check('选中黑炮', app.selected == (2, 7), str(app.selected))
pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(0, 0)))
for ev in pygame.event.get():
    app.handle_event(ev)
check('右键取消选择', app.selected is None, str(app.selected))

# --- 黑方也走一步 ---------------------------------------------------------
app.on_left_click((BX(7), BY(2)))          # 黑炮 (2,7)
app.on_left_click((BX(4), BY(2)))          # 平到中路
check('黑方走子', app.last_move == (2, 7, 2, 4), str(app.last_move))
check('记录两条着法', len(app.history) == 2, str(app.history))

# --- 悔棋（双人模式退一步）------------------------------------------------
app.undo()
check('双人悔棋后退回红方', app.state.turn == BLACK, str(app.state.turn))
check('双人悔棋后记录剩一条', len(app.history) == 1, str(app.history))

# --- 人机模式：AI 应手 + 悔棋两步 -----------------------------------------
app.mode = 'ai'
app.human_color = RED
app.new_game()
app.on_left_click((BX(1), BY(7)))
app.on_left_click((BX(4), BY(7)))
check('人机模式红方走子', app.last_move == (7, 1, 7, 4), str(app.last_move))

app.start_ai()
t0 = time.time()
while app.ai_pending and time.time() - t0 < 20:
    app.poll_ai()
    time.sleep(0.05)
check('AI 在 20 秒内落子',
      app.last_move is not None and app.last_move != (7, 1, 7, 4), str(app.last_move))
check('AI 落子后轮到红方', app.state.turn == RED, str(app.state.turn))
check('AI 落子有记录', len(app.history) == 2, str(app.history))

app.undo()
check('人机悔棋后回到红方', app.state.turn == RED, str(app.state.turn))
check('人机悔棋清空记录', len(app.history) == 0, str(app.history))
check('悔棋后记住 AI 上一步', app.ai_avoid is not None, str(app.ai_avoid))
check('人机悔棋后棋盘复原',
      sum(1 for r in range(10) for c in range(9) if app.state.board[r][c]) == 32)

# --- 提示 ----------------------------------------------------------------
app.request_hint()
t0 = time.time()
while app.hint_move is None and time.time() - t0 < 10:
    time.sleep(0.05)
check('提示功能给出着法', app.hint_move is not None, str(app.hint_move))

# --- 横幅提示文案 --------------------------------------------------------
check('横幅显示轮次', '你的回合' in app.turn_text() or '电脑回合' in app.turn_text(),
      app.turn_text())
check('横幅有副标题', bool(app.sub_text()), repr(app.sub_text()))
check('提示文字不超出画布', app.tip_surface().get_width() <= app.layout.w - 24,
      str(app.tip_surface().get_width()))
check('按钮都在画布内',
      all(b['rect'].right <= app.layout.w and b['rect'].bottom <= app.layout.h
          for b in app.buttons))

# --- 将军（黑方可以吃车，故不是绝杀）--------------------------------------
app.new_game()
app.mode = 'pvp'
setpos(app, [(0, 4, 'K', BLACK), (9, 3, 'K', RED), (2, 4, 'R', RED)], RED)
app.apply_move((2, 4, 1, 4))
check('检测到将军', app.status == '将军！', repr(app.status))
check('将军时黑方被将', app.state.in_check(BLACK))
check('将军后游戏继续', app.result is None, str(app.result))
app.draw(); pygame.image.save(app.screen, os.path.join(TMP, 'xq_check.png'))

# --- 将死 ----------------------------------------------------------------
app.new_game()
app.mode = 'pvp'
setpos(app, [(0, 4, 'K', BLACK), (9, 4, 'K', RED), (0, 0, 'R', RED),
              (2, 5, 'R', RED)], RED)
app.apply_move((2, 5, 2, 4))
check('检测到将死', app.result is not None and app.result[0] == 'red_win', str(app.result))
check('将死提示文案', app.status and '将死' in app.status, repr(app.status))
app.draw(); pygame.image.save(app.screen, os.path.join(TMP, 'xq_end.png'))

# --- 按钮 ----------------------------------------------------------------
app.new_game()
app.mode = 'ai'
app.on_button('level')
check('难度切换', app.difficulty == 1)
check('难度按钮文案更新', app.button_label('level', '') == '难度：简单',
      app.button_label('level', ''))
app.on_button('mode')
check('模式切换', app.mode == 'pvp')
check('模式按钮文案更新', app.button_label('mode', '') == '对战：双人',
      app.button_label('mode', ''))
app.on_button('sound')
check('音效切换', app.sounds.enabled is False)
check('音效按钮文案更新', app.button_label('sound', '') == '音效：关',
      app.button_label('sound', ''))
app.on_button('new')
check('新局重置', app.state.turn == RED and len(app.history) == 0)

# --- 全屏切换（用桩函数代替真实的 set_mode）------------------------------
saved_display = app.apply_display
app.apply_display = lambda: app.set_layout((1920, 1080))
app.on_button('full')
check('全屏按钮切换', app.fullscreen is True)
check('全屏后布局放大', app.layout.cell > lay_small.cell,
      str(app.layout.cell))
check('全屏按钮文案更新', app.button_label('full', '') == '全屏：开',
      app.button_label('full', ''))
app.on_button('full')
check('再点一次退出全屏', app.fullscreen is False)
app.apply_display = saved_display
app.set_layout(app.screen.get_size())

# --- 按钮点击（模拟真实鼠标）--------------------------------------------
btn = [b for b in app.buttons if b['id'] == 'undo'][0]
app.on_left_click(btn['rect'].center)
check('点击悔棋按钮不报错', app.state.turn == RED)

# --- 棋谱记录面板 ---------------------------------------------------------
app.new_game()
app.mode = 'pvp'
app.on_left_click((BX(1), BY(7)))          # 红炮 (7,1)
app.on_left_click((BX(4), BY(7)))          # 平到中路
app.on_left_click((BX(7), BY(2)))          # 黑炮 (2,7)
app.on_left_click((BX(4), BY(2)))          # 平到中路
check('棋谱记录两条', len(app.history) == 2, str(app.history))
items = app.panel_items()
check('棋谱标出红黑方', items and items[0]['side'] == RED and items[1]['side'] == BLACK,
      str(items))
check('棋谱条目含着法', items and items[0]['note'] == '炮八平五', str(items[:1]))
check('棋谱面板在棋盘下方',
      app.layout.rec.y >= app.layout.frame_y + app.layout.frame_h)
check('棋谱面板不遮第一排按钮', app.layout.rec.bottom <= app.layout.row1_y)
check('棋谱面板不遮第二排按钮', app.layout.row2_y > app.layout.rec.bottom)

# 多走几步，棋谱超出面板高度才能翻页
for _ in range(4):
    for (fr, fc, tr, tc) in ((9, 0, 8, 0), (0, 8, 1, 8), (8, 0, 7, 0), (1, 8, 2, 8)):
        if (fr, fc, tr, tc) in legal_moves(app.state, app.state.turn):
            app.apply_move((fr, fc, tr, tc))
            break
check('棋谱记录多手', len(app.history) >= 6, str(len(app.history)))
app.record_scroll = 0
app.scroll_record(1)
check('棋谱可向下翻', app.record_scroll > 0, str(app.record_scroll))
app.scroll_record(-1)
check('棋谱可向上翻', app.record_scroll == 0, str(app.record_scroll))

app.new_game()
check('新局清空棋谱记录', len(app.history) == 0 and len(app.panel_items()) == 0,
      str(app.history))

# --- 保存 / 读取棋局 ------------------------------------------------------
TEST_SAVE = os.path.join(TMP, 'xq_saves')
if os.path.isdir(TEST_SAVE):
    shutil.rmtree(TEST_SAVE, ignore_errors=True)
os.makedirs(TEST_SAVE, exist_ok=True)
orig_dir = app.save_dir
check('默认存档目录叫「棋局存档」',
      orig_dir and os.path.basename(orig_dir) == '棋局存档', str(orig_dir))
app.save_dir = TEST_SAVE

app.new_game()
app.mode = 'pvp'
app.on_left_click((BX(1), BY(7)))
app.on_left_click((BX(4), BY(7)))
app.on_left_click((BX(7), BY(2)))
app.on_left_click((BX(4), BY(2)))
ok = app.save_game()
check('保存棋局成功', ok, app.status)
files = [f for f in os.listdir(TEST_SAVE) if f.endswith('.json')]
check('存档文件已生成', len(files) == 1, str(files))

app.toggle_save_list()
check('切到存档列表', app.panel_mode == 'saves')
check('存档列表有这一局', len(app.save_items) == 1, str(app.save_items))
check('存档列表显示手数', app.save_items and '手' in app.save_items[0]['info'],
      str(app.save_items[:1]))

app.load_game(app.save_items[0]['path'])
check('读取后回到棋谱模式', app.panel_mode == 'record')
check('读取后棋盘复原',
      app.state.board[7][4] is not None and app.state.board[2][4] is not None,
      str(app.state.board[7][4]))
check('读取后记录复原', len(app.history) == 2, str(app.history))
check('读取后轮次正确', app.state.turn == RED, str(app.state.turn))
check('读取后模式正确', app.mode == 'pvp', app.mode)

app.save_dir = orig_dir
shutil.rmtree(TEST_SAVE, ignore_errors=True)

# --- 1920x1080 全屏截图 ---------------------------------------------------
app.new_game()
app.mode = 'ai'
app.on_left_click((BX(1), BY(7)))
app.on_left_click((BX(4), BY(7)))
app.screen = pygame.Surface((1920, 1080))
app.set_layout((1920, 1080))
app.draw()
pygame.image.save(app.screen, os.path.join(TMP, 'xq_fullscreen.png'))
check('全屏截图已生成', os.path.exists(os.path.join(TMP, 'xq_fullscreen.png')))

print('\nFAILURES: %d' % len(fails))
if fails:
    print('  ' + ', '.join(fails))
print('screenshots ->', TMP)
