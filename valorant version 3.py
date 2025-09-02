# valorant_improved.py
# Extended Mini-Valorant prototype
# - Transparent HUD
# - Player/bot cannot cross walls (per-axis collision)
# - Bullets cannot cross walls (segment-vs-rect)
# - Multiple guns (unique damage/fire rate/bullet speed)
# - Player can heal up to 3 times per round with 'H'
# - Human-shaped players (body/head/legs) and visible gun
#
# Requires: pygame
# pip install pygame

import pygame
import math
import random
import time
from collections import deque

pygame.init()
WIDTH, HEIGHT = 1400, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mini-Valorant (Improved)")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 18)
BIG_FONT = pygame.font.SysFont("consolas", 24)

# --- Config ---
PLAYER_SPEED = 260
PLAYER_RADIUS = 14  # collision radius used for movement/wall checks
BULLET_LIFETIME = 1.2
BOT_SPEED = 160
ROUND_TIME = 90
RESPAWN_DELAY = 3

# Colors
WHITE = (245, 245, 245)
BLACK = (10, 10, 10)
RED = (220, 60, 60)
GREEN = (60, 200, 80)
BLUE = (80, 160, 220)
YELLOW = (240, 220, 80)
GRAY = (120, 120, 120)
SMOKE_COLOR = (80, 80, 100, 140)
PANEL_BG = (18, 18, 22, 160)  # include alpha for transparency
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
    return (v[0]/l, v[1]/l)

# Segment intersection helper (bullet vs rect)
def seg_intersect(a1, a2, b1, b2):
    (x1,y1),(x2,y2)=a1,a2
    (x3,y3),(x4,y4)=b1,b2
    den = (y4-y3)*(x2-x1) - (x4-x3)*(y2-y1)
    if den == 0:
        return False
    ua = ((x4-x3)*(y1-y3) - (y4-y3)*(x1-x3))/den
    ub = ((x2-x1)*(y1-y3) - (y2-y1)*(x1-x3))/den
    return 0<=ua<=1 and 0<=ub<=1

def seg_rect_intersect(p1,p2,rect):
    rpts = [(rect.left,rect.top),(rect.right,rect.top),(rect.right,rect.bottom),(rect.left,rect.bottom)]
    edges = [ (rpts[i], rpts[(i+1)%4]) for i in range(4) ]
    for e in edges:
        if seg_intersect(p1,p2,e[0],e[1]):
            return True
    # also if either end inside rect
    if rect.collidepoint(p1) or rect.collidepoint(p2):
        return True
    return False

# Circle-rect collision (for player/bot)
def circle_rect_collision(circle_pos, r, rect):
    cx, cy = circle_pos
    closest_x = clamp(cx, rect.left, rect.right)
    closest_y = clamp(cy, rect.top, rect.bottom)
    dx = cx - closest_x
    dy = cy - closest_y
    return dx*dx + dy*dy < r*r

