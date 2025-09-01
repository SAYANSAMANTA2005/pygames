# valorant.py
# Mini-Valorant prototype (extended): improved UI, weapon switching, agent on-kill abilities,
# and robust bullet-wall collision (segment-vs-rect).
# Requires pygame: pip install pygame

import pygame
import math
import random
import time 
from collections import deque

pygame.init()
WIDTH, HEIGHT = 1200, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini-Valorant (Top-down prototype) — Extended")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 18)
BIG_FONT = pygame.font.SysFont("consolas", 28)

# --- Config ---
PLAYER_SPEED = 260  # px/sec
PLAYER_RADIUS = 14
BULLET_SPEED = 1200  # increased bullet speed to highlight tunneling problem fix
BULLET_LIFETIME = 1.2
FIRE_RATE = 0.18  # default; weapons override
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
PANEL_BG = (18, 18, 22)
ACCENT = (120, 170, 255)

# --- Helpers ---
def clamp(n, a, b):
    return max(a, min(b, n))


def vec_len(v):
    return math.hypot(v[0], v[1])


def normalize(v):
    l = vec_len(v)
    if l == 0:
        return (0, 0)
    return (v[0] / l, v[1] / l)


# Segment intersection helper (for bullet-wall)
def seg_intersect(a1, a2, b1, b2):
    # a1,a2,b1,b2 = (x,y)
    (x1, y1), (x2, y2) = a1, a2
    (x3, y3), (x4, y4) = b1, b2

    den = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    if den == 0:
        return False
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / den
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / den
    return 0 <= ua <= 1 and 0 <= ub <= 1


def seg_rect_intersect(p1, p2, rect):
    # check segment p1-p2 intersects any rect edge
    rpts = [
        (rect.left, rect.top),
        (rect.right, rect.top),
        (rect.right, rect.bottom),
        (rect.left, rect.bottom),
    ]
    edges = [ (rpts[i], rpts[(i+1)%4]) for i in range(4) ]
    for e in edges:
        if seg_intersect(p1, p2, e[0], e[1]):
            return True
    # also if segment is completely inside rect
    if rect.collidepoint(p1) or rect.collidepoint(p2):
        return True
    return False


# --- Weapon system ---
class Weapon:
    def __init__(self, name, dmg, fire_rate, spread_deg, mag, reload_time):
        self.name = name
        self.dmg = dmg
        self.fire_rate = fire_rate
        self.spread_deg = spread_deg
        self.mag = mag
        self.reload_time = reload_time
        self.cur_mag = mag
        self.last_shot = -999
        self.reloading_until = -1

    def ready(self, now):
        if self.reloading_until > now:
            return False
        return (now - self.last_shot) >= self.fire_rate and self.cur_mag > 0

    def shoot(self, owner, target_pos, now):
        if self.reloading_until > now:
            return None
        if self.cur_mag <= 0:
            return None
        self.last_shot = now
        self.cur_mag -= 1
        dx = target_pos[0] - owner.pos[0]
        dy = target_pos[1] - owner.pos[1]
        base = normalize((dx, dy))
        angle = math.atan2(base[1], base[0])
        angle += math.radians(random.uniform(-self.spread_deg, self.spread_deg))
        vel = (math.cos(angle) * BULLET_SPEED, math.sin(angle) * BULLET_SPEED)
        return Bullet(owner.pos[:], vel, owner, damage=self.dmg, created_now=now)

    def start_reload(self, now):
        if self.cur_mag == self.mag or self.reloading_until > now:
            return
        self.reloading_until = now + self.reload_time

    def finish_reload_if_needed(self, now):
        if self.reloading_until > 0 and now >= self.reloading_until:
            self.cur_mag = self.mag
            self.reloading_until = -1


