# freefire_offline.py
# Self-contained FreeFire-like demo using only procedurally generated art (no internet)
# Requirements: Python 3.8+, pygame
# Run: python freefire_offline.py

import math
import random
import pygame
from pygame.math import Vector2

# ---------- CONFIG ----------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

PLAYER_SPEED = 340
PLAYER_MAX_HEALTH = 14000
PLAYER_MAX_AMMO = 200
PLAYER_FIRE_RATE_RIFLE = 0.09
PLAYER_FIRE_RATE_PISTOL = 20
PLAYER_BULLET_SPEED = 1400
ENEMY_BULLET_SPEED = 700
ENEMY_SPAWN_START = 1.4
SAFE_ZONE_SHRINK_INTERVAL = 10.0
SAFE_ZONE_SHRINK_FACTOR = 0.80

MAX_ENEMYS_ON_SCREEN=10

# Enemy count slider settings
ENEMY_SLIDER_X, ENEMY_SLIDER_Y = 50, 60
ENEMY_SLIDER_W, ENEMY_SLIDER_H = 200, 10
ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H = 20, 30
ENEMY_MIN_LIMIT, ENEMY_MAX_LIMIT = 1, 30   # user can allow 1–30 enemies


#

# ---------- UTIL: procedural art ----------
def make_player_surface(size=96):
    w, h = size, size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # body
    pygame.draw.rect(surf, (60, 90, 180), (w*0.25, h*0.35, w*0.5, h*0.45), border_radius=10)
    # head
    pygame.draw.circle(surf, (220, 180, 140), (w//2, int(h*0.22)), w//8)
    # vest / chest highlight
    pygame.draw.rect(surf, (30, 60, 140), (w*0.3, h*0.5, w*0.4, h*0.18), border_radius=8)
    # arms
    pygame.draw.rect(surf, (60,90,180), (w*0.12, h*0.42, w*0.18, h*0.12), border_radius=6)
    pygame.draw.rect(surf, (60,90,180), (w*0.7, h*0.42, w*0.18, h*0.12), border_radius=6)
    # simple gun silhouette pointing right (original sprite oriented to right)
    gun_rect = pygame.Rect(w*0.65, h*0.45, w*0.5, h*0.08)
    pygame.draw.rect(surf, (40,40,40), gun_rect)
    pygame.draw.rect(surf, (20,20,20), (w*0.9, h*0.43, w*0.12, h*0.12))
    return surf

def make_enemy_surface(size=80):
    w,h = size,size
    surf = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (200,60,60), (w*0.22, h*0.32, w*0.56, h*0.46), border_radius=9)
    pygame.draw.circle(surf, (90,30,30), (w//2, int(h*0.18)), w//10)
    pygame.draw.rect(surf, (150,30,30), (w*0.35, h*0.5, w*0.3, h*0.15), border_radius=6)
    # gun
    pygame.draw.rect(surf, (30,30,30), (w*0.77, h*0.45, w*0.4, h*0.08))
    return surf

def make_cursor_surface(size=40):
    w = h = size
    surf = pygame.Surface((w,h), pygame.SRCALPHA)
    pygame.draw.circle(surf, (255,255,255), (w//2,h//2), w//4, 2)
    pygame.draw.line(surf, (255,255,255), (w//2 - 10, h//2), (w//2 + 10, h//2), 2)
    pygame.draw.line(surf, (255,255,255), (w//2, h//2-10), (w//2, h//2+10), 2)
    return surf

def make_parallax_layer(seed, w=1024, h=1024, base=(40,80,40)):
    random.seed(seed)
    surf = pygame.Surface((w,h)).convert()
    surf.fill(base)
    # add blobs/foliage
    for _ in range(180):
        rx = random.randint(0,w-1); ry = random.randint(0,h-1)
        r = random.randint(6, 50)
        color = (max(0, base[0]+random.randint(-10,40)),
                 max(0, base[1]+random.randint(-10,60)),
                 max(0, base[2]+random.randint(-10,30)))
        pygame.draw.circle(surf, color, (rx,ry), r)
    # add simple fog/gradients
    for y in range(h):
        shade = int(20 * (y / h))
        overlay = pygame.Surface((w,1)).convert_alpha()
        overlay.fill((0,0,0,shade))
        surf.blit(overlay, (0,y))
    return surf

# ---------- SPRITES ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, surf):
        super().__init__()
        self.orig = surf
        self.image = surf
        self.rect = self.image.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
        self.pos = Vector2(self.rect.center)
        self.speed = PLAYER_SPEED
        self.health = PLAYER_MAX_HEALTH
        self.ammo = PLAYER_MAX_AMMO
        self.fire_timer = 0.0
        self.weapons = {
            'rifle': [PLAYER_FIRE_RATE_RIFLE, 16, PLAYER_BULLET_SPEED, self.ammo],
            'pistol': [PLAYER_FIRE_RATE_PISTOL, 34, PLAYER_BULLET_SPEED*0.6, self.ammo],
            'BEST GUN': [PLAYER_FIRE_RATE_PISTOL*2, 50, PLAYER_BULLET_SPEED*1.15, self.ammo]
        }
        self.current_weapon = 'rifle'
        self.score = 0 

    def update(self, dt, keys, mouse_pos, shooting, bullets_group):
        mv = Vector2(0,0)
        if keys[pygame.K_w] or keys[pygame.K_UP]: mv.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: mv.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: mv.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: mv.x += 1
        if mv.length_squared() > 0:
            mv = mv.normalize()
            self.pos += mv * self.speed * dt
            # clamp to screen
            self.pos.x = max(20, min(self.pos.x, SCREEN_W-20))
            self.pos.y = max(20, min(self.pos.y, SCREEN_H-20))
            self.rect.center = self.pos

        # rotate to face mouse
        dx = mouse_pos[0] - self.rect.centerx
        dy = mouse_pos[1] - self.rect.centery
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotozoom(self.orig, angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)

        # shooting continuous while shooting True
        self.fire_timer -= dt
        rate, dmg, speed, ammo_dummy = self.weapons[self.current_weapon]
        if shooting and self.fire_timer <= 0 and self.ammo > 0:
            self.fire_timer = rate
            direction = Vector2(dx, dy)
            if direction.length_squared() == 0:
                direction = Vector2(1,0)
            direction = direction.normalize()
            bx = self.rect.centerx + direction.x * (self.rect.width//2)
            by = self.rect.centery + direction.y * (self.rect.height//2)
            b = Bullet(bx, by, direction, speed, dmg, 'player')
            bullets_group.add(b)
            self.ammo -= 1

    def switch_weapon(self, name):
        if name in self.weapons:
            self.current_weapon = name

class Enemy(pygame.sprite.Sprite):
    def __init__(self, surf, x, y):
        super().__init__()
        s = random.randint(52,92)
        self.orig = pygame.transform.smoothscale(surf, (s,s))
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=(x,y))
        self.pos = Vector2(self.rect.center)
        self.speed = random.uniform(40, 120)
        self.health = random.randint(22, 68)
        self.fire_timer = random.uniform(0.8, 2.0)

    def update(self, dt, player, bullets_group):
        dirv = player.pos - self.pos
        dist = dirv.length()
        if dist > 18:
            dirv.normalize_ip()
            self.pos += dirv * self.speed * dt
            self.rect.center = self.pos

        # rotate toward player
        dx = player.pos.x - self.pos.x
        dy = player.pos.y - self.pos.y
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotozoom(self.orig, angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)

        # shooting
        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = random.uniform(0.9, 2.4)
            direction = Vector2(dx, dy)
            if direction.length_squared() == 0:
                direction = Vector2(1,0)
            direction = direction.normalize()
            b = Bullet(self.pos.x + direction.x*10, self.pos.y + direction.y*10, direction, ENEMY_BULLET_SPEED, random.randint(6,12), 'enemy')
            bullets_group.add(b)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, speed, damage, owner):
        super().__init__()
        self.image = pygame.Surface((6,6), pygame.SRCALPHA)
        color = (255,230,90) if owner == 'player' else (255,120,120)
        pygame.draw.circle(self.image, color, (3,3), 3)
        self.rect = self.image.get_rect(center=(x,y))
        self.pos = Vector2(self.rect.center)
        self.direction = direction
        self.speed = speed
        self.damage = damage
        self.owner = owner

    def update(self, dt):
        self.pos += self.direction * self.speed * dt
        self.rect.center = self.pos
        if not (-300 < self.pos.x < SCREEN_W+300 and -300 < self.pos.y < SCREEN_H+300):
            self.kill()

class Pickup(pygame.sprite.Sprite):
    def __init__(self, kind, x, y):
        super().__init__()
        self.kind = kind
        self.image = pygame.Surface((18,18), pygame.SRCALPHA)
        if kind == 'health':
            pygame.draw.rect(self.image, (220,80,80), (0,0,18,18), border_radius=4)
        else:
            pygame.draw.rect(self.image, (80,160,220), (0,0,18,18), border_radius=4)
        self.rect = self.image.get_rect(center=(x,y))

# ---------- MAIN ----------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("FreeFire-like (Procedural Art, Offline)")
    clock = pygame.time.Clock()

    # create art surfaces
    player_surf = make_player_surface(96)
    enemy_surf = make_enemy_surface(80)
    cursor_surf = make_cursor_surface(36)
    bg_far = make_parallax_layer(1, w=1024, h=1024, base=(30,80,30))
    bg_near = make_parallax_layer(2, w=1024, h=1024, base=(20,110,35))

    # sprite groups
    player_group = pygame.sprite.GroupSingle()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    pickups = pygame.sprite.Group()

    player = Player(player_surf)
    player_group.add(player)
    player_group.add(player)

    spawn_timer = ENEMY_SPAWN_START
    running = True
    paused = False

    font = pygame.font.SysFont(None, 24)
    big_font = pygame.font.SysFont(None, 64)

    # camera/world offset (parallax)
    world_offset = Vector2(0,0)

    # safe zone
    safe_center = Vector2(SCREEN_W//2, SCREEN_H//2)
    safe_radius = max(SCREEN_W, SCREEN_H)//2
    safe_shrink_timer = SAFE_ZONE_SHRINK_INTERVAL

    pygame.mouse.set_visible(False)
    enemy_slider_value = 0.3  # between 0 and 1
    enemy_dragging = False
    max_enemies = int(ENEMY_MIN_LIMIT + enemy_slider_value * (ENEMY_MAX_LIMIT - ENEMY_MIN_LIMIT))

    while running:
        dt = clock.tick(FPS) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    running = False
                if ev.key == pygame.K_p:
                    paused = not paused
                if ev.key == pygame.K_1:
                    player.switch_weapon('rifle')
                if ev.key == pygame.K_2:
                    player.switch_weapon('pistol')
                if ev.key == pygame.K_3:
                    player.switch_weapon('BEST GUN')
                if ev.key == pygame.K_r and player.health <= 0:
                    # restart
                    enemies.empty(); bullets.empty(); pickups.empty()
                    player.pos = Vector2(SCREEN_W//2, SCREEN_H//2)
                    player.health = PLAYER_MAX_HEALTH
                    player.ammo = PLAYER_MAX_AMMO
                    player.score = 0
                    safe_radius = max(SCREEN_W, SCREEN_H)//2
                    safe_center = Vector2(SCREEN_W//2, SCREEN_H//2)
                    paused = False
                   # event=ev
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                mx, my = ev.pos
                handle_rect = pygame.Rect(
                ENEMY_SLIDER_X + int(enemy_slider_value * (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W)),
                ENEMY_SLIDER_Y - (ENEMY_SLIDER_HANDLE_H - ENEMY_SLIDER_H) // 2,
                ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H
    )
                if handle_rect.collidepoint(mx, my):
                  enemy_dragging = True

            elif ev.type == pygame.MOUSEBUTTONUP:
                 enemy_dragging = False

            elif ev.type == pygame.MOUSEMOTION and enemy_dragging:
                mx, my = ev.pos
                enemy_slider_value = max(0, min(1, (mx - ENEMY_SLIDER_X) / (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W)))
                max_enemies = int(ENEMY_MIN_LIMIT + enemy_slider_value * (ENEMY_MAX_LIMIT - ENEMY_MIN_LIMIT))


        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        shooting = keys[pygame.K_SPACE]

        if not paused:
            player.update(dt, keys, mouse_pos, shooting, bullets)

            # spawn enemies from edges
            spawn_timer -= dt
            if spawn_timer <= 0:
                spawn_timer = max(0.75 - (player.score * 0.0015), 0.28)
                side = random.choice(['top','bottom','left','right'])
                if side == 'top':
                    x = random.randint(0, SCREEN_W); y = -60
                elif side == 'bottom':
                    x = random.randint(0, SCREEN_W); y = SCREEN_H + 60
                elif side == 'left':
                    x = -60; y = random.randint(0, SCREEN_H)
                else:
                    x = SCREEN_W + 60; y = random.randint(0, SCREEN_H)
                if len(enemies)<max_enemies:
                 e = Enemy(enemy_surf, x, y)
                 enemies.add(e)

            # update enemies
            for e in list(enemies):
                e.update(dt, player, bullets)
                if e.health <= 0:
                    if random.random() < 0.33:
                        pickups.add(Pickup(random.choice(['health','ammo']), e.pos.x, e.pos.y))
                    e.kill()
                    player.score += 10

            bullets.update(dt)

            # bullets collisions
            for b in [bb for bb in bullets if bb.owner == 'player']:
                hit = pygame.sprite.spritecollideany(b, enemies)
                if hit:
                    hit.health -= b.damage
                    b.kill()

            for b in [bb for bb in bullets if bb.owner == 'enemy']:
                if pygame.sprite.collide_rect(b, player):
                    player.health -= b.damage
                    b.kill()

            # pickups
            for p in pygame.sprite.spritecollide(player, pickups, True):
                if p.kind == 'health':
                    player.health = min(PLAYER_MAX_HEALTH, player.health + 40)
                    player.score += 6
                else:
                    player.ammo = min(PLAYER_MAX_AMMO, player.ammo + 40)
                    player.score += 4

            # safe zone shrink behavior
           # safe_shrink_timer -= dt
            if safe_shrink_timer <= 0:
                safe_shrink_timer = SAFE_ZONE_SHRINK_INTERVAL
                safe_radius = max(60, int(safe_radius * SAFE_ZONE_SHRINK_FACTOR))
                safe_center += Vector2(random.randint(-80,80), random.randint(-80,80))

            # damage when outside safe zone
            if (player.pos - safe_center).length() > safe_radius:
                player.health -= 18 * dt

            if player.health <= 0:
                paused = True

            # world_offset smoothing for parallax (follow player)
            target = player.pos - Vector2(SCREEN_W/2, SCREEN_H/2)
            world_offset += (target - world_offset) * min(1, dt * 3.0)

        # ---------- DRAW ----------
        screen.fill((18,18,28))

        # helper: tiled draw with per-axis modulo
        def tiled_draw(img, parallax_factor):
            iw, ih = img.get_width(), img.get_height()
            px = (-world_offset.x * parallax_factor) % iw
            py = (-world_offset.y * parallax_factor) % ih
            for sx in range(-1, 2):
                for sy in range(-1, 2):
                    screen.blit(img, (sx * iw + px, sy * ih + py))

        tiled_draw(bg_far, 0.22)
        tiled_draw(bg_near, 0.55)

        enemies.draw(screen)
        bullets.draw(screen)
        pickups.draw(screen)
        player_group.draw(screen)

        # draw safe zone (semi-transparent ring)
        safe_surface = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.circle(safe_surface, (50,140,200,40), (int(safe_center.x), int(safe_center.y)), int(safe_radius))
        pygame.draw.circle(safe_surface, (50,140,200,90), (int(safe_center.x), int(safe_center.y)), int(safe_radius), 2)
        screen.blit(safe_surface, (0,0))

        # draw cursor
        screen.blit(cursor_surf, cursor_surf.get_rect(center=mouse_pos))

        # HUD
        hud_x = 12
        hud_y = 12
        font = pygame.font.SysFont(None, 24)
        health_text = font.render(f'Health: {int(player.health)}', True, (255,255,255))
        ammo_text = font.render(f'Ammo: {player.ammo}', True, (255,255,255))
        score_text = font.render(f'Score: {player.score}', True, (255,255,255))
        weapon_text = font.render(f'Weapon: {player.current_weapon}', True, (220,220,220))
        safe_text = font.render(f'Safe radius: {int(safe_radius)}', True, (200,220,255))
        screen.blit(health_text, (hud_x, hud_y))
        screen.blit(ammo_text, (hud_x, hud_y+24))
        screen.blit(score_text, (hud_x, hud_y+48))
        screen.blit(weapon_text, (hud_x, hud_y+72))
        screen.blit(safe_text, (hud_x, hud_y+100))
        
        #
        # Enemy count slider bar
        pygame.draw.rect(screen, (180,180,180), (ENEMY_SLIDER_X, ENEMY_SLIDER_Y, ENEMY_SLIDER_W, ENEMY_SLIDER_H))
# Handle
        handle_x = ENEMY_SLIDER_X + int(enemy_slider_value * (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W))
        handle_y = ENEMY_SLIDER_Y - (ENEMY_SLIDER_HANDLE_H - ENEMY_SLIDER_H)//2
        pygame.draw.rect(screen, (100,200,255), (handle_x, handle_y, ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H))

# Label
        font_small = pygame.font.SysFont("Arial", 20)
        label = font_small.render(f"Max Enemies: {max_enemies}", True, (255,255,255))
        screen.blit(label, (ENEMY_SLIDER_X + ENEMY_SLIDER_W + 20, ENEMY_SLIDER_Y - 10))

        #
        if paused and player.health <= 0:
            gg = big_font.render('YOU DIED', True, (255,80,80))
            sub = font.render('Press R to restart or ESC to quit', True, (220,220,220))
            screen.blit(gg, gg.get_rect(center=(SCREEN_W/2, SCREEN_H/2 - 20)))
            screen.blit(sub, sub.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 30)))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