# --- Weapon ---
class Weapon:
    def __init__(self, name, dmg, fire_rate, spread_deg, mag, reload_time, bullet_speed):
        self.name = name
        self.dmg = dmg
        self.fire_rate = fire_rate
        self.spread_deg = spread_deg
        self.mag = mag
        self.reload_time = reload_time
        self.bullet_speed = bullet_speed
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
        vel = (math.cos(angle)*self.bullet_speed, math.sin(angle)*self.bullet_speed)
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
        self.spawn = created_now if created_now is not None else pygame.time.get_ticks()/1000.0
        self.damage = damage

    def update(self, dt):
        self.prev_pos[0] = self.pos[0]
        self.prev_pos[1] = self.pos[1]
        self.pos[0] += self.vel[0]*dt
        self.pos[1] += self.vel[1]*dt

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
        self.pos = [x,y]
        self.vel = [0,0]
        self.color = color
        self.angle = 0
        self.hp = 100
        self.max_hp = 100
        self.radius = PLAYER_RADIUS
        self.name = name
        self.kills = 0
        self.deaths = 0
        self.alive = True
        self.respawn_time = 0
        self.dash = Ability("Dash", 6.0)
        self.smoke = Ability("Smoke", 12.0)
        self.shield = Ability("Shield", 15.0)
        self.shield_active_until = -1
        self.smokes = []
        # medkits per round (max 3)
        self.medkits = 3
        # weapons (unique damage / speed)
        self.weapons = {
            "Vandal": Weapon("Vandal", dmg=38, fire_rate=0.18, spread_deg=2.5, mag=25, reload_time=2.5, bullet_speed=1200),
            "Phantom": Weapon("Phantom", dmg=34, fire_rate=0.14, spread_deg=2.0, mag=30, reload_time=2.3, bullet_speed=1100),
            "Sheriff": Weapon("Sheriff", dmg=95, fire_rate=0.55, spread_deg=5.0, mag=6, reload_time=2.0, bullet_speed=1600),
        }
        self.weapon_order = ["Vandal","Phantom","Sheriff"]
        self.cur_weapon_idx = 0
        self.agent = agent
        # agent-specific
        self.revealed_until = -1

    @property
    def weapon(self):
        return self.weapons[self.weapon_order[self.cur_weapon_idx]]

    def switch_weapon(self, idx):
        if 0 <= idx < len(self.weapon_order):
            self.cur_weapon_idx = idx

    def update(self, dt, now, walls_list):
        if not self.alive:
            if now >= self.respawn_time:
                self.respawn()
            return
        # Try per-axis movement with collision prevention
        # Intended new positions
        new_x = self.pos[0] + self.vel[0]*dt
        new_y = self.pos[1] + self.vel[1]*dt
        # X axis
        collided_x = False
        for w in walls_list:
            if circle_rect_collision((new_x, self.pos[1]), self.radius, w):
                collided_x = True
                break
        if not collided_x:
            self.pos[0] = clamp(new_x, 16, WIDTH-16)
        # Y axis
        collided_y = False
        for w in walls_list:
            if circle_rect_collision((self.pos[0], new_y), self.radius, w):
                collided_y = True
                break
        if not collided_y:
            self.pos[1] = clamp(new_y, 16, HEIGHT-16)

        # shield end
        if now > self.shield_active_until:
            self.shield_active_until = -1
        # remove expired smokes
        self.smokes = [s for s in self.smokes if s[3] > now]
        # finish reloads
        for w in self.weapons.values():
            w.finish_reload_if_needed(now)

    def respawn(self):
        self.hp = self.max_hp
        self.alive = True
        self.pos = [random.choice([80, WIDTH-80]), random.randint(80, HEIGHT-80)]
        self.shield_active_until = -1
        self.medkits = 3

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

    def on_kill(self, victim, now):
        if self.agent == "Phoenix":
            self.hp = clamp(self.hp + 25, 0, self.max_hp)
        elif self.agent == "Jett":
            self.dash.last = -999
        elif self.agent == "Sova":
            self.revealed_until = now + 3.0

# Walls (rectangles)
walls = [
    pygame.Rect(300,120,40,280),
    pygame.Rect(600,350,420,40),
    pygame.Rect(900,70,40,180),
    pygame.Rect(120,470,220,40),
]

