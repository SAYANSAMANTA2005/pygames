"""
FreeFire-like Pygame demo — Renderable background + full combat loop

Features implemented (playable demo):
- Renderable tiled parallax background (2 layers) that follows player movement
- Player (WASD) with mouse aiming; cursor visible and movable with mouse
- Hold SPACE to continuously fire toward the mouse cursor at chosen fire rate
- Enemies spawn from edges, move toward player, and shoot toward player
- Enemy bullets can damage player; player bullets damage enemies
- Two weapons (pistol / rifle) with different fire rates & damage; press 1/2 to switch
- Health, score, pickups (health pack, ammo), and basic HUD
- Local image loading with best-effort automatic download; falls back to generated art if download fails
- Robust math fixes (no Vector2 % Vector2 usage)

Run:
 - pip install pygame
 - python freefire_like_game.py

Notes:
 - This is a small demo inspired by battle-royale shooters. It's NOT the official Free Fire game.
 - If you prefer to force local images, drop PNG files into the `assets/` folder with names used below.
"""

import os
import sys
import math
import random
import urllib.request
from io import BytesIO

import pygame

# ---------------- CONFIG ----------------
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60
ASSET_DIR = 'assets'
os.makedirs(ASSET_DIR, exist_ok=True)

# Direct PNG links (CC0 / OpenGameArt examples). They are best-effort; if unavailable the code falls back.
IMAGE_URLS = {
    'player': 'https://opengameart.org/sites/default/files/soldier1_gun.png',
    'enemy':  'https://opengameart.org/sites/default/files/soldier2_gun.png',
    'bg_far': 'https://opengameart.org/sites/default/files/backgroundColorForest.png',
    'bg_near':'https://opengameart.org/sites/default/files/backgroundDetailsForest.png',
    'cursor':'https://opengameart.org/sites/default/files/crosshair.png'
}

# ---------------- UTIL ----------------

def download_if_needed(name, url):
    local = os.path.join(ASSET_DIR, name)
    if os.path.exists(local):
        return local
    if not url:
        return None
    try:
        urllib.request.urlretrieve(url, local)
        return local
    except Exception as e:
        print(f"Download failed for {url}: {e}")
        return None


