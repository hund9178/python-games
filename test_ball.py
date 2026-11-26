# -*- coding: utf-8 -*-
"""
弹球物理与速度箭头测试
==========================================
检查滚动物理、加速方向和速度箭头的映射关系是否正确。

运行：
    python test_ball.py
"""
from __future__ import annotations

import math
import os
import sys

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame

pygame.init()
pygame.display.set_mode((10, 10))

import ball

fails = []


def check(name, cond, detail=''):
    print('%s %s%s' % ('[PASS]' if cond else '[FAIL]', name,
                       ('  -> ' + detail) if (detail and not cond) else ''))
    if not cond:
        fails.append(name)


def simulate(b, seconds, dt=1.0 / 60.0):
    """按固定步长推进 seconds 秒。"""
    for _ in range(int(round(seconds / dt))):
        b.update(dt)


print('=' * 60)
print('弹球物理与速度箭头测试')
print('=' * 60)

# --- 1. 球始终待在窗口和地面以内 ---
b = ball.RollingBall(None)
out_of_screen = False
below_ground = False
for _ in range(60 * 40):  # 40 秒
    b.update(1.0 / 60.0)
    if b.x - b.radius < -0.01 or b.x + b.radius > ball.WIDTH + 0.01:
        out_of_screen = True
    if b.y + b.radius > ball.HEIGHT - ball.GROUND_OFFSET + 0.01:
        below_ground = True
check('球不会飞出左右边界', not out_of_screen)
check('球不会掉到地面以下', not below_ground)

# --- 2. 摩擦会让球停下来 ---
b = ball.RollingBall(None)
simulate(b, 30)
check('摩擦足够时球会完全停下', b.speed() == 0.0, '当前速度 %.2f' % b.speed())
check('停下后不再画箭头', b.arrow_state() is None)

# --- 3. 运动中加速：方向不变，速度变大 ---
b = ball.RollingBall(None)
b.vx, b.vy = 400.0, 0.0
before_dir = math.atan2(b.vy, b.vx)
before_speed = b.speed()
b.boost()
after_dir = math.atan2(b.vy, b.vx)
check('加速后方向保持不变',
      abs((after_dir - before_dir + math.pi) % (2 * math.pi) - math.pi) < 1e-6)
check('加速后速度变大', b.speed() > before_speed,
      '%.1f -> %.1f' % (before_speed, b.speed()))
check('加速不超过速度上限', b.speed() <= ball.MAX_SPEED + 1e-6)

# --- 4. 静止时加速：方向随机 ---
angles = []
for _ in range(12):
    b = ball.RollingBall(None)
    b.vx = b.vy = 0.0
    b.boost()
    angles.append(math.atan2(b.vy, b.vx))
    check_range = (ball.RANDOM_SPEED[0] <= b.speed() <= ball.RANDOM_SPEED[1])
    if not check_range:
        check('静止加速后的速度在随机范围内', False, '%.1f' % b.speed())
        break
else:
    check('静止加速后的速度在随机范围内', True)
check('静止时加速的方向确实是随机的',
      len({round(a, 2) for a in angles}) > 1, '取样方向: %r' % angles)

# --- 5. 箭头指向运动方向 ---
b = ball.RollingBall(None)
b.vx, b.vy = 300.0, 400.0
ang, length, color = b.arrow_state()
check('箭头角度等于速度方向角',
      abs(ang - math.atan2(b.vy, b.vx)) < 1e-9)

# --- 6. 速度越快箭头越长 ---
lengths = []
for speed in (50.0, 300.0, 600.0, 1000.0):
    b = ball.RollingBall(None)
    b.vx, b.vy = speed, 0.0
    lengths.append(b.arrow_state()[1])
check('箭头长度随速度递增',
      lengths == sorted(lengths) and lengths[0] < lengths[-1],
      '各速度对应长度: %r' % lengths)

# --- 7. 速度越快箭头颜色越深 ---
sums = []
for speed in (50.0, 300.0, 600.0, 1000.0):
    b = ball.RollingBall(None)
    b.vx, b.vy = speed, 0.0
    c = b.arrow_state()[2]
    sums.append(sum(c))
check('箭头颜色随速度变深',
      sums == sorted(sums, reverse=True) and sums[0] > sums[-1],
      '各速度颜色亮度: %r' % sums)

# --- 8. 帧率无关：60 帧和 30 帧跑 1 秒结果接近 ---
def distance_after_one_second(dt):
    b = ball.RollingBall(None)
    b.vx, b.vy = ball.INITIAL_SPEED, 0.0
    start = b.x
    simulate(b, 1.0, dt)
    return b.x - start


d60 = distance_after_one_second(1.0 / 60.0)
d30 = distance_after_one_second(1.0 / 30.0)
check('不同帧率下滚动的距离接近',
      abs(d60 - d30) / max(d60, 1e-6) < 0.05,
      '60帧 %.1f vs 30帧 %.1f' % (d60, d30))

print()
print('=' * 60)
if fails:
    print('失败 %d 项:' % len(fails))
    for name in fails:
        print('  -', name)
    sys.exit(1)
print('全部通过')
