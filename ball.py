import pygame
import sys
import math

from uifont import Fonts

# 1. 初始化设置
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("真实物理滚球模拟")
clock = pygame.time.Clock()

fonts = Fonts()

# 颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (50, 50, 50)
GREEN = (0, 200, 100)
RED = (200, 50, 50)

# 2. 定义滚动圆球类
class RollingBall:
    def __init__(self):
        self.radius = 25
        self.x = 100.0
        self.y = HEIGHT - 100.0 - self.radius  # 初始放在地面
        
        # --- 物理引擎参数 ---
        self.vx = 15.0        # 初始水平滚动速度 (每秒像素)
        self.angle = 0.0      # 圆球的滚动角度
        self.ground_friction = 0.99  # 地面摩擦力 (越接近1摩擦力越小，滚得越远)
        
    def update(self):
        # 如果速度还没完全停止，继续更新
        if abs(self.vx) > 0.01:
            # 1. 应用摩擦力 (速度逐渐衰减)
            self.vx *= self.ground_friction
            
            # 2. 更新位置
            self.x += self.vx
            
            # 3. 更新旋转角度 (真实的物理滚动公式: 弧长 = 半径 * 角度)
            self.angle += self.vx / self.radius
            
            # 4. 碰到墙壁反弹并减速
            if self.x + self.radius >= WIDTH:
                self.x = WIDTH - self.radius
                self.vx *= -0.8  # 碰墙反弹并损失部分能量
            elif self.x - self.radius <= 0:
                self.x = self.radius
                self.vx *= -0.8
        else:
            self.vx = 0.0 # 彻底停止

    def draw(self):
        # 绘制白色圆球外轮廓
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius)
        
        # 在圆球上画一条“直径线”，用来直观展示它确实在转动
        line_end_x = self.x + self.radius * math.cos(self.angle)
        line_end_y = self.y + self.radius * math.sin(self.angle)
        
        pygame.draw.line(screen, RED, (int(self.x), int(self.y)), (int(line_end_x), int(line_end_y)), 3)

# 3. 初始化圆球和字体
ball = RollingBall()
font = fonts.get(24)

# 4. 主循环
running = True
while running:
    # 处理退出事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 更新物理状态
    ball.update()

    # 绘制画面
    screen.fill(BLACK)
    
    # 画地面线
    ground_y = HEIGHT - 100
    pygame.draw.line(screen, GRAY, (0, ground_y), (WIDTH, ground_y), 2)
    
    # 画滚动的球
    ball.draw()

    # 绘制状态提示
    speed_text = font.render(f"滚动速度: {ball.vx:.2f}", True, GREEN)
    hint_text = font.render("观察圆球的惯性与地面摩擦力", True, GRAY)
    reset_text = font.render("按 R 键重新加速", True, WHITE)
    
    screen.blit(speed_text, (20, 20))
    screen.blit(hint_text, (20, 60))
    screen.blit(reset_text, (20, 100))

    # 按 R 键重置速度，让它再次滚起来
    keys = pygame.key.get_pressed()
    if keys[pygame.K_r]:
        ball.vx = 15.0

    pygame.display.update()
    clock.tick(60)

pygame.quit()
sys.exit()