def load_image(name, url, scale=None, colorkey=None):
    path = download_if_needed(name, url)
    surf = None
    if path and os.path.exists(path):
        try:
            surf = pygame.image.load(path).convert_alpha()
        except Exception as e:
            print('pygame failed to load', path, e)
            surf = None
    if surf is None:
        # fallback generated sprite
        w, h = scale if scale else (96, 96)
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # simple placeholder art depending on type
        if 'player' in name:
            pygame.draw.rect(surf, (200, 200, 255), (0,0,w,h), border_radius=12)
            pygame.draw.circle(surf, (60,60,60), (w//2, h//3), w//8)
        elif 'enemy' in name:
            pygame.draw.rect(surf, (255, 200, 200), (0,0,w,h), border_radius=12)
            pygame.draw.circle(surf, (80,30,30), (w//2, h//3), w//8)
        elif 'bg' in name:
            surf = pygame.Surface((w,h))
            surf.fill((50, 90, 50))
            for i in range(100):
                rx = random.randint(0, w-1); ry = random.randint(0,h-1)
                surf.set_at((rx, ry), (50 + random.randint(0,40), 80 + random.randint(0,40), 50))
        elif 'cursor' in name:
            pygame.draw.circle(surf, (255,255,255), (w//2,h//2), min(w,h)//4, 2)
        else:
            pygame.draw.rect(surf, (120,120,120), (0,0,w,h))
    if scale:
        surf = pygame.transform.smoothscale(surf, scale)
    if colorkey is not None:
        surf.set_colorkey(colorkey)
    return surf

# ---------------- ENTITIES ----------------
class Player(pygame.sprite.Sprite):
    def __init__(self, img):
        super().__init__()
        self.orig = img
        self.image = img
        self.rect = self.image.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
        self.pos = pygame.Vector2(self.rect.center)
        self.speed = 360
        self.health = 120
        self.score = 0
        # weapons: (fire_rate_sec, damage, bullet_speed, ammo)
        self.weapons = {
            'pistol': [0.18, 18, 1200, 9999],
            'rifle' : [0.09, 9, 1600, 180]
        }
        self.current_weapon = 'rifle'
        self.fire_cooldown = 0.0
        self.radius = max(self.rect.width, self.rect.height) * 0.45

    def update(self, dt, keys, mouse_pos, shooting, bullets_group):
        # movement
        mv = pygame.Vector2(0,0)
        if keys[pygame.K_w] or keys[pygame.K_UP]: mv.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: mv.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: mv.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: mv.x += 1
        if mv.length_squared() > 0:
            mv = mv.normalize()
            self.pos += mv * self.speed * dt
            # clamp to screen
            self.pos.x = max(0, min(self.pos.x, SCREEN_W))
            self.pos.y = max(0, min(self.pos.y, SCREEN_H))
            self.rect.center = self.pos

        # aim rotation to face cursor
        dx = mouse_pos[0] - self.rect.centerx
        dy = mouse_pos[1] - self.rect.centery
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotozoom(self.orig, angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)

        # shooting: continuous while 'shooting' True and cooldown <=0
        self.fire_cooldown -= dt
        rate, damage, speed, ammo = self.weapons[self.current_weapon]
        if shooting and self.fire_cooldown <= 0 and ammo != 0:
            self.fire_cooldown = rate
            if self.weapons[self.current_weapon][3] > 0:
                # consume ammo unless infinite
                if self.weapons[self.current_weapon][3] != 9999:
                    self.weapons[self.current_weapon][3] -= 1
            # spawn bullet toward cursor
            dirv = pygame.Vector2(dx, dy)
            if dirv.length_squared() == 0:
                dirv = pygame.Vector2(1, 0)
            dirv = dirv.normalize()
            bx = self.rect.centerx + dirv.x * (self.rect.width//2)
            by = self.rect.centery + dirv.y * (self.rect.height//2)
            b = Bullet(bx, by, dirv, speed, damage, owner='player')
            bullets_group.add(b)

    def switch_weapon(self, name):
        if name in self.weapons:
            self.current_weapon = name

class Enemy(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        super().__init__()
        s = random.randint(48, 88)
        self.orig = pygame.transform.smoothscale(img, (s, s))
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=(x,y))
        self.pos = pygame.Vector2(self.rect.center)
        self.speed = random.uniform(40, 140)
        self.health = random.randint(18, 48)
        self.fire_cooldown = random.uniform(0.5, 2.0)
        self.radius = max(self.rect.width, self.rect.height) * 0.45

    def update(self, dt, player, bullets_group):
        # simple AI: move toward player
        dirv = player.pos - self.pos
        dist = dirv.length()
        if dist > 6:
            dirv.normalize_ip()
            self.pos += dirv * self.speed * dt
            self.rect.center = self.pos
        # face player
        dx = player.pos.x - self.pos.x
        dy = player.pos.y - self.pos.y
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotozoom(self.orig, angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)

        # shooting
        self.fire_cooldown -= dt
        if self.fire_cooldown <= 0:
            self.fire_cooldown = random.uniform(0.8, 2.4)
            direction = pygame.Vector2(dx, dy)
            if direction.length_squared() == 0:
                direction = pygame.Vector2(1,0)
            direction = direction.normalize()
            b = Bullet(self.pos.x + direction.x*10, self.pos.y + direction.y*10, direction, 780, 10, owner='enemy')
            bullets_group.add(b)

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, speed, damage, owner='player'):
        super().__init__()
        self.image = pygame.Surface((6,6), pygame.SRCALPHA)
        if owner == 'player':
            pygame.draw.circle(self.image, (255,230,120), (3,3), 3)
        else:
            pygame.draw.circle(self.image, (255,120,120), (3,3), 3)
        self.rect = self.image.get_rect(center=(x,y))
        self.pos = pygame.Vector2(self.rect.center)
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
        self.image = pygame.Surface((20,20), pygame.SRCALPHA)
        if kind == 'health':
            pygame.draw.rect(self.image, (220,80,80), (0,0,20,20), border_radius=4)
        elif kind == 'ammo':
            pygame.draw.rect(self.image, (80,150,230), (0,0,20,20), border_radius=4)
        self.rect = self.image.get_rect(center=(x,y))

# ---------------- MAIN GAME ----------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption('FreeFire-like Demo (playable)')
    clock = pygame.time.Clock()

    # load assets (scale sizes chosen sensibly)
    player_img = load_image('player.png', IMAGE_URLS['player'], scale=(96,96))
    enemy_img = load_image('enemy.png', IMAGE_URLS['enemy'], scale=(80,80))
    bg_far = load_image('bg_far.png', IMAGE_URLS['bg_far'], scale=(SCREEN_W*2, SCREEN_H*2))
    bg_near = load_image('bg_near.png', IMAGE_URLS['bg_near'], scale=(SCREEN_W*2, SCREEN_H*2))
    cursor_img = load_image('cursor.png', IMAGE_URLS['cursor'], scale=(40,40))

    # groups
    player_group = pygame.sprite.GroupSingle()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()
    pickups = pygame.sprite.Group()

    player = Player(player_img)
    player_group.add(player)

    spawn_timer = 1.2
    running = True
    paused = False

    font = pygame.font.SysFont(None, 26)
    big_font = pygame.font.SysFont(None, 64)

    # world offset for parallax - we will track a 'camera' centered on player
    world_offset = pygame.Vector2(0,0)

    # hide OS cursor (we'll draw our own)
    pygame.mouse.set_visible(False)

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_1:
                    player.switch_weapon('pistol')
                if event.key == pygame.K_2:
                    player.switch_weapon('rifle')
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # allow left click to also fire instantly (space is continuous)
                pass

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        shooting = keys[pygame.K_SPACE]

        if not paused:
            # update player
            player.update(dt, keys, mouse_pos, shooting, bullets)

            # spawn enemies from edges
            spawn_timer -= dt
            if spawn_timer <= 0:
                spawn_timer = max(0.9 - player.score*0.0015, 0.28)
                side = random.choice(['top','bottom','left','right'])
                if side == 'top': x = random.randint(0, SCREEN_W); y = -60
                elif side == 'bottom': x = random.randint(0, SCREEN_W); y = SCREEN_H + 60
                elif side == 'left': x = -60; y = random.randint(0, SCREEN_H)
                else: x = SCREEN_W + 60; y = random.randint(0, SCREEN_H)
                e = Enemy(enemy_img, x, y)
                enemies.add(e)

            # update enemies
            for e in list(enemies):
                e.update(dt, player, bullets)
                if e.health <= 0:
                    e.kill(); player.score += 12
                    player.health+=40
                    if random.random() < 0.30:
                        pickups.add(Pickup('health', e.pos.x, e.pos.y))
                    if random.random() < 0.4:
                        pickups.add(Pickup('ammo', e.pos.x, e.pos.y))

            # bullets update
            bullets.update(dt)

            # collision: player bullets -> enemies
            for b in [bb for bb in bullets if bb.owner == 'player']:
                hit = pygame.sprite.spritecollideany(b, enemies)
                if hit:
                    hit.health -= b.damage
                    b.kill()

            # collision: enemy bullets -> player
            for b in [bb for bb in bullets if bb.owner == 'enemy']:
                if pygame.sprite.collide_circle(b, player) or player.rect.colliderect(b.rect):
                    player.health -= b.damage
                    b.kill()

            # pickups
            for p in pygame.sprite.spritecollide(player, pickups, True):
                if p.kind == 'health':
                    player.health = min(200, player.health + 40)
                    player.score += 6
                elif p.kind == 'ammo':
                    # give ammo to both weapons moderately
                    player.weapons['rifle'][3] += 40
                    player.weapons['pistol'][3] += 10
                    player.score += 4

            # check player death
            if player.health <= 0:
                paused = True

            # update world_offset (camera) to follow player smoothly
            target = player.pos - pygame.Vector2(SCREEN_W/2, SCREEN_H/2)
            world_offset += (target - world_offset) * min(1, dt*3.0)

        # ---------------- DRAW ----------------
        screen.fill((20, 20, 28))

        # compute per-axis modulo positions for parallax layers (no Vector2 % Vector2)
        far_x = (-world_offset.x * 0.20) % bg_far.get_width()
        far_y = (-world_offset.y * 0.20) % bg_far.get_height()
        near_x = (-world_offset.x * 0.6) % bg_near.get_width()
        near_y = (-world_offset.y * 0.6) % bg_near.get_height()

        # tile far layer
        for sx in range(-1, 2):
            for sy in range(-1, 2):
                px = sx*bg_far.get_width() + far_x
                py = sy*bg_far.get_height() + far_y
                screen.blit(bg_far, (px, py))
        # tile near layer
        for sx in range(-1, 2):
            for sy in range(-1, 2):
                px = sx*bg_near.get_width() + near_x
                py = sy*bg_near.get_height() + near_y
                screen.blit(bg_near, (px, py))

        # draw sprites (they are screen-space so no camera transform needed)
        enemies.draw(screen)
        bullets.draw(screen)
        pickups.draw(screen)
        player_group.draw(screen)

        # draw custom cursor at mouse position
        screen.blit(cursor_img, cursor_img.get_rect(center=mouse_pos))

        # HUD
        hud1 = font.render(f"Health: {int(player.health)}", True, (255,255,255))
        hud2 = font.render(f"Score: {player.score}", True, (255,255,255))
        hud3 = font.render(f"Weapon: {player.current_weapon} | Ammo: {player.weapons[player.current_weapon][3]}", True, (255,255,255))
        screen.blit(hud1, (12, 12))
        screen.blit(hud2, (12, 36))
        screen.blit(hud3, (12, 60))

        if paused and player.health <= 0:
            gg = big_font.render('YOU DIED', True, (255, 80, 80))
            screen.blit(gg, gg.get_rect(center=(SCREEN_W/2, SCREEN_H/2)))
            sub = font.render('Press R to restart or ESC to quit', True, (220,220,220))
            screen.blit(sub, sub.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 40)))
            # restart handling
            keys2 = pygame.key.get_pressed()
            if keys2[pygame.K_r]:
                # reset game quickly
                enemies.empty(); bullets.empty(); pickups.empty()
                player.pos = pygame.Vector2(SCREEN_W/2, SCREEN_H/2)
                player.health = 1400; player.score = 0
                player.weapons['rifle'][3] = 180; player.weapons['pistol'][3] = 9999
                paused = False

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()