# --- Game Objects ---
class Bullet:
    def __init__(self, pos, vel, owner, damage=34, created_now=None):
        self.pos = list(pos)
        self.prev_pos = list(pos)
        self.vel = vel
        self.owner = owner
        self.spawn = created_now if created_now is not None else pygame.time.get_ticks() / 1000.0
        self.damage = damage

    def update(self, dt):
        self.prev_pos[0] = self.pos[0]
        self.prev_pos[1] = self.pos[1]
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
    def __init__(self, x, y, color=BLUE, name="Player", agent="Phoenix"):
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
        # Weapon inventory
        self.weapons = {
            "Vandal": Weapon("Vandal", dmg=38, fire_rate=0.18, spread_deg=2.5, mag=25, reload_time=2.5),
            "Phantom": Weapon("Phantom", dmg=34, fire_rate=0.14, spread_deg=2.2, mag=30, reload_time=2.3),
            "Sheriff": Weapon("Sheriff", dmg=95, fire_rate=0.55, spread_deg=4.5, mag=6, reload_time=2.0),
        }
        self.weapon_order = ["Vandal", "Phantom", "Sheriff"]
        self.cur_weapon_idx = 0
        self.agent = agent
        # agent-specific state
        self.revealed_until = -1  # for Sova: reveals bots
        self.kill_feed = None

    @property
    def weapon(self):
        return self.weapons[self.weapon_order[self.cur_weapon_idx]]

    def switch_weapon(self, idx):
        if 0 <= idx < len(self.weapon_order):
            self.cur_weapon_idx = idx

    def update(self, dt, now):
        if not self.alive:
            if now >= self.respawn_time:
                self.respawn()
            return
        # movement
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.pos[0] = clamp(self.pos[0], 16, WIDTH - 16)
        self.pos[1] = clamp(self.pos[1], 16, HEIGHT - 16)
        # shield
        if now > self.shield_active_until:
            self.shield_active_until = -1
        # remove expired smokes
        self.smokes = [s for s in self.smokes if s[3] > now]
        # weapon reload finish
        for w in self.weapons.values():
            w.finish_reload_if_needed(now)

    def respawn(self):
        self.hp = self.max_hp
        self.alive = True
        self.pos = [random.choice([80, WIDTH - 80]), random.randint(80, HEIGHT - 80)]
        self.shield_active_until = -1

    def take_damage(self, dmg, now):
        if self.shield_active_until > now:
            dmg = dmg * 0.45
        self.hp -= dmg
        if self.hp <= 0 and self.alive:
            self.die(now)

    def die(self, now):
        self.alive = False
        self.deaths += 1
        self.respawn_time = now + RESPAWN_DELAY

    def on_kill(self, victim, now, game_state):
        # Agent-specific on-kill effects
        if self.agent == "Phoenix":
            # heal 25 hp on kill
            self.hp = clamp(self.hp + 25, 0, self.max_hp)
            game_state.add_killfeed(f"{self.name} (Phoenix) healed +25")
        elif self.agent == "Jett":
            # refresh dash cooldown
            self.dash.last = -999
            game_state.add_killfeed(f"{self.name} (Jett) dash refreshed")
        elif self.agent == "Sova":
            # reveal nearby bots briefly
            self.revealed_until = now + 3.0
            game_state.add_killfeed(f"{self.name} (Sova) revealed nearby enemies")


# Simple map obstacles (axis-aligned rectangles)
walls = [
    pygame.Rect(300, 120, 40, 280),
    pygame.Rect(600, 350, 420, 40),
    pygame.Rect(900, 70, 40, 180),
    pygame.Rect(120, 470, 220, 40),
]