# Small game state
class GameState:
    def __init__(self):
        self.player = Player(120, HEIGHT//2, color=BLUE, name="You", agent="Phoenix")
        self.bots = []
        self.bullets = []
        self.round_start = pygame.time.get_ticks()/1000.0
        self.round_end = self.round_start + ROUND_TIME
        self.killfeed = deque(maxlen=6)

    def spawn_bot(self):
        x = random.choice([WIDTH-60, 60])
        y = random.randint(60, HEIGHT-60)
        b = Player(x,y,color=RED,name="Bot",agent="BotAgent")
        b.kills = 0
        self.bots.append(b)

    def add_killfeed(self, s):
        ts = time.strftime("%H:%M:%S")
        self.killfeed.appendleft(f"[{ts}] {s}")

gs = GameState()
for _ in range(3):
    gs.spawn_bot()

now_time = lambda: pygame.time.get_ticks()/1000.0

# AI
def bot_ai(bot, dt, now, gs):
    if not bot.alive:
        return
    target = gs.player
    dirv = (target.pos[0]-bot.pos[0], target.pos[1]-bot.pos[1])
    dist = vec_len(dirv)
    if dist > 200:
        nd = normalize(dirv)
        bot.vel[0] = nd[0] * BOT_SPEED
        bot.vel[1] = nd[1] * BOT_SPEED
    else:
        ang = math.atan2(dirv[1], dirv[0]) + math.pi/2
        bot.vel[0] = math.cos(ang)*(BOT_SPEED*0.55)
        bot.vel[1] = math.sin(ang)*(BOT_SPEED*0.55)

    if dist < 520:
        if getattr(bot,'bot_last_shot',0) + 0.5 <= now:
            w = bot.weapon
            if w.cur_mag <= 0 and w.reloading_until < now:
                w.start_reload(now)
            elif w.ready(now):
                b = w.shoot(bot, target.pos, now)
                if b:
                    gs.bullets.append(b)
                bot.bot_last_shot = now

# Shoot helpers
def shoot_from(shooter, target_pos, now, gs):
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

def handle_player_shoot(mouse_pos, now, gs):
    shoot_from(gs.player, mouse_pos, now, gs)

def bullet_hits_player(b, p):
    if not p.alive:
        return False
    dx = b.pos[0]-p.pos[0]
    dy = b.pos[1]-p.pos[1]
    return dx*dx + dy*dy <= (p.radius)**2

# Drawing helpers
def draw_transparent_panel(surf, rect, color=(18,18,22,160), border=2):
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    panel.fill(color)
    surf.blit(panel, (rect.left, rect.top))
    pygame.draw.rect(surf, ACCENT, rect, border)

def draw_text(surf, text, x, y, color=WHITE, font=FONT):
    surf.blit(font.render(text, True, color), (x,y))

def draw_human(surf, pos, angle, color, name_tag=None, is_dead=False):
    x,y = int(pos[0]), int(pos[1])
    # body (rectangle)
    body_w, body_h = 14, 28
    body_rect = pygame.Rect(0,0,body_w,body_h)
    body_rect.center = (x,y)
    # head
    head_r = 6
    head_pos = (x, y - body_h//2 - head_r)
    # legs (two lines)
    leg_y = y + body_h//2
    # draw body
    bcol = (100,100,100) if is_dead else color
    pygame.draw.rect(surf, bcol, body_rect)
    pygame.draw.circle(surf, bcol, head_pos, head_r)
    pygame.draw.line(surf, bcol, (x-6, leg_y), (x, leg_y+10), 3)
    pygame.draw.line(surf, bcol, (x+6, leg_y), (x, leg_y+10), 3)
    # gun as a rotated rectangle/line extending from chest toward angle
    gun_len = 20
    gx = x + math.cos(angle)*(body_w//2 + gun_len/2)
    gy = y + math.sin(angle)*(0 + gun_len/2)
    # draw gun shaft
    ex = x + math.cos(angle)*(body_w//2 + gun_len)
    ey = y + math.sin(angle)*(body_h//8 + gun_len)
    pygame.draw.line(surf, (30,30,30), (x + math.cos(angle)*6, y + math.sin(angle)*6), (ex,ey), 6)
    if name_tag:
        draw_text(surf, name_tag, x-20, y - body_h - 18, color=WHITE)

# Main loop
running = True
mouse_down = False

while running:
    dt = clock.tick(60)/1000.0
    now = now_time()
    player = gs.player

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_down = True
            elif event.button == 3:
                if player.smoke.ready(now):
                    mx,my = pygame.mouse.get_pos()
                    player.smokes.append([mx,my,120, now + 8.0])
                    player.smoke.trigger(now)
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                mouse_down = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if player.dash.ready(now) and player.alive:
                    mx,my = pygame.mouse.get_pos()
                    dirv = normalize((mx-player.pos[0], my-player.pos[1]))
                    dash_dist = 180
                    # dash must also respect walls: try incremental small steps to avoid teleporting inside walls
                    steps = 8
                    for s in range(1, steps+1):
                        tx = player.pos[0] + dirv[0]*dash_dist*(s/steps)
                        ty = player.pos[1] + dirv[1]*dash_dist*(s/steps)
                        blocked = False
                        for w in walls:
                            if circle_rect_collision((tx, ty), player.radius, w):
                                blocked = True
                                break
                        if blocked:
                            # step back one and stop
                            player.pos[0] = player.pos[0] + dirv[0]*dash_dist*((s-1)/steps)
                            player.pos[1] = player.pos[1] + dirv[1]*dash_dist*((s-1)/steps)
                            break
                        if s==steps:
                            player.pos[0] = tx
                            player.pos[1] = ty
                    player.dash.trigger(now)
            elif event.key == pygame.K_q:
                if player.shield.ready(now):
                    player.shield.trigger(now)
                    player.shield_active_until = now + 4.0
            elif event.key == pygame.K_r:
                player.weapon.start_reload(now)
            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                idx = {pygame.K_1:0, pygame.K_2:1, pygame.K_3:2}[event.key]
                player.switch_weapon(idx)
                gs.add_killfeed(f"Switched to {player.weapon.name}")
            elif event.key == pygame.K_F1:
                player.agent = "Phoenix"; gs.add_killfeed("Switched to Phoenix")
            elif event.key == pygame.K_F2:
                player.agent = "Jett"; gs.add_killfeed("Switched to Jett")
            elif event.key == pygame.K_F3:
                player.agent = "Sova"; gs.add_killfeed("Switched to Sova")
            elif event.key == pygame.K_h:
                # use medkit
                if player.medkits > 0 and player.alive:
                    heal_amount = 35
                    old = player.hp
                    player.hp = clamp(player.hp + heal_amount, 0, player.max_hp)
                    player.medkits -= 1
                    gs.add_killfeed(f"Used medkit: +{player.hp-old} HP ({player.medkits} left)")
            elif event.key == pygame.K_e:
                # another way to throw smoke
                if player.smoke.ready(now):
                    mx,my = pygame.mouse.get_pos()
                    player.smokes.append([mx,my,120, now + 8.0])
                    player.smoke.trigger(now)

    # movement
    if player.alive:
        keys = pygame.key.get_pressed()
        mx,my = pygame.mouse.get_pos()
        player.angle = math.atan2(my - player.pos[1], mx - player.pos[0])
        vx = vy = 0
        if keys[pygame.K_w]: vy -= 1
        if keys[pygame.K_s]: vy += 1
        if keys[pygame.K_a]: vx -= 1
        if keys[pygame.K_d]: vx += 1
        norm = normalize((vx,vy))
        player.vel[0] = norm[0]*PLAYER_SPEED
        player.vel[1] = norm[1]*PLAYER_SPEED
    else:
        player.vel = [0,0]

    if mouse_down:
        handle_player_shoot(pygame.mouse.get_pos(), now, gs)

    # Update player (with wall list)
    player.update(dt, now, walls)

    # Update bots
    for b in gs.bots:
        bot_ai(b, dt, now, gs)
        b.update(dt, now, walls)

    # Update bullets: move, check seg-rect for walls, and player/bot collision
    for b in gs.bullets[:]:
        b.update(dt)
        if b.is_expired(now):
            gs.bullets.remove(b)
            continue
        # check if bullet segment intersects any wall
        hit_wall = False
        for w in walls:
            if seg_rect_intersect(tuple(b.prev_pos), tuple(b.pos), w):
                hit_wall = True
                break
        if hit_wall:
            try: gs.bullets.remove(b)
            except: pass
            continue
        # check collision with players
        targets = [player] + gs.bots
        hit_any = False
        for t in targets:
            if t is b.owner:
                continue
            if bullet_hits_player(b, t):
                t.take_damage(b.damage, now)
                if not t.alive:
                    b.owner.kills += 1
                    b.owner.on_kill(t, now)
                    gs.add_killfeed(f"{b.owner.name} killed {t.name}")
                try: gs.bullets.remove(b)
                except: pass
                hit_any = True
                break
        if hit_any: continue

    # Round timer
    if now >= gs.round_end:
        for ent in [gs.player] + gs.bots:
            ent.alive = True
            ent.respawn_time = 0
            ent.hp = ent.max_hp
            ent.pos = [random.randint(80, WIDTH-80), random.randint(80, HEIGHT-80)]
            ent.medkits = 3
        gs.bullets.clear()
        gs.round_start = now
        gs.round_end = gs.round_start + ROUND_TIME
        gs.add_killfeed("Round reset")

    # --- Drawing ---
    screen.fill((12,14,18))
    # walls
    for w in walls:
        pygame.draw.rect(screen, GRAY, w)

    # smokes (player's)
    s_surf = pygame.Surface((WIDTH,HEIGHT), pygame.SRCALPHA)
    for s in player.smokes:
        pygame.draw.circle(s_surf, SMOKE_COLOR, (int(s[0]),int(s[1])), int(s[2]))
    screen.blit(s_surf, (0,0))

    # bullets
    for b in gs.bullets:
        col = YELLOW if b.owner is player else RED
        pygame.draw.circle(screen, col, (int(b.pos[0]), int(b.pos[1])), 4)

    # draw bots as humans
    for b in gs.bots:
        draw_human(screen, b.pos, math.atan2(gs.player.pos[1]-b.pos[1], gs.player.pos[0]-b.pos[0]), b.color, name_tag=b.name, is_dead=not b.alive)
        if b.alive:
            # small HP bar
            hpw = int((b.hp/b.max_hp)*28)
            pygame.draw.rect(screen, BLACK, (b.pos[0]-14, b.pos[1]-40, 28, 6))
            pygame.draw.rect(screen, GREEN, (b.pos[0]-14, b.pos[1]-40, hpw, 6))

    # draw player as human and gun
    if player.alive:
        draw_human(screen, player.pos, player.angle, player.color, name_tag=player.name, is_dead=False)
        # HP bar bigger
        hpw = int((player.hp/player.max_hp)*200)
        pygame.draw.rect(screen, BLACK, (16, HEIGHT-64, 204, 22))
        pygame.draw.rect(screen, GREEN, (18, HEIGHT-62, hpw, 18))
        pygame.draw.rect(screen, WHITE, (16, HEIGHT-64, 204, 22), 2)

    # HUD: transparent panel bottom-left
    hud_rect = pygame.Rect(8, HEIGHT-118, 420, 110)
    draw_transparent_panel(screen, hud_rect)
    draw_text(screen, f"HP: {int(player.hp)}/{player.max_hp}", 24, HEIGHT-110)
    draw_text(screen, f"Agent: {player.agent}", 24, HEIGHT-88)
    draw_text(screen, f"Medkits left (H): {player.medkits}", 24, HEIGHT-66)
    # weapon box
    wx,wy = 260, HEIGHT-98
    pygame.draw.rect(screen, (22,22,26,200), (wx,wy,140,72))
    pygame.draw.rect(screen, ACCENT, (wx,wy,140,72),2)
    draw_text(screen, f"Weapon: {player.weapon.name}", wx+8, wy+6)
    draw_text(screen, f"Ammo: {player.weapon.cur_mag}/{player.weapon.mag}", wx+8, wy+28)
    # ability cooldown bars
    def cooldown_bar(x,y,label,ability,width=160,height=10):
        cd = max(0, ability.cooldown - (now - ability.last))
        frac = 1 - (cd/ability.cooldown) if ability.cooldown>0 else 1
        frac = clamp(frac,0,1)
        pygame.draw.rect(screen, (30,30,30), (x,y,width,height))
        pygame.draw.rect(screen, ACCENT, (x,y,int(width*frac),height))
        draw_text(screen, f"{label} {'Ready' if ability.ready(now) else int(cd)}s", x, y-18)
    cooldown_bar(26, HEIGHT-52, "Dash (SPACE)", player.dash)
    cooldown_bar(26, HEIGHT-36, "Shield (Q)", player.shield)

    # crosshair at mouse pos with spread
    mx,my = pygame.mouse.get_pos()
    spread_px = int(player.weapon.spread_deg*0.8)
    # small crosshair lines
    gap = 10 + spread_px
    length = 8
    pygame.draw.line(screen, WHITE, (mx-gap-length, my), (mx-gap, my), 2)
    pygame.draw.line(screen, WHITE, (mx+gap+length, my), (mx+gap, my), 2)
    pygame.draw.line(screen, WHITE, (mx, my-gap-length), (mx, my-gap), 2)
    pygame.draw.line(screen, WHITE, (mx, my+gap+length), (mx, my+gap), 2)
    pygame.draw.circle(screen, WHITE, (mx,my), 2)

    # killfeed panel (top-right)
    kx,ky = WIDTH-440, 16
    krect = pygame.Rect(kx, ky, 420, 140)
    pygame.draw.rect(screen, (14,14,18), krect)
    pygame.draw.rect(screen, ACCENT, krect, 2)
    draw_text(screen, "Killfeed", kx+10, ky+6, font=BIG_FONT)
    i = 0
    for msg in gs.killfeed:
        draw_text(screen, msg, kx+10, ky+40 + i*18)
        i+=1

    draw_text(screen, f"Round ends in: {int(gs.round_end - now)}s", WIDTH//2 - 90, 12)
    draw_text(screen, f"Kills: {player.kills}  Deaths: {player.deaths}", WIDTH//2 - 90, 36)
    draw_text(screen, "Switch weapon: [1] Vandal  [2] Phantom  [3] Sheriff | Reload: R | Medkit: H", 18, 16)

    # bots scoreboard
    by = 160
    for b in gs.bots:
        draw_text(screen, f"{b.name} K:{b.kills} D:{b.deaths} HP:{int(b.hp) if b.alive else 'DEAD'}", WIDTH-220, by)
        by+=22

    pygame.display.flip()

pygame.quit()
