import pygame
import math
import sys
import random

from version import caption

pygame.init()

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption(caption("射箭小游戏"))
clock = pygame.time.Clock()

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
BLUE = (70, 130, 180)
BROWN = (139, 69, 19)

slow = False
shake_timer = 0

class Archer:
    def __init__(self):
        self.x = 100
        self.y = HEIGHT // 2
        self.angle = 0

    def update(self, mouse_pos):
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        self.angle = math.atan2(dy, dx)

    def draw(self):
        pygame.draw.rect(screen, BLUE, (self.x - 15, self.y - 15, 30, 30))
        end_x = self.x + 40 * math.cos(self.angle)
        end_y = self.y + 40 * math.sin(self.angle)
        pygame.draw.line(screen, BLACK, (self.x, self.y), (end_x, end_y), 3)

class Arrow:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.speed = 15
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.gravity = 0.25
        self.active = True
        self.trail = []

    def update(self):
        if self.active:
            if slow:
                self.trail.append((self.x, self.y))
                if len(self.trail) > 10:
                    self.trail.pop(0)

            self.vy += self.gravity
            self.x += self.vx
            self.y += self.vy
            if self.y > HEIGHT or self.x > WIDTH or self.x < 0:
                self.active = False

    def draw(self):
        if self.active:
            angle = math.atan2(self.vy, self.vx)
            length = 20

            # 拖影（跟随箭的角度）
            for i, (tx, ty) in enumerate(self.trail):
                alpha = int(180 * (i + 1) / max(len(self.trail), 1))
                trail_surf = pygame.Surface((40, 10), pygame.SRCALPHA)
                pygame.draw.line(trail_surf, (100, 180, 255, alpha),
                                 (5, 5), (35, 5), 2)
                rotated = pygame.transform.rotate(trail_surf, -math.degrees(angle))
                rect = rotated.get_rect(center=(int(tx), int(ty)))
                screen.blit(rotated, rect)

            tail_x = self.x - length * math.cos(angle)
            tail_y = self.y - length * math.sin(angle)
            pygame.draw.line(screen, BROWN, (int(tail_x), int(tail_y)),
                             (int(self.x), int(self.y)), 3)

            head_len = 8
            left_x = self.x - head_len * math.cos(angle - 0.5)
            left_y = self.y - head_len * math.sin(angle - 0.5)
            right_x = self.x - head_len * math.cos(angle + 0.5)
            right_y = self.y - head_len * math.sin(angle + 0.5)
            pygame.draw.polygon(screen, RED, [
                (int(self.x), int(self.y)),
                (int(left_x), int(left_y)),
                (int(right_x), int(right_y))
            ])

archer = Archer()
arrows = []

running = True
while running:
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                new_arrow = Arrow(archer.x, archer.y, archer.angle)
                arrows.append(new_arrow)
            if event.key == pygame.K_e:
                slow = not slow
                if slow:
                    shake_timer = 8

    archer.update(mouse_pos)
    for arrow in arrows:
        arrow.update()
    arrows = [a for a in arrows if a.active]

    offset_x = 0
    offset_y = 0
    if shake_timer > 0:
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        shake_timer -= 1

    screen.fill(WHITE)

    pygame.draw.line(screen, BLACK, (0, HEIGHT - 20), (WIDTH, HEIGHT - 20), 2)

    if offset_x or offset_y:
        temp = screen.copy()
        screen.fill(WHITE)
        screen.blit(temp, (offset_x, offset_y))

    archer.draw()
    for arrow in arrows:
        arrow.draw()

    # 林克时间晕影滤镜：中间白，外面蓝
    if slow:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_r = int((WIDTH ** 2 + HEIGHT ** 2) ** 0.5) // 2
        for r in range(max_r, 0, -3):
            ratio = r / max_r
            blue = int(220 * (1 - ratio))
            alpha = int(100 * (1 - ratio ** 2))
            color = (255 - blue // 3, 255 - blue // 3, 255, alpha)
            pygame.draw.circle(overlay, color, (cx, cy), r)
        screen.blit(overlay, (0, 0))

    font = pygame.font.SysFont("Arial", 20)
    info = font.render("Mouse to aim, SPACE to shoot, E for slow motion", True, BLACK)
    screen.blit(info, (10, 10))

    pygame.display.flip()
    if slow:
        clock.tick(20)
    else:
        clock.tick(60)

pygame.quit()
sys.exit()
