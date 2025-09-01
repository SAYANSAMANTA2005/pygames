# valorant.py
# A simple 2D top-down shooter prototype inspired by Valorant mechanics.
# Requires: pygame (pip install pygame)

import pygame
import math
import random

pygame.init()
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini-Valorant (Top-down prototype)")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 18)

# --- Config ---
PLAYER_SPEED = 260  # px/sec
PLAYER_RADIUS = 14
BULLET_SPEED = 900
BULLET_LIFETIME = 1.2
FIRE_RATE = 0.18  # seconds between shots
BOT_FIRE_RATE = 0.5
BOT_SPEED = 160
ROUND_TIME = 90  # seconds
RESPAWN_DELAY = 3  # seconds

# Colors
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
RED = (220, 60, 60)
GREEN = (60, 200, 80)
BLUE = (80, 160, 220)
YELLOW = (240, 220, 80)
GRAY = (120, 120, 120)
SMOKE_COLOR = (80, 80, 100, 160)


# --- Helper functions ---
def clamp(n, a, b):
    return max(a, min(b, n))


def vec_len(v):
    return math.hypot(v[0], v[1])


def normalize(v):
    l = vec_len(v)
    if l == 0:
        return (0, 0)
    return (v[0] / l, v[1] / l)


# --- Game Objects ---
class Bullet:
    def __init__(self, pos, vel, owner, damage=34):
        self.pos = list(pos)
        self.vel = vel
        self.owner = owner
        self.spawn = pygame.time.get_ticks() / 1000.0
        self.damage = damage

    def update(self, dt):
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt

    def is_expired(self, now):
        return now - self.spawn > BULLET_LIFETIME


class Ability:
    def __init__(self, name, cooldown):
        self.name = name
        self.cooldown = cooldown
        self.last = -999

    def ready(self, now):
        return now - self.last >= self.cooldown

    def trigger(self, now):
        self.last = now


class Player:
    def __init__(self, x, y, color=BLUE, name="Player"):
        self.pos = [x, y]
        self.vel = [0, 0]
        self.color = color
        self.angle = 0
        self.hp = 100
        self.max_hp = 100
        self.radius = PLAYER_RADIUS
        self.fire_cooldown = 0
        self.name = name
        self.kills = 0
        self.deaths = 0
        self.alive = True
        self.respawn_time = 0
        # Abilities:
        self.dash = Ability("Dash", 6.0)
        self.smoke = Ability("Smoke", 12.0)
        self.shield = Ability("Shield", 15.0)
        self.shield_active_until = -1
        self.smokes = []  # active smoke circles (x,y,r,expiry)

    def update(self, dt, now):
        if not self.alive:
            if now >= self.respawn_time:
                self.respawn()
            return
        # apply movement
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        # clamp to map
        self.pos[0] = clamp(self.pos[0], 16, WIDTH - 16)
        self.pos[1] = clamp(self.pos[1], 16, HEIGHT - 16)
        # fire cooldown
        self.fire_cooldown = max(0, self.fire_cooldown - dt)
        # shield duration check
        if now > self.shield_active_until:
            self.shield_active_until = -1
        # remove expired smokes
        self.smokes = [s for s in self.smokes if s[3] > now]

    def respawn(self):
        self.hp = self.max_hp
        self.alive = True
        # place in random spawn area
        self.pos = [random.choice([80, WIDTH - 80]), random.randint(80, HEIGHT - 80)]
        self.shield_active_until = -1

    def take_damage(self, dmg, now):
        if self.shield_active_until > now:
            dmg = dmg * 0.45  # shield reduces damage
        self.hp -= dmg
        if self.hp <= 0 and self.alive:
            self.die(now)

    def die(self, now):
        self.alive = False
        self.deaths += 1
        self.respawn_time = now + RESPAWN_DELAY


# Simple map obstacles (axis-aligned rectangles)
walls = [
    pygame.Rect(300, 120, 40, 280),  # vertical wall
    pygame.Rect(600, 350, 420, 40),  # horizontal wall
    pygame.Rect(900, 70, 40, 180),
    pygame.Rect(120, 470, 220, 40),
]

