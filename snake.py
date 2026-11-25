import random

import pygame
import sys
from collections import deque

from uifont import Fonts

# 1. 初始化设置
pygame.init()
CELL_SIZE = 20
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("贪吃蛇 - 穿墙版")

fonts = Fonts()

# 定义颜色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (220, 0, 0)

# 游戏状态
snake = deque([(WIDTH // (2 * CELL_SIZE), HEIGHT // (2 * CELL_SIZE))])
direction = (0, -1)  # 初始方向向上
food = (0, 0)
score = 0
game_over = False

# 2. 生成食物
def get_food():
    while True:
        x = random.randint(0, WIDTH // CELL_SIZE - 1)
        y = random.randint(0, HEIGHT // CELL_SIZE - 1)
        if (x, y) not in snake:
            return (x, y)
food = get_food()

# 3. 绘制文字 (支持居中)
def draw_text(text, font_size, color, center=False):
    font = fonts.get(font_size)
    text_surface = font.render(text, True, color)
    if center:
        screen.blit(text_surface, (WIDTH // 2 - text_surface.get_width() // 2, HEIGHT // 2 - text_surface.get_height() // 2))
    else:
        screen.blit(text_surface, (10, 10))

# 4. 绘制蛇和食物
def draw():
    screen.fill(BLACK)
    # 画蛇
    for segment in snake:
        rect = pygame.Rect(segment[0] * CELL_SIZE, segment[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
        pygame.draw.rect(screen, GREEN, rect)
    # 画食物
    rect = pygame.Rect(food[0] * CELL_SIZE, food[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE)
    pygame.draw.rect(screen, RED, rect)
    
    # 画分数
    draw_text(f"分数: {score}", 24, WHITE)

# 5. 游戏主循环
running = True
# 【慢速设定】将速度调慢到 7帧/秒，给足反应时间！
clock = pygame.time.Clock()
FPS = 7 

import random # 确保 random 模块被导入

while running:
    clock.tick(FPS)
    
    # 处理键盘和窗口事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
                
            if not game_over:
                # 方向控制 (不能直接掉头)
                if event.key == pygame.K_UP and direction != (0, 1):
                    direction = (0, -1)
                elif event.key == pygame.K_DOWN and direction != (0, -1):
                    direction = (0, 1)
                elif event.key == pygame.K_LEFT and direction != (1, 0):
                    direction = (-1, 0)
                elif event.key == pygame.K_RIGHT and direction != (-1, 0):
                    direction = (1, 0)
            else:
                # 游戏结束后的重开机制
                if event.key == pygame.K_SPACE:
                    snake = deque([(WIDTH // (2 * CELL_SIZE), HEIGHT // (2 * CELL_SIZE))])
                    direction = (0, -1)
                    food = get_food()
                    score = 0
                    game_over = False

    # 游戏逻辑更新
    if not game_over:
        # 计算蛇头新位置
        head = snake[0]
        new_head = (head[0] + direction[0], head[1] + direction[1])
        
        # --- 穿墙处理 (走到边缘后从另一边出来) ---
        if new_head[0] >= WIDTH // CELL_SIZE:
            new_head = (0, new_head[1])
        elif new_head[0] < 0:
            new_head = (WIDTH // CELL_SIZE - 1, new_head[1])
        elif new_head[1] >= HEIGHT // CELL_SIZE:
            new_head = (new_head[0], 0)
        elif new_head[1] < 0:
            new_head = (new_head[0], HEIGHT // CELL_SIZE - 1)
        # --- 穿墙处理结束 ---
        
        # 撞到自己，游戏结束
        if new_head in list(snake)[:-1]:
            game_over = True
        else:
            # 蛇正常移动
            snake.appendleft(new_head)
            # 如果吃到食物
            if new_head == food:
                score += 1
                food = get_food()
            else:
                # 没吃到食物，移除蛇尾
                snake.pop()
                
    # 绘制画面
    draw()
    if game_over:
        draw_text("游戏结束！", 60, RED, center=True)
        draw_text("按空格键重玩，按 ESC 退出", 30, WHITE, center=True)
        
    pygame.display.update()

pygame.quit()
sys.exit()
