import pygame
import random
import math
import sys
import time

# ----------------------------
# CONFIG
# ----------------------------
WIDTH, HEIGHT = 900, 600
FPS = 120
N_PARTICLES = 2
RADIUS = 10
SPEED = 180        # pixels/sec
MARGIN = 40
TRAIL_DURATION = 2.0  # seconds to keep history

# Colors
BG = (18, 18, 22)
BOX = (230, 230, 230)
HUD = (230, 230, 230)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gas Particle Simulation with Trails")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)

# ----------------------------
# Utility
# ----------------------------
def random_unit_vec():
    theta = random.uniform(0, 2*math.pi)
    return math.cos(theta), math.sin(theta)

# ----------------------------
# Particle class
# ----------------------------
class Particle:
    def __init__(self, x, y, vx, vy, radius=RADIUS):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.r = radius
        self.color = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
        self.trail = []  # list of (x,y,timestamp)

    def update(self, dt, now):
        # Add current position to trail
        self.trail.append((self.x, self.y, now))

        # Remove old trail points
        while self.trail and now - self.trail[0][2] > TRAIL_DURATION:
            self.trail.pop(0)

        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Wall collisions
        left, right = MARGIN + self.r, WIDTH - MARGIN - self.r
        top, bottom = MARGIN + self.r, HEIGHT - MARGIN - self.r

        if self.x <= left:
            self.x = left + (left - self.x)
            self.vx *= -1
        elif self.x >= right:
            self.x = right - (self.x - right)
            self.vx *= -1

        if self.y <= top:
            self.y = top + (top - self.y)
            self.vy *= -1
        elif self.y >= bottom:
            self.y = bottom - (self.y - bottom)
            self.vy *= -1

    def draw(self, surface, now):
        # Draw trail
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                x1, y1, t1 = self.trail[i-1]
                x2, y2, t2 = self.trail[i]
                age = now - t1
                alpha = max(0, 255 - int(255 * age / TRAIL_DURATION))
                color = (*self.color[:3], alpha)
                trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                pygame.draw.line(trail_surface, color, (x1, y1), (x2, y2), 2)
                surface.blit(trail_surface, (0,0))

        # Draw particle
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.r)

# ----------------------------
# Elastic collision handling
# ----------------------------
def resolve_collision(p1, p2):
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    dist = math.hypot(dx, dy)
    if dist == 0:
        return

    nx, ny = dx / dist, dy / dist
    dvx, dvy = p1.vx - p2.vx, p1.vy - p2.vy
    rel_vel = dvx * nx + dvy * ny
    if rel_vel > 0:
        return

    # Exchange velocities (elastic, equal mass)
    p1.vx -= rel_vel * nx
    p1.vy -= rel_vel * ny
    p2.vx += rel_vel * nx
    p2.vy += rel_vel * ny

    # Fix overlap
    overlap = p1.r + p2.r - dist
    if overlap > 0:
        p1.x += nx * overlap / 2
        p1.y += ny * overlap / 2
        p2.x -= nx * overlap / 2
        p2.y -= ny * overlap / 2

# ----------------------------
# Setup particles
# ----------------------------
particles = []
for _ in range(N_PARTICLES):
    while True:
        x = random.uniform(MARGIN+RADIUS, WIDTH-MARGIN-RADIUS)
        y = random.uniform(MARGIN+RADIUS, HEIGHT-MARGIN-RADIUS)
        if all(math.hypot(x - p.x, y - p.y) > 2*RADIUS for p in particles):
            break
    vx, vy = random_unit_vec()
    particles.append(Particle(x, y, vx*SPEED, vy*SPEED))

# ----------------------------
# Main loop
# ----------------------------
def draw_box():
    pygame.draw.rect(screen, BOX,
        (MARGIN, MARGIN, WIDTH - 2*MARGIN, HEIGHT - 2*MARGIN), width=2)

def hud():
    screen.blit(font.render(f"N={N_PARTICLES} | Trail={TRAIL_DURATION}s", True, HUD), (10, 10))

def main():
    running = True
    last = pygame.time.get_ticks()/1000.0

    while running:
        now = pygame.time.get_ticks()/1000.0
        dt = min(0.05, now - last)
        last = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False

        # Update
        for p in particles:
            p.update(dt, now)

        # Collisions
        for i in range(len(particles)):
            for j in range(i+1, len(particles)):
                dx = particles[i].x - particles[j].x
                dy = particles[i].y - particles[j].y
                if dx*dx + dy*dy <= (particles[i].r + particles[j].r)**2:
                    resolve_collision(particles[i], particles[j])

        # Draw
        screen.fill(BG)
        draw_box()
        for p in particles:
            p.draw(screen, now)
        hud()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