# Game state container for helper functions like killfeed
class GameState:
    def __init__(self):
        self.player = Player(120, HEIGHT // 2, color=BLUE, name="You", agent="Phoenix")
        self.bots = []
        self.bullets = []
        self.round_start = pygame.time.get_ticks() / 1000.0
        self.round_end = self.round_start + ROUND_TIME
        self.killfeed = deque(maxlen=6)  # recent messages
        self.last_kill_time = 0

    def spawn_bot(self):
        x = random.choice([WIDTH - 60, 60])
        y = random.randint(60, HEIGHT - 60)
        b = Player(x, y, color=RED, name="Bot", agent="BotAgent")
        b.kills = 0
        self.bots.append(b)

    def add_killfeed(self, s):
        ts = time.strftime("%H:%M:%S")
        self.killfeed.appendleft(f"[{ts}] {s}")

game_state = GameState()
for _ in range(3):
    game_state.spawn_bot()

now_time = lambda: pygame.time.get_ticks() / 1000.0

# AI
def bot_ai(bot, dt, now, gs: GameState):
    if not bot.alive:
        return
    target = gs.player
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
            w = bot.weapon
            if w.cur_mag <= 0 and w.reloading_until < now:
                w.start_reload(now)
            elif w.ready(now):
                b = w.shoot(bot, target.pos, now)
                if b:
                    gs.bullets.append(b)
                bot.bot_last_shot = now


def shoot_from(shooter, target_pos, now, gs: GameState):
    if not shooter.alive:
        return
    w = shooter.weapon
    if w.reloading_until > now:
        return
    if w.cur_mag <= 0:
        w.start_reload(now)
        return
    if not w.ready(now):
        return
    b = w.shoot(shooter, target_pos, now)
    if b:
        gs.bullets.append(b)


def handle_player_shoot(mouse_pos, now, gs: GameState):
    p = gs.player
    if not p.alive:
        return
    shoot_from(p, mouse_pos, now, gs)


def bullet_hits_player(b, p):
    if not p.alive:
        return False
    dx = b.pos[0] - p.pos[0]
    dy = b.pos[1] - p.pos[1]
    return dx * dx + dy * dy <= (p.radius) ** 2


# --- Drawing helpers for improved UI ---
def draw_panel(surf, rect, color=PANEL_BG, border=2, radius=6):
    pygame.draw.rect(surf, color, rect)
    pygame.draw.rect(surf, ACCENT, rect, border)


def draw_text(surf, text, x, y, color=WHITE, font=FONT):
    surf.blit(font.render(text, True, color), (x, y))


def draw_crosshair(surf, pos, spread_px=0):
    x, y = pos
    # center dot
    pygame.draw.circle(surf, WHITE, (int(x), int(y)), 2)
    # four lines
    gap = 10 + spread_px
    length = 8
    pygame.draw.line(surf, WHITE, (x - gap - length, y), (x - gap, y), 2)
    pygame.draw.line(surf, WHITE, (x + gap + length, y), (x + gap, y), 2)
    pygame.draw.line(surf, WHITE, (x, y - gap - length), (x, y - gap), 2)
    pygame.draw.line(surf, WHITE, (x, y + gap + length), (x, y + gap), 2)


# Main loop
running = True
mouse_down = False

while running:
    dt = clock.tick(60) / 1000.0
    now = now_time()
    gs = game_state
    player = gs.player

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
                # reload current weapon
                player.weapon.start_reload(now)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = {pygame.K_1:0, pygame.K_2:1, pygame.K_3:2}[event.key]
                player.switch_weapon(idx)
            elif event.key == pygame.K_F1:
                player.agent = "Phoenix"
                gs.add_killfeed("Switched to Phoenix (on-kill: heal)")
            elif event.key == pygame.K_F2:
                player.agent = "Jett"
                gs.add_killfeed("Switched to Jett (on-kill: dash refresh)")
            elif event.key == pygame.K_F3:
                player.agent = "Sova"
                gs.add_killfeed("Switched to Sova (on-kill: reveal)")
            elif event.key == pygame.K_e:
                # manual: use small local action (plant test): smoke thrown
                if player.smoke.ready(now):
                    mx, my = pygame.mouse.get_pos()
                    player.smokes.append([mx, my, 120, now + 8.0])
                    player.smoke.trigger(now)

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

    # Handle firing
    if mouse_down:
        handle_player_shoot(pygame.mouse.get_pos(), now, gs)

    # Update player
    player.update(dt, now)

    # Update bots
    for b in gs.bots:
        bot_ai(b, dt, now, gs)
        b.update(dt, now)

    # Update bullets with segment-vs-rect checks
    for b in gs.bullets[:]:
        b.update(dt)
        # check lifetime
        if b.is_expired(now):
            gs.bullets.remove(b)
            continue
        # check segment intersection with walls (prevents tunneling)
        hit_wall = False
        for w in walls:
            if seg_rect_intersect(tuple(b.prev_pos), tuple(b.pos), w):
                hit_wall = True
                break
        if hit_wall:
            try:
                gs.bullets.remove(b)
            except ValueError:
                pass
            continue
        # collision with players
        targets = [player] + gs.bots
        hit_any = False
        for t in targets:
            if t is b.owner:
                continue
            if bullet_hits_player(b, t):
                t.take_damage(b.damage, now)
                # awarding kill if died
                if not t.alive:
                    b.owner.kills += 1
                    b.owner.on_kill(t, now, gs)
                    gs.add_killfeed(f"{b.owner.name} killed {t.name}")
                try:
                    gs.bullets.remove(b)
                except ValueError:
                    pass
                hit_any = True
                break
        if hit_any:
            continue

    # Round timer
    if now >= gs.round_end:
        for ent in [gs.player] + gs.bots:
            ent.alive = True
            ent.respawn_time = 0
            ent.hp = ent.max_hp
            ent.pos = [random.randint(80, WIDTH - 80), random.randint(80, HEIGHT - 80)]
        gs.bullets.clear()
        gs.round_start = now
        gs.round_end = gs.round_start + ROUND_TIME
        gs.add_killfeed("Round reset")

    # --- Drawing ---
    screen.fill((12, 14, 18))

    # draw walls
    for w in walls:
        pygame.draw.rect(screen, GRAY, w)

    # smokes (player)
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for s in player.smokes:
        pygame.draw.circle(surf, SMOKE_COLOR, (int(s[0]), int(s[1])), int(s[2]))
    screen.blit(surf, (0, 0))

    # bullets
    for b in gs.bullets:
        col = YELLOW if b.owner is player else RED
        pygame.draw.circle(screen, col, (int(b.pos[0]), int(b.pos[1])), 4)

    # bots
    for b in gs.bots:
        if b.alive:
            highlight = (b.revealed_until > now and player.revealed_until > now)
            draw_col = (255, 170, 170) if highlight else b.color
            pygame.draw.circle(screen, draw_col, (int(b.pos[0]), int(b.pos[1])), b.radius)
            hpw = int((b.hp / b.max_hp) * (b.radius * 2))
            pygame.draw.rect(screen, BLACK, (b.pos[0] - b.radius, b.pos[1] - b.radius - 8, b.radius * 2, 6))
            pygame.draw.rect(screen, GREEN, (b.pos[0] - b.radius, b.pos[1] - b.radius - 8, hpw, 6))
        else:
            # draw a faint dead marker
            pygame.draw.circle(screen, (60,60,60), (int(b.pos[0]), int(b.pos[1])), b.radius, 1)

    # player
    if player.alive:
        pygame.draw.circle(screen, player.color, (int(player.pos[0]), int(player.pos[1])), player.radius)
        muzzle = (
            player.pos[0] + math.cos(player.angle) * player.radius * 1.6,
            player.pos[1] + math.sin(player.angle) * player.radius * 1.6,
        )
        pygame.draw.line(screen, WHITE, player.pos, muzzle, 3)
        if player.shield_active_until > now:
            a = int(120 * (player.shield_active_until - now) / 4.0)
            # shield ring
            surf2 = pygame.Surface((int(player.radius*4), int(player.radius*4)), pygame.SRCALPHA)
            pygame.draw.circle(surf2, (180,220,255,a), (int(player.radius*2), int(player.radius*2)), int(player.radius*1.8), 2)
            screen.blit(surf2, (int(player.pos[0]-player.radius*2), int(player.pos[1]-player.radius*2)))
        # hp bar
        hpw = int((player.hp / player.max_hp) * 160)
        pygame.draw.rect(screen, BLACK, (16, HEIGHT - 64, 168, 20))
        pygame.draw.rect(screen, GREEN, (18, HEIGHT - 62, hpw, 16))
        pygame.draw.rect(screen, WHITE, (16, HEIGHT - 64, 168, 20), 2)

    # HUD left panel (rounded simplified)
    hud_rect = pygame.Rect(8, HEIGHT - 110, 360, 96)
    draw_panel(screen, hud_rect)
    draw_text(screen, f"HP: {int(player.hp)}/{player.max_hp}", 26, HEIGHT - 104)
    draw_text(screen, f"Agent: {player.agent}", 26, HEIGHT - 82)
    # weapon box
    wrect = pygame.Rect(220, HEIGHT - 96, 128, 72)
    pygame.draw.rect(screen, (22,22,26), wrect)
    pygame.draw.rect(screen, ACCENT, wrect, 2)
    draw_text(screen, f"Weapon: {player.weapon.name}", 232, HEIGHT - 92)
    draw_text(screen, f"Ammo: {player.weapon.cur_mag}/{player.weapon.mag}", 232, HEIGHT - 72)
    # ability cooldown bars
    def cooldown_bar(x,y, label, ability, width=140, height=8):
        cd = max(0, ability.cooldown - (now - ability.last))
        frac = 1 - (cd / ability.cooldown) if ability.cooldown>0 else 1
        frac = clamp(frac, 0, 1)
        pygame.draw.rect(screen, (30,30,30), (x,y,width,height))
        pygame.draw.rect(screen, ACCENT, (x,y,int(width*frac),height))
        draw_text(screen, f"{label} {'Ready' if ability.ready(now) else int(cd)}s", x, y-16)
    cooldown_bar(26, HEIGHT - 46, "Dash (SPACE)", player.dash)
    cooldown_bar(26, HEIGHT - 30, "Shield (Q)", player.shield)

    # center crosshair
    # spread indicator based on weapon spread
    spread_px = int(player.weapon.spread_deg * 0.8)
    draw_crosshair(screen, pygame.mouse.get_pos(), spread_px)

    # right-top killfeed panel
    kx, ky = WIDTH - 420, 16
    krect = pygame.Rect(kx, ky, 400, 140)
    pygame.draw.rect(screen, (14,14,18), krect)
    pygame.draw.rect(screen, ACCENT, krect, 2)
    draw_text(screen, "Killfeed", kx+10, ky+6, font=BIG_FONT)
    i = 0
    for msg in gs.killfeed:
        draw_text(screen, msg, kx+10, ky+40 + i*18, color=WHITE)
        i += 1

    # bottom center round timer + info
    draw_text(screen, f"Round ends in: {int(gs.round_end - now)}s", WIDTH//2 - 90, 12)
    draw_text(screen, f"Kills: {player.kills}  Deaths: {player.deaths}", WIDTH//2 - 90, 36)

    # weapon switch hints
    draw_text(screen, "Switch weapon: [1] Vandal  [2] Phantom  [3] Sheriff  | Reload: R | Agents: F1/F2/F3", 16, 16)

    # bots scoreboard
    y = 160
    for b in gs.bots:
        draw_text(screen, f"{b.name} K:{b.kills} D:{b.deaths} HP:{int(b.hp) if b.alive else 'DEAD'}", WIDTH - 200, y)
        y += 22

    pygame.display.flip()

pygame.quit()
