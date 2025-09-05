import pygame
import sys
import math
import random

# -------- CONFIG ----------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

WORLD_W, WORLD_H = 4000, 3000    # larger world than screen
PLAYER_SPEED = 380               # pixels per second
BULLET_SPEED = 1200
PARALLAX_FACTORS = [0.4, 0.7, 1.0]  # farther -> smaller factor (moves less)

# Colors
SKY = (100, 155, 255)
GROUND = (40, 120, 60)
GRID_COLOR = (35, 100, 50)
PLAYER_COLOR = (255, 200, 50)
ENEMY_COLOR = (220, 80, 80)
BULLET_COLOR = (255, 255, 0)
WALL_COLOR = (80, 80, 80, 200)

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Mini Valorant Exploration (Pygame)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Consolas", 18)

# -------- UTIL ----------
def clamp(v, a, b):
    return max(a, min(b, v))

# -------- CAMERA ----------
class Camera:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.x = 0
        self.y = 0

    def update(self, target_x, target_y):
        # center camera on target, but clamp to world bounds
        self.x = clamp(target_x - SCREEN_W//2, 0, self.w - SCREEN_W)
        self.y = clamp(target_y - SCREEN_H//2, 0, self.h - SCREEN_H)

    def world_to_screen(self, wx, wy, parallax=1.0):
        # parallax: 1.0 = full movement, <1 moves less (far layer)
        sx = (wx - self.x) * parallax + (1 - parallax) * (SCREEN_W/2)
        sy = (wy - self.y) * parallax + (1 - parallax) * (SCREEN_H/2)
        return int(sx), int(sy)

camera = Camera(WORLD_W, WORLD_H)

# -------- WORLD CONTENT ----------
# generate some random rectangular walls (obstacles)
walls = []
for _ in range(120):
    w = random.randint(60, 260)
    h = random.randint(60, 260)
    x = random.randint(0, WORLD_W - w)
    y = random.randint(0, WORLD_H - h)
    walls.append(pygame.Rect(x, y, w, h))

# make sure a start region is clear
start_rect = pygame.Rect(0, 0, 600, 600)
walls = [r for r in walls if not r.colliderect(start_rect)]

# -------- PLAYER ----------
player = {
    "x": 300.0,
    "y": 300.0,
    "r": 16,
    "speed": PLAYER_SPEED,
    "angle": 0.0,
}

# bullets list
bullets = []

# helper to check collision with walls
def collides_walls(rect):
    for w in walls:
        if rect.colliderect(w):
            return True
    return False

# -------- MAIN LOOP ----------
running = True
while running:
    dt = clock.tick(FPS) / 1000.0

    # --- EVENTS ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # shoot bullet towards mouse world pos
            mx, my = pygame.mouse.get_pos()
            # convert mouse screen -> world (approx)
            wx = camera.x + mx
            wy = camera.y + my
            dx = wx - player["x"]
            dy = wy - player["y"]
            dist = math.hypot(dx, dy) or 1.0
            vx = dx / dist * BULLET_SPEED
            vy = dy / dist * BULLET_SPEED
            bullets.append({
                "x": player["x"],
                "y": player["y"],
                "vx": vx,
                "vy": vy,
                "life": 2.5
            })

    # --- INPUT & PLAYER MOVE ---
    keys = pygame.key.get_pressed()
    move_x = move_y = 0.0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        move_y -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        move_y += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        move_x -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        move_x += 1

    # normalize diagonal
    if move_x != 0 and move_y != 0:
        inv = 1 / math.sqrt(2)
        move_x *= inv
        move_y *= inv

    # compute tentative new position and collision
    new_x = player["x"] + move_x * player["speed"] * dt
    new_y = player["y"] + move_y * player["speed"] * dt

    # create circle rect for collision test
    player_rect = pygame.Rect(new_x - player["r"], new_y - player["r"], player["r"]*2, player["r"]*2)
    if not collides_walls(player_rect):
        player["x"], player["y"] = new_x, new_y
    else:
        # try axis separated movement (slide along walls)
        test_rect_x = pygame.Rect(new_x - player["r"], player["y"] - player["r"], player["r"]*2, player["r"]*2)
        test_rect_y = pygame.Rect(player["x"] - player["r"], new_y - player["r"], player["r"]*2, player["r"]*2)
        if not collides_walls(test_rect_x):
            player["x"] = new_x
        elif not collides_walls(test_rect_y):
            player["y"] = new_y
        # else blocked, stay

    # update player angle to face mouse world pos
    mx, my = pygame.mouse.get_pos()
    world_mx = camera.x + mx
    world_my = camera.y + my
    player["angle"] = math.degrees(math.atan2(world_my - player["y"], world_mx - player["x"]))

    # update bullets
    for b in bullets[:]:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["life"] -= dt
        br = pygame.Rect(b["x"]-3, b["y"]-3, 6, 6)
        # bullet vs walls
        hit = False
        for w in walls:
            if br.colliderect(w):
                hit = True
                break
        if hit or b["life"] <= 0 or b["x"] < 0 or b["x"] > WORLD_W or b["y"] < 0 or b["y"] > WORLD_H:
            bullets.remove(b)

    # update camera to follow player (centered) with clamping
    camera.update(player["x"], player["y"])

    # --- DRAW BACKGROUND LAYERS (parallax) ---
    screen.fill(SKY)

    # far layer: clouds (parallax factor 0.4)
    par = PARALLAX_FACTORS[0]
    # draw simple random "cloud" blobs as circles spaced across the world
    cloud_radius = 60
    # we'll draw clouds on a grid so they repeat uniformly
    cloud_spacing = 800
    start_cx = -cloud_spacing
    for cx in range(start_cx, WORLD_W + cloud_spacing, cloud_spacing):
        for cy in range(-cloud_spacing//2, WORLD_H + cloud_spacing, cloud_spacing):
            sx, sy = camera.world_to_screen(cx + 120 * math.sin(cx+cy*0.01), cy + 70*math.cos(cx*0.005), parallax=par)
            pygame.draw.circle(screen, (245,245,255), (sx, sy), int(cloud_radius * (0.8 + 0.4*math.sin(cx*0.001+pygame.time.get_ticks()*0.0005))))

    # mid layer: repeated mountains/tiles (parallax 0.7)
    par = PARALLAX_FACTORS[1]
    tile = 120
    for tx in range(0, WORLD_W, tile):
        for ty in range(0, WORLD_H, tile):
            sx, sy = camera.world_to_screen(tx, ty, parallax=par)
            # draw small tiles / decorative mountains as rects
            r = pygame.Rect(sx - int(tile*par/2), sy - int(tile*par/2), int(tile*par), int(tile*par))
            pygame.draw.rect(screen, (35, 95, 45), r)

    # ground layer (parallax 1.0) - tiled grid
    par = PARALLAX_FACTORS[2]
    screen_ground = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    # draw grid tile lines in world space but mapped to screen
    grid_size = 80
    # compute first grid line indices visible
    gx0 = (camera.x // grid_size) * grid_size
    gy0 = (camera.y // grid_size) * grid_size
    for gx in range(int(gx0)-grid_size, int(gx0)+SCREEN_W+grid_size, grid_size):
        sx, sy = camera.world_to_screen(gx, camera.y, parallax=par)
        pygame.draw.line(screen, GRID_COLOR, (sx, 0), (sx, SCREEN_H), 2)
    for gy in range(int(gy0)-grid_size, int(gy0)+SCREEN_H+grid_size, grid_size):
        sx, sy = camera.world_to_screen(camera.x, gy, parallax=par)
        pygame.draw.line(screen, GRID_COLOR, (0, sy), (SCREEN_W, sy), 2)

    # fill floor as a large rectangle in world coords mapped to screen corners
    # draw a big rectangle under everything (just cover screen bottom area)
    pygame.draw.rect(screen, GROUND, (0, SCREEN_H//2, SCREEN_W, SCREEN_H//2))

    # --- DRAW WALLS (world -> screen) ---
    for w in walls:
        sx, sy = camera.world_to_screen(w.x, w.y, parallax=1.0)
        rect = pygame.Rect(sx, sy, w.width, w.height)
        pygame.draw.rect(screen, WALL_COLOR, rect)

    # --- DRAW BULLETS ---
    for b in bullets:
        sx, sy = camera.world_to_screen(b["x"], b["y"], parallax=1.0)
        pygame.draw.circle(screen, BULLET_COLOR, (sx, sy), 4)

    # --- DRAW PLAYER (world -> screen) ---
    px, py = camera.world_to_screen(player["x"], player["y"], parallax=1.0)
    # draw shadow slightly below
    shadow = pygame.Surface((player["r"]*4, player["r"]*2), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0,0,0,90), shadow.get_rect())
    sh_rect = shadow.get_rect(center=(px, py + player["r"] + 8))
    screen.blit(shadow, sh_rect)

    # player body
    pygame.draw.circle(screen, PLAYER_COLOR, (px, py), player["r"])
    # facing direction line
    ang = math.radians(player["angle"])
    ex = px + math.cos(ang) * player["r"] * 1.6
    ey = py + math.sin(ang) * player["r"] * 1.6
    pygame.draw.line(screen, (0,0,0), (px, py), (ex, ey), 3)

    # draw a little 'reticle' at mouse screen pos
    mx, my = pygame.mouse.get_pos()
    pygame.draw.circle(screen, (0,0,0), (mx,my), 6, 2)

    # --- HUD (score/time/simple minimap) ---
    # top-left info
    info_surf = font.render(f"World: {WORLD_W}x{WORLD_H}  Pos: ({int(player['x'])},{int(player['y'])})  Bullets: {len(bullets)}", True, (255,255,255))
    screen.blit(info_surf, (12, 12))

    # minimap (scaled down view)
    mini_w, mini_h = 240, 160
    minimap = pygame.Surface((mini_w, mini_h))
    minimap.fill((20, 20, 20))
    # draw walls on minimap
    scale_x = mini_w / WORLD_W
    scale_y = mini_h / WORLD_H
    for w in walls:
        r = pygame.Rect(int(w.x * scale_x), int(w.y * scale_y), int(w.width * scale_x), int(w.height * scale_y))
        pygame.draw.rect(minimap, (120,120,120), r)
    # draw player on minimap
    pygame.draw.circle(minimap, PLAYER_COLOR, (int(player["x"] * scale_x), int(player["y"] * scale_y)), 4)
    # draw viewport rect
    view_rect = pygame.Rect(int(camera.x * scale_x), int(camera.y * scale_y), int(SCREEN_W * scale_x), int(SCREEN_H * scale_y))
    pygame.draw.rect(minimap, (255,255,255), view_rect, 2)
    screen.blit(minimap, (SCREEN_W - mini_w - 12, 12))

    # update display
    pygame.display.flip()

pygame.quit()
sys.exit()
