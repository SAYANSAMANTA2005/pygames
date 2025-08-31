import pygame
import math
import sys

# Initialize pygame
pygame.init()

# Screen settings
WIDTH, HEIGHT = 1000, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Solar System Simulation")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 204, 0)
GRAY = (180, 180, 180)
BLUE = (80, 80, 255)
RED = (255, 80, 80)
GREEN = (80, 255, 80)

# Clock
clock = pygame.time.Clock()

# Planet data: (name, color, distance, radius, orbit_speed, has_moon)
planets = [
    ("Mercury", GRAY, 70, 6, 0.04, False),
    ("Venus", (255, 180, 0), 100, 10, 0.03, False),
    ("Earth", BLUE, 150, 12, 0.02, True),
    ("Mars", RED, 200, 9, 0.017, True),
    ("Jupiter", (200, 150, 100), 280, 20, 0.01, True),
    ("Saturn", (210, 180, 140), 350, 18, 0.008, True),
    ("Uranus", (150, 200, 255), 420, 14, 0.006, True),
    ("Neptune", (100, 120, 255), 480, 14, 0.005, True),
]

# Sun
SUN_RADIUS = 30
sun_pos = (WIDTH // 2, HEIGHT // 2)

# Planet angles
angles = [0 for _ in planets]
moon_angles = [0 for _ in planets]

# Main loop
running = True
while running:
    clock.tick(60)
    WIN.fill(BLACK)

    # Draw Sun
    pygame.draw.circle(WIN, YELLOW, sun_pos, SUN_RADIUS)

    for i, (name, color, dist, radius, speed, has_moon) in enumerate(planets):
        # Update angle
        angles[i] += speed
        x = sun_pos[0] + int(dist * math.cos(angles[i]))
        y = sun_pos[1] + int(dist * math.sin(angles[i]))

        # Planet body
        pygame.draw.circle(WIN, color, (x, y), radius)

        # Draw orbit path (light reflection effect with transparency)
        pygame.draw.circle(WIN, (100, 100, 100), sun_pos, dist, 1)

        # Add moons
        if has_moon:
            moon_angles[i] += speed * 4
            mx = x + int((radius + 20) * math.cos(moon_angles[i]))
            my = y + int((radius + 20) * math.sin(moon_angles[i]))
            pygame.draw.circle(WIN, GRAY, (mx, my), 4)

        # Eclipse shadow effect (planet blocking sunlight)
        dx, dy = x - sun_pos[0], y - sun_pos[1]
        dist_from_sun = math.sqrt(dx*dx + dy*dy)
        shadow_len = max(40, 200 - dist_from_sun//2)
        shadow_end = (x + int(dx/dist_from_sun*shadow_len),
                      y + int(dy/dist_from_sun*shadow_len))
        pygame.draw.line(WIN, BLACK, (x, y), shadow_end, radius//2)

    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            running = False

    # Update display
    pygame.display.flip()

pygame.quit()
sys.exit()