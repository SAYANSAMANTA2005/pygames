import pygame
import random
import math
import sys

# ----------------------------
# CONFIG
# ----------------------------
WIDTH, HEIGHT = 900, 600
FPS = 120
N_PARTICLES = 25   # number of particles
RADIUS = 10
SPEED = 180        # pixels/sec
MARGIN = 40

# Colors
BG = (18, 18, 22)
BOX = (230, 230, 230)
HUD = (230, 230, 230)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Gas Particle Simulation (N particles)")
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
        self.color = (random.randint(80,255), random.randint(80,255), random.randint(80,255))

    def update(self, dt):
        # Move
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Wall collisions (elastic)
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

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.r)

# ----------------------------
# Elastic collision handling
# ----------------------------
def resolve_collision(p1, p2):
    # Vector between centers
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    dist = math.hypot(dx, dy)

    if dist == 0:
        return  # Overlapping exactly, skip to avoid divide by zero

    # Normalized vector
    nx, ny = dx / dist, dy / dist

    # Relative velocity
    dvx, dvy = p1.vx - p2.vx, p1.vy - p2.vy

    # Velocity along normal
    rel_vel = dvx * nx + dvy * ny

    if rel_vel > 0:
        return  # already separating

    # Exchange velocity along normal (equal mass elastic collision)
    p1.vx -= rel_vel * nx
    p1.vy -= rel_vel * ny
    p2.vx += rel_vel * nx
    p2.vy += rel_vel * ny

    # Push them apart slightly to avoid overlap sticking
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
def hud():
    text = f"N={N_PARTICLES} | Speed={SPEED}px/s | Collisions simulated"
    screen.blit(font.render(text, True, HUD), (10, 10))

def draw_box():
    pygame.draw.rect(screen, BOX,
        (MARGIN, MARGIN, WIDTH - 2*MARGIN, HEIGHT - 2*MARGIN), width=2)

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

        # Update particles
        for p in particles:
            p.update(dt)

        # Handle pairwise collisions
        for i in range(len(particles)):
            for j in range(i+1, len(particles)):
                p1, p2 = particles[i], particles[j]
                dx, dy = p1.x - p2.x, p1.y - p2.y
                if dx*dx + dy*dy <= (p1.r + p2.r)**2:
                    resolve_collision(p1, p2)

        # Draw
        screen.fill(BG)
        draw_box()
        for p in particles:
            p.draw(screen)
        hud()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
