import pygame
import sys
import math
import random

from uifont import Fonts
from version import caption

# 窗口大小
WIDTH, HEIGHT = 800, 600

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
LIGHT_GRAY = (120, 120, 120)
GREEN = (0, 200, 100)
HOLD_COLOR = (255, 214, 64)  # 定住时的黄色

# 物理参数（单位：像素 / 秒，与帧率无关）
GROUND_OFFSET = 100.0     # 地面离窗口底部的距离
GRAVITY = 1600.0          # 重力加速度
INITIAL_SPEED = 800.0     # 初始滚动速度
MAX_SPEED = 1100.0        # 速度上限，同时也是箭头长度的满量程
BOOST_ADD = 220.0         # 按空格加速时增加的速度
FLING_FACTOR = 1.5        # R 键「弹出去」时动量的放大倍数
RANDOM_SPEED = (320.0, 780.0)  # 静止时随机加速的速度范围
ROLL_FRICTION = 0.5       # 滚动摩擦：每秒保留的速度比例
BOUNCE = 0.7              # 落地反弹系数
WALL_BOUNCE = 0.82        # 撞墙反弹系数
STOP_SPEED = 25.0         # 低于该速度视为静止

# 箭头参数：起点在圆心，指向滚动方向，长度/颜色表示速度
ARROW_MIN_LEN = 38.0      # 速度接近 0 时的箭头长度
ARROW_MAX_LEN = 105.0     # 速度达到 MAX_SPEED 时的箭头长度
SPEED_STOPS = (            # 速度 → 颜色：越快颜色越深（浅绿 → 橙 → 深红）
    (0.0, (150, 240, 160)),
    (0.5, (255, 170, 50)),
    (1.0, (150, 15, 15)),
)


def speed_color(t):
    """按速度比例取颜色，t 为 0~1，越大颜色越深。"""
    t = max(0.0, min(1.0, t))
    for i in range(len(SPEED_STOPS) - 1):
        t0, c0 = SPEED_STOPS[i]
        t1, c1 = SPEED_STOPS[i + 1]
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return (int(c0[0] + (c1[0] - c0[0]) * k),
                    int(c0[1] + (c1[1] - c0[1]) * k),
                    int(c0[2] + (c1[2] - c0[2]) * k))
    return SPEED_STOPS[-1][1]


