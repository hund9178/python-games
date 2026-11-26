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

# 物理参数（单位：像素 / 秒，与帧率无关）
GROUND_OFFSET = 100.0     # 地面离窗口底部的距离
GRAVITY = 1600.0          # 重力加速度
INITIAL_SPEED = 800.0     # 初始滚动速度
MAX_SPEED = 1100.0        # 速度上限，同时也是箭头长度的满量程
BOOST_ADD = 220.0         # 按空格加速时增加的速度
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
    """在地面上滚动的球，带速度箭头。"""

    def __init__(self, screen):
        self.screen = screen
        self.radius = 25
        self.x = 100.0
        self.y = HEIGHT - GROUND_OFFSET - self.radius  # 初始放在地面
        self.vx = INITIAL_SPEED  # 水平速度 (像素/秒)
        self.vy = 0.0            # 垂直速度 (像素/秒)
        self.angle = 0.0         # 圆球的滚动角度

    def speed(self):
        """当前速度大小。"""
        return math.hypot(self.vx, self.vy)

    def boost(self):
        """按空格加速：沿当前运动方向加速；完全静止时随机给一个方向。"""
        speed = self.speed()
        if speed > STOP_SPEED:
            ux, uy = self.vx / speed, self.vy / speed
            new_speed = min(speed + BOOST_ADD, MAX_SPEED)
        else:
            ang = random.uniform(0.0, math.tau)
            ux, uy = math.cos(ang), math.sin(ang)
            new_speed = random.uniform(*RANDOM_SPEED)
        self.vx = ux * new_speed
        self.vy = uy * new_speed

    def update(self, dt):
        """按时间步长 dt（秒）推进物理，帧率变化不影响手感。"""
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

        # 滚动角度：弧长 = 半径 * 角度
        self.angle += (self.vx / self.radius) * dt

    def arrow_state(self):
        """箭头的几何信息：(方向角, 长度, 颜色)。静止时返回 None。"""
        speed = self.speed()
        if speed <= STOP_SPEED:
            return None
        t = min(1.0, speed / MAX_SPEED)
        ang = math.atan2(self.vy, self.vx)
        length = ARROW_MIN_LEN + (ARROW_MAX_LEN - ARROW_MIN_LEN) * t
        return ang, length, speed_color(t)

    def draw(self):
        # 绘制白色圆球外轮廓
        pygame.draw.circle(self.screen, WHITE, (int(self.x), int(self.y)), self.radius)

        # 在圆球上画一条“直径线”，用来直观展示它确实在转动
        line_end_x = self.x + self.radius * math.cos(self.angle)
        line_end_y = self.y + self.radius * math.sin(self.angle)

        pygame.draw.line(self.screen, LIGHT_GRAY, (int(self.x), int(self.y)),
                         (int(line_end_x), int(line_end_y)), 3)

        self.draw_arrow()

    def draw_arrow(self):
        """速度箭头：起点在圆心，指向滚动方向，长度和颜色深浅表示速度。"""
        state = self.arrow_state()
        if state is None:
            return  # 静止时不画箭头

        ang, length, color = state
        t = min(1.0, self.speed() / MAX_SPEED)
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
                    ball.boost()  # 沿当前方向加速，静止时随机方向
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
        speed_text = font.render(f"速度: {speed:.1f} px/s", True, GREEN)
        if speed > STOP_SPEED:
            name, deg = direction_name(ball.vx, ball.vy)
            dir_text = font.render(f"方向: {name} ({deg:.0f}°)", True, WHITE)
        else:
            dir_text = font.render("方向: 静止", True, LIGHT_GRAY)
        hint_text = font.render("箭头指向滚动方向，长度和颜色深浅表示速度", True, GRAY)
        reset_text = font.render("按空格键加速（沿当前方向，静止时随机方向）", True, WHITE)

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