# Game state
player = Player(120, HEIGHT // 2, color=BLUE, name="You")
bots = []
bullets = []
now_time = lambda: pygame.time.get_ticks() / 1000.0


def spawn_bot():
    x = random.choice([WIDTH - 60, 60])
    y = random.randint(60, HEIGHT - 60)
    b = Player(x, y, color=RED, name="Bot")
    b.kills = 0
    bots.append(b)


for _ in range(3):
    spawn_bot()

round_start = now_time()
round_end = round_start + ROUND_TIME


# AI simple behavior
def bot_ai(bot, dt, now):
    if not bot.alive:
        return
    target = player
    dirv = (target.pos[0] - bot.pos[0], target.pos[1] - bot.pos[1])
    dist = vec_len(dirv)
    if dist > 200:
        nd = normalize(dirv)
        bot.vel[0] = nd[0] * BOT_SPEED
        bot.vel[1] = nd[1] * BOT_SPEED
    else:
        ang = math.atan2(dirv[1], dirv[0]) + math.pi / 2
        bot.vel[0] = math.cos(ang) * (BOT_SPEED * 0.55)
        bot.vel[1] = math.sin(ang) * (BOT_SPEED * 0.55)

    if dist < 520:
        if getattr(bot, "bot_last_shot", 0) + BOT_FIRE_RATE <= now:
            shoot_from(bot, target.pos, now, spread=6)
            bot.bot_last_shot = now


def shoot_from(shooter, target_pos, now, spread=3):
    if not shooter.alive:
        return
    if shooter.fire_cooldown > 0:
        return
    dx = target_pos[0] - shooter.pos[0]
    dy = target_pos[1] - shooter.pos[1]
    base = normalize((dx, dy))
    angle = math.atan2(base[1], base[0])
    angle += math.radians(random.uniform(-spread, spread))
    vel = (math.cos(angle) * BULLET_SPEED, math.sin(angle) * BULLET_SPEED)
    bullets.append(Bullet(shooter.pos[:], vel, shooter))
    shooter.fire_cooldown = FIRE_RATE


def handle_player_shoot(mouse_pos, now):
    if not player.alive:
        return
    if player.fire_cooldown > 0:
        return
    shoot_from(player, mouse_pos, now, spread=2)


def bullet_hits_wall(b):
    for w in walls:
        if w.collidepoint(b.pos[0], b.pos[1]):
            return True
    return False


def bullet_hits_player(b, p, now):
    if not p.alive:
        return False
    dx = b.pos[0] - p.pos[0]
    dy = b.pos[1] - p.pos[1]
    return dx * dx + dy * dy <= (p.radius) ** 2


def draw_text(surf, text, x, y, color=WHITE):
    surf.blit(FONT.render(text, True, color), (x, y))


# Main loop
running = True
mouse_down = False

while running:
    dt = clock.tick(60) / 1000.0
    now = now_time()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_down = True
            elif event.button == 3:
                if player.smoke.ready(now):
                    mx, my = pygame.mouse.get_pos()
                    player.smokes.append([mx, my, 120, now + 8.0])
                    player.smoke.trigger(now)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_down = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if player.dash.ready(now) and player.alive:
                    mx, my = pygame.mouse.get_pos()
                    dirv = normalize((mx - player.pos[0], my - player.pos[1]))
                    dash_dist = 180
                    player.pos[0] += dirv[0] * dash_dist
                    player.pos[1] += dirv[1] * dash_dist
                    player.dash.trigger(now)
            elif event.key == pygame.K_q:
                if player.shield.ready(now):
                    player.shield.trigger(now)
                    player.shield_active_until = now + 4.0
            elif event.key == pygame.K_r:
                if not player.alive:
                    player.respawn()

    # keyboard movement
    if player.alive:
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()
        player.angle = math.atan2(my - player.pos[1], mx - player.pos[0])
        vx = vy = 0
        if keys[pygame.K_w]:
            vy -= 1
        if keys[pygame.K_s]:
            vy += 1
        if keys[pygame.K_a]:
            vx -= 1
        if keys[pygame.K_d]:
            vx += 1
        norm = normalize((vx, vy))
        player.vel[0] = norm[0] * PLAYER_SPEED
        player.vel[1] = norm[1] * PLAYER_SPEED
    else:
        player.vel = [0, 0]

    if mouse_down:
        handle_player_shoot(pygame.mouse.get_pos(), now)

    player.update(dt, now)

    for b in bots:
        bot_ai(b, dt, now)
        b.update(dt, now)

    for b in bullets[:]:
        b.update(dt)
        if b.is_expired(now) or bullet_hits_wall(b):
            bullets.remove(b)
            continue
        targets = [player] + bots
        for t in targets:
            if t is b.owner:
                continue
            if bullet_hits_player(b, t, now):
                t.take_damage(b.damage, now)
                if not t.alive:
                    b.owner.kills += 1
                try:
                    bullets.remove(b)
                except ValueError:
                    pass
                break

    if now >= round_end:
        for ent in [player] + bots:
            ent.alive = True
            ent.respawn_time = 0
            ent.hp = ent.max_hp
            ent.pos = [random.randint(80, WIDTH - 80), random.randint(80, HEIGHT - 80)]
        bullets.clear()
        round_start = now
        round_end = round_start + ROUND_TIME

    # --- Drawing ---
    screen.fill((20, 20, 30))
    for w in walls:
        pygame.draw.rect(screen, GRAY, w)

    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for s in player.smokes:
        pygame.draw.circle(surf, SMOKE_COLOR, (int(s[0]), int(s[1])), int(s[2]))
    screen.blit(surf, (0, 0))

    for b in bullets:
        pygame.draw.circle(screen, YELLOW if b.owner is player else RED, (int(b.pos[0]), int(b.pos[1])), 4)

    for b in bots:
        if b.alive:
            pygame.draw.circle(screen, b.color, (int(b.pos[0]), int(b.pos[1])), b.radius)
            hpw = int((b.hp / b.max_hp) * (b.radius * 2))
            pygame.draw.rect(screen, BLACK, (b.pos[0] - b.radius, b.pos[1] - b.radius - 8, b.radius * 2, 6))
            pygame.draw.rect(screen, GREEN, (b.pos[0] - b.radius, b.pos[1] - b.radius - 8, hpw, 6))

    if player.alive:
        pygame.draw.circle(screen, player.color, (int(player.pos[0]), int(player.pos[1])), player.radius)
        muzzle = (
            player.pos[0] + math.cos(player.angle) * player.radius * 1.6,
            player.pos[1] + math.sin(player.angle) * player.radius * 1.6,
        )
        pygame.draw.line(screen, WHITE, player.pos, muzzle, 3)
        if player.shield_active_until > now:
            a = int(120 * (player.shield_active_until - now) / 4.0)
            pygame.draw.circle(
                screen,
                (180, 220, 255, a),
                (int(player.pos[0]), int(player.pos[1])),
                int(player.radius * 1.8),
                2,
            )
        hpw = int((player.hp / player.max_hp) * 80)
        pygame.draw.rect(screen, BLACK, (10, HEIGHT - 38, 84, 16))
        pygame.draw.rect(screen, GREEN, (12, HEIGHT - 36, hpw, 12))

    draw_text(screen, f"HP: {int(player.hp)}  Kills: {player.kills}  Deaths: {player.deaths}", 10, HEIGHT - 66)
    draw_text(screen, f"Round ends in: {int(round_end - now)}s", WIDTH - 220, 10)
    cd_dash = max(0, round(player.dash.cooldown - (now - player.dash.last), 1)) if not player.dash.ready(now) else 0
    draw_text(screen, f"[SPACE] Dash cd: {cd_dash if cd_dash>0 else 'Ready'}", 10, 10)
    draw_text(
        screen, f"[RMB] Smoke cd: {int(max(0, player.smoke.cooldown - (now - player.smoke.last)))}", 10, 30
    )
    draw_text(
        screen, f"[Q] Shield cd: {int(max(0, player.shield.cooldown - (now - player.shield.last)))}", 10, 50
    )
    draw_text(screen, "Shoot: LMB | Dash: SPACE | Smoke: RMB | Shield: Q", WIDTH // 2 - 180, HEIGHT - 30)

    y = 10
    for b in bots:
        draw_text(screen, f"{b.name} K:{b.kills} D:{b.deaths} HP:{int(b.hp) if b.alive else 'DEAD'}", WIDTH - 260, y)
        y += 20

    pygame.display.flip()

pygame.quit()