def direction_name(dx, dy):
    """把方向向量翻译成「左上 / 右下」这类说法，同时返回角度。"""
    deg = math.degrees(math.atan2(dy, dx)) % 360.0
    names = ('右', '右下', '下', '左下', '左', '左上', '上', '右上')
    return names[int((deg + 22.5) // 45) % 8], deg


class RollingBall:
    """在地面上滚动的球，带速度箭头。

    按键：
      空格  滚动时沿当前方向加速；定住时按原来的方向和力度放出去
      R     滚动时把球定住（变黄，保存当前的力和方向）；
            攒着力时一次全放出来弹出去
    """

    def __init__(self, screen):
        self.screen = screen
        self.radius = 25
        self.x = 100.0
        self.y = HEIGHT - GROUND_OFFSET - self.radius  # 初始放在地面
        self.vx = INITIAL_SPEED  # 水平速度 (像素/秒)
        self.vy = 0.0            # 垂直速度 (像素/秒)
        self.angle = 0.0         # 圆球的滚动角度
        # --- 定住 / 蓄力 ---
        self.held = False           # 球是否被定住
        self.hold_speed = 0.0       # 定住时保存的力（速度大小）
        self.hold_dir = (1.0, 0.0)  # 定住时保存的方向
        self.pending_force = 0.0    # 攒着还没放出来的力
        self.fling_flash = 0.0      # 弹出去时的特效
        self.clock_time = 0.0

    def speed(self):
        """球现在的实际速度。定住时球没在动，速度是 0。"""
        if self.held:
            return 0.0
        return math.hypot(self.vx, self.vy)

    def stored_speed(self):
        """定住时保存的力，平时就是当前速度。"""
        return self.hold_speed if self.held else self.speed()

    def boost(self):
        """空格：定住时按原方向原力度放出去，滚动时沿当前方向加速。"""
        if self.held:
            speed = self.hold_speed
            if speed > STOP_SPEED:
                ux, uy = self.hold_dir
            else:
                # 停稳以后再放出去，给个随机方向
                ang = random.uniform(0.0, math.tau)
                ux, uy = math.cos(ang), math.sin(ang)
                speed = random.uniform(*RANDOM_SPEED)
            self.vx, self.vy = ux * speed, uy * speed
            self.held = False
            # 放出去的力还攒着，等 R 一次全放出来
            self.pending_force = speed
            return

        speed = self.speed()
        if speed > STOP_SPEED:
            ux, uy = self.vx / speed, self.vy / speed
            new_speed = min(speed + BOOST_ADD, MAX_SPEED)
        else:
            # 完全静止：随机方向加速
            ang = random.uniform(0.0, math.tau)
            ux, uy = math.cos(ang), math.sin(ang)
            new_speed = random.uniform(*RANDOM_SPEED)
        self.vx, self.vy = ux * new_speed, uy * new_speed
        self.pending_force += BOOST_ADD

    def toggle_hold(self):
        """R：平时把球定住（变黄），攒着力时一次全放出来弹出去。"""
        if self.held:
            # 定住时再按 R：直接弹出去，把保存的力全放出来
            speed = min(self.hold_speed * FLING_FACTOR, MAX_SPEED)
            ux, uy = self.hold_dir
            self.vx, self.vy = ux * speed, uy * speed
            self.held = False
            self.pending_force = 0.0
            self.fling_flash = 1.0
            return

        if self.pending_force > 0:
            # 攒着的力一次放完
            speed = self.speed()
            if speed > STOP_SPEED:
                ux, uy = self.vx / speed, self.vy / speed
            else:
                ux, uy = 1.0, 0.0
            new_speed = min(speed + self.pending_force, MAX_SPEED)
            self.vx, self.vy = ux * new_speed, uy * new_speed
            self.pending_force = 0.0
            self.fling_flash = 1.0
            return

        # 定住球，保存当前的力和方向
        speed = self.speed()
        if speed > STOP_SPEED:
            self.hold_speed = speed
            self.hold_dir = (self.vx / speed, self.vy / speed)
        else:
            self.hold_speed = 0.0
            self.hold_dir = (1.0, 0.0)
        self.held = True
        self.vx = self.vy = 0.0

    def update(self, dt):
        """按时间步长 dt（秒）推进物理，帧率变化不影响手感。"""
        self.clock_time += dt
        if self.fling_flash > 0:
            self.fling_flash = max(0.0, self.fling_flash - dt * 2.5)

        if self.held:
            return  # 定住时球不动，保存的力也不衰减

        # 重力
        self.vy += GRAVITY * dt

        # 位置
        self.x += self.vx * dt
        self.y += self.vy * dt

        # 地面：落地反弹并承受滚动摩擦
        ground_y = HEIGHT - GROUND_OFFSET
        on_ground = False
        if self.y + self.radius >= ground_y:
            self.y = ground_y - self.radius
            on_ground = True
            if self.vy > 0:
                self.vy = -self.vy * BOUNCE
                if abs(self.vy) < 60.0:
                    self.vy = 0.0
            self.vx *= ROLL_FRICTION ** dt

        # 左右墙壁反弹
        if self.x + self.radius >= WIDTH:
            self.x = WIDTH - self.radius
            self.vx = -abs(self.vx) * WALL_BOUNCE
        elif self.x - self.radius <= 0:
            self.x = self.radius
            self.vx = abs(self.vx) * WALL_BOUNCE

        # 地面上慢下来以后彻底停住
        if on_ground and self.speed() < STOP_SPEED:
            self.vx = 0.0
            self.vy = 0.0
            self.pending_force = 0.0  # 攒着的力被摩擦耗光了

        # 滚动角度：弧长 = 半径 * 角度
        self.angle += (self.vx / self.radius) * dt

    def arrow_state(self):
        """箭头的几何信息：(方向角, 长度, 颜色)。没有速度时返回 None。"""
        if self.held:
            # 定住时画的是保存下来的力，方向和大小都不变
            if self.hold_speed <= STOP_SPEED:
                return None
            t = min(1.0, self.hold_speed / MAX_SPEED)
            ang = math.atan2(self.hold_dir[1], self.hold_dir[0])
            length = ARROW_MIN_LEN + (ARROW_MAX_LEN - ARROW_MIN_LEN) * t
            return ang, length, HOLD_COLOR

        speed = self.speed()
        if speed <= STOP_SPEED:
            return None
        t = min(1.0, speed / MAX_SPEED)
        ang = math.atan2(self.vy, self.vx)
        length = ARROW_MIN_LEN + (ARROW_MAX_LEN - ARROW_MIN_LEN) * t
        return ang, length, speed_color(t)

    def draw(self):
        pos = (int(self.x), int(self.y))
        if self.held:
            self._draw_held(pos)
        else:
            # 白色圆球外轮廓
            pygame.draw.circle(self.screen, WHITE, pos, self.radius)

            # 直径线，用来直观展示它确实在转动
            line_end_x = self.x + self.radius * math.cos(self.angle)
            line_end_y = self.y + self.radius * math.sin(self.angle)
            pygame.draw.line(self.screen, LIGHT_GRAY, (int(self.x), int(self.y)),
                             (int(line_end_x), int(line_end_y)), 3)

        self.draw_arrow()
        self._draw_fling_flash(pos)

    def _draw_held(self, pos):
        """定住时球变黄，外面套一圈呼吸光环。"""
        pygame.draw.circle(self.screen, HOLD_COLOR, pos, self.radius)
        pygame.draw.circle(self.screen, WHITE, pos, self.radius, 2)
        pulse = 4 + 3 * math.sin(self.clock_time * 6.0)
        pygame.draw.circle(self.screen, HOLD_COLOR, pos,
                           int(self.radius + pulse), 2)

    def _draw_fling_flash(self, pos):
        """弹出去的一瞬间扩散一圈黄环。"""
        if self.fling_flash <= 0:
            return
        radius = int(self.radius + (1.0 - self.fling_flash) * 70)
        pygame.draw.circle(self.screen, HOLD_COLOR, pos, radius, 3)

    def draw_arrow(self):
        """速度箭头：起点在圆心，指向滚动方向，长度和颜色深浅表示速度。"""
        state = self.arrow_state()
        if state is None:
            return  # 没有速度时不画箭头

        ang, length, color = state
        speed = self.stored_speed()
        t = min(1.0, speed / MAX_SPEED)
        ux, uy = math.cos(ang), math.sin(ang)
        px, py = -uy, ux  # 垂直于箭头方向的单位向量

        shaft_w = 3.0 + 3.0 * t          # 箭杆半宽
        head_w = 9.0 + 6.0 * t           # 箭头半宽
        head_len = 14.0 + 8.0 * t        # 箭头长度
        base = length - head_len         # 箭杆与箭头相接处

        cx, cy = self.x, self.y
        pts = [
            (cx, cy),
            (cx + ux * base + px * shaft_w, cy + uy * base + py * shaft_w),
            (cx + ux * base + px * head_w, cy + uy * base + py * head_w),
            (cx + ux * length, cy + uy * length),
            (cx + ux * base - px * head_w, cy + uy * base - py * head_w),
            (cx + ux * base - px * shaft_w, cy + uy * base - py * shaft_w),
        ]
        pygame.draw.polygon(self.screen, color, pts)


def draw_legend(screen, small_font):
    """右下角的颜色图例，说明颜色越深速度越快。"""
    bar_w, bar_h = 220, 14
    x0, y0 = WIDTH - bar_w - 30, HEIGHT - 60
    for i in range(bar_w):
        pygame.draw.rect(screen, speed_color(i / (bar_w - 1)),
                         (x0 + i, y0, 1, bar_h))
    pygame.draw.rect(screen, LIGHT_GRAY, (x0, y0, bar_w, bar_h), 1)
    screen.blit(small_font.render("慢", True, LIGHT_GRAY), (x0 - 26, y0 - 4))
    screen.blit(small_font.render("快", True, LIGHT_GRAY), (x0 + bar_w + 6, y0 - 4))


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(caption("真实物理滚球模拟"))
    clock = pygame.time.Clock()

    fonts = Fonts()
    font = fonts.get(24)
    small_font = fonts.get(18)

    ball = RollingBall(screen)
    running = True
    while running:
        # dt 用两次 tick 之间的时间，帧率变化不影响手感
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 1.0 / 20.0)  # 掉帧时不要让物理跳得太离谱
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    ball.boost()  # 加速 / 把定住的球放出去
                elif event.key == pygame.K_r:
                    ball.toggle_hold()  # 定住 / 一次放出所有的力
                elif event.key == pygame.K_ESCAPE:
                    running = False

        # 更新物理状态
        ball.update(dt)

        # 绘制画面
        screen.fill(BLACK)

        # 画地面线
        ground_y = HEIGHT - GROUND_OFFSET
        pygame.draw.line(screen, GRAY, (0, ground_y), (WIDTH, ground_y), 2)

        # 画滚动的球和速度箭头
        ball.draw()

        # 绘制状态提示
        speed = ball.speed()
        if ball.held:
            speed_text = font.render(f"蓄力: {ball.hold_speed:.1f} px/s", True,
                                     HOLD_COLOR)
            dir_text = font.render("状态: 定住（球变黄，方向和力都锁着）",
                                    True, HOLD_COLOR)
        else:
            speed_text = font.render(f"速度: {speed:.1f} px/s", True, GREEN)
            if speed > STOP_SPEED:
                name, deg = direction_name(ball.vx, ball.vy)
                dir_text = font.render(f"方向: {name} ({deg:.0f}°)", True, WHITE)
            else:
                dir_text = font.render("方向: 静止", True, LIGHT_GRAY)
        hint_text = font.render("空格：加速（定住时按原方向放出去）", True, GRAY)
        reset_text = font.render("R：定住球（变黄）／攒着力时一次全放出来", True,
                                 WHITE)

        screen.blit(speed_text, (20, 20))
        screen.blit(dir_text, (20, 55))
        screen.blit(hint_text, (20, 95))
        screen.blit(reset_text, (20, 130))
        draw_legend(screen, small_font)

        pygame.display.update()

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
