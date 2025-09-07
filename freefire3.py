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
PLAYER_MAX_AMMO = 20000
PLAYER_FIRE_RATE_RIFLE = 0.09
PLAYER_FIRE_RATE_PISTOL = 20
PLAYER_BULLET_SPEED = 1400
ENEMY_BULLET_SPEED = 700
ENEMY_SPAWN_START = 1.4
SAFE_ZONE_SHRINK_INTERVAL = 100.0
SAFE_ZONE_SHRINK_FACTOR = 0.0
MIN_SAFE_ZONE_RADIOUS=500

MAX_ENEMYS_ON_SCREEN=50

# Enemy count slider settings
ENEMY_SLIDER_X, ENEMY_SLIDER_Y = 50, 60
ENEMY_SLIDER_W, ENEMY_SLIDER_H = 200, 10
ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H = 20, 30
ENEMY_MIN_LIMIT, ENEMY_MAX_LIMIT = 1, 100   # user can allow 1–30 enemies


# GEANADE 
GRANADE_EXPLOSION_RADIOUS=100
# Boss settings
BOSS_APPERENCE_DURATION=5
MAX_BOSSES_ON_SCREEN=5
# max boss setting
# Boss count slider settings
BOSS_SLIDER_X, BOSS_SLIDER_Y = 50, 120
BOSS_SLIDER_W, BOSS_SLIDER_H = 200, 10
BOSS_SLIDER_HANDLE_W, BOSS_SLIDER_HANDLE_H = 20, 30
BOSS_MIN_LIMIT, BOSS_MAX_LIMIT = 1, 10  # allow 1–10 bosses


#mini map settings
# ----- MINI-MAP SETTINGS -----
MINIMAP_W, MINIMAP_H = 180, 180
MINIMAP_MARGIN = 20
WORLD_W, WORLD_H = 4000, 3000   # same world size as your code


cntboss=0

#sound effects 




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
def draw_minimap(screen, player, enemies, airdrops, safe_center, safe_radius):
    # minimap rect (bottom-right corner)
    mini_rect = pygame.Rect(
        SCREEN_W - MINIMAP_W - MINIMAP_MARGIN,
        SCREEN_H - MINIMAP_H - MINIMAP_MARGIN,
        MINIMAP_W, MINIMAP_H
    )

    # background
    pygame.draw.rect(screen, (20,20,40), mini_rect)
    pygame.draw.rect(screen, (80,80,120), mini_rect, 2)

    scale_x = MINIMAP_W / WORLD_W
    scale_y = MINIMAP_H / WORLD_H

    def world_to_minimap(pos):
        return (
            mini_rect.x + int(pos.x * scale_x),
            mini_rect.y + int(pos.y * scale_y)
        )

    # safe zone circle
    pygame.draw.circle(
        screen, (50,140,200),
        (mini_rect.x + int(safe_center.x * scale_x), mini_rect.y + int(safe_center.y * scale_y)),
        int(safe_radius * scale_x), 1
    )

    # player
    px, py = world_to_minimap(player.pos)
    pygame.draw.circle(screen, (0,255,0), (px, py), 4)

    # enemies
    for e in enemies:
        ex, ey = world_to_minimap(e.pos)
        #if hasattr(e, "is_boss") and e.is_boss:  # bosses marked
        if isinstance(e, Boss):
            pygame.draw.circle(screen, (180,0,255), (ex, ey), 6)
        else:
            pygame.draw.circle(screen, (255,0,0), (ex, ey), 3)

    # airdrops
    for a in airdrops:
        ax, ay = world_to_minimap(a.pos)
        pygame.draw.rect(screen, (0,150,255), (ax-2, ay-2, 5, 5))

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
            'BEST_GUN': [PLAYER_FIRE_RATE_PISTOL, 40, PLAYER_BULLET_SPEED, self.ammo]
        }
        self.current_weapon = 'rifle'
        self.score = 0 
        ## melee (knife) attack
        self.melee_cooldown = 0.0   # cooldown timer
        self.melee_range = 70       # knife reach
        self.melee_damage = 50      # knife damage
       # mele visual effect
        self.flash_timer = 0  # 👈 for flash effect
    
    def flash_red(self):
        self.flash_timer = 0.1  # 0.1s flash
    def update(self, dt, keys, mouse_pos, shooting, bullets_group):
        mv = Vector2(0,0)
        if self.flash_timer > 0:
            self.flash_timer -= dt
            self.image.fill((255,0,0), special_flags=pygame.BLEND_RGB_ADD)
        else:
            self.image = self.orig.copy()
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
        # update melee cooldown
        if self.melee_cooldown > 0:
            self.melee_cooldown -= dt
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

    def melee_attack(self, enemies, all_sprites):
        if self.melee_cooldown <= 0:   # only if ready
            self.melee_cooldown = 0.6  # reset cooldown
            all_sprites.add(KnifeSwing(self.pos))  # always show slash arc

            hit_count = 0
            for enemy in enemies:
                if self.pos.distance_to(enemy.pos) <= self.melee_range:
                    if isinstance(enemy, Boss):
                        enemy.health -= self.melee_damage // 2  # bosses take half dmg
                    else:
                        enemy.health -= self.melee_damage
                    hit_count += 1
                    enemy.flash_red()   # 👈 new effect when hit
                all_sprites.add(HitSpark(enemy.pos))
                    
            #if hit_count > 0:
              #  knife_sound = pygame.mixer.Sound("E:/PYGAME PROJECTS/assets/knife.wav")
              #  knife_sound.set_volume(0.5)
              #  knife_sound.play()
        
        # 👇 Add knife swing effect whether you hit or not

    # Add knife swing effect
                
    def switch_weapon(self, name):
        if name in self.weapons:
            self.current_weapon = name
            
# self playing teammates
class Teammate(pygame.sprite.Sprite):
    def __init__(self, surf, x, y):
        super().__init__()
        s = 72
        self.orig = pygame.transform.smoothscale(surf, (s, s))
        # Different color from player
        pygame.draw.circle(self.orig, (50, 200, 255), (s//2, s//2), s//2)  # blue circle
        pygame.draw.circle(self.orig, (255, 255, 255), (s//2, s//2), s//2, 3)  # white border

        self.orig.fill((80, 180, 220), special_flags=pygame.BLEND_RGB_ADD)
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = Vector2(self.rect.center)

        self.speed = 260
        self.health = 800
        self.max_health = self.health
        self.fire_timer = 0.0
        self.range = 600  # attack range
        self.damage = 14

    def update(self, dt, player, enemies, bullets_group):
        # 🔵 draw circle marker AFTER rotation
        pygame.draw.circle(self.image, (50, 200, 255), (self.image.get_width()//2, self.image.get_height()//2), self.image.get_width()//2, 4)
        #self.rect = self.image.get_rect(center=self.pos)

        # follow player loosely
        to_player = player.pos - self.pos
        if to_player.length() > 500:  # maintain some distance
            self.pos += to_player.normalize() * self.speed * dt
            self.rect.center = self.pos

        # find nearest enemy
        target = None
        min_dist = self.range
        for e in enemies:
            d = self.pos.distance_to(e.pos)
            if d < min_dist:
                min_dist = d
                target = e

        # rotate to face target or player
        if target:
            dx, dy = target.pos.x - self.pos.x, target.pos.y - self.pos.y
        else:
            dx, dy = player.pos.x - self.pos.x, player.pos.y - self.pos.y
        angle = math.degrees(math.atan2(-dy, dx))
        self.image = pygame.transform.rotozoom(self.orig, angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)

        # -------------------------#
        # shooting logic
        self.fire_timer -= dt
        if target and self.fire_timer <= 0:
            self.fire_timer = 0.5  # fire rate
            direction = Vector2(dx, dy).normalize()
            bx = self.pos.x + direction.x * (self.rect.width // 2)
            by = self.pos.y + direction.y * (self.rect.height // 2)
            b = Bullet(bx, by, direction, PLAYER_BULLET_SPEED * 0.8, self.damage, 'player')
            bullets_group.add(b)

        # draw health bar
        max_width = self.rect.width * 0.6
        height = 5
        ratio = max(self.health, 0) / self.max_health
        filled = int(max_width * ratio)
        bar_x = self.rect.width * 0.2
        bar_y = self.rect.height * 0.85
        pygame.draw.rect(self.image, (180, 0, 0), (bar_x, bar_y, max_width, height))
        pygame.draw.rect(self.image, (0, 255, 0), (bar_x, bar_y, filled, height))
            
class HitSpark(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((30, 30), pygame.SRCALPHA)
        for i in range(5):
            x = random.randint(10, 20)
            y = random.randint(10, 20)
            pygame.draw.circle(self.image, (255, 220, 100), (x, y), 2)
        self.rect = self.image.get_rect(center=pos)
        self.timer = 2.15   # short flash

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.kill()
class KnifeSwing(pygame.sprite.Sprite):
    def __init__(self, pos, radius=70):
        super().__init__()
        self.image = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.arc(
            self.image, (255, 255, 150),
            (10, 10, radius*2-20, radius*2-20),
            math.radians(-60), math.radians(60), 5
        )
        self.rect = self.image.get_rect(center=pos)
        self.timer = 4.25   # visible for 0.25s

    def update(self, dt):
        self.timer -= dt
        self.image.set_alpha(int(255 * (self.timer / 0.25 * 255)))
        if self.timer <= 0:
            self.kill()

class Enemy(pygame.sprite.Sprite):
    def __init__(self, surf, x, y, etype="normal"):
        super().__init__()
        s = random.randint(52,92)
        self.flash_timer = 2  # 👈 add flash effect timer
        self.is_boss = False
        self.orig = pygame.transform.smoothscale(surf, (s,s))
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=(x,y))
        self.pos = Vector2(self.rect.center)

        # Enemy type
        self.type = etype
        # Default body color
        body_color = (200, 60, 60)
        head_color = (90,30,30)
        chest_color = (150,30,30)

        # Customize color/shape per type
        if etype == "runner":       # Fast, weak
            body_color = (255, 100, 50)       # bright orange
            head_color = (180, 50, 50)
            chest_color = (220, 80, 80)
            # maybe taller/slimmer shape
            pygame.draw.rect(self.orig, body_color, (s*0.3, s*0.3, s*0.4, s*0.5), border_radius=5)
        elif etype == "tank":       # Slow, strong
            body_color = (255, 220, 120)   # bright pastel, yellow-pink with some green tone

       # dark blue
            head_color = (30,30,90)
            chest_color = (50,50,150)
            pygame.draw.rect(self.orig, body_color, (s*0.2, s*0.25, s*0.6, s*0.5), border_radius=10)
        elif etype == "sniper":     # Slow, long-range
            body_color = (50, 180, 50)       # green
            head_color = (30,100,30)
            chest_color = (40,140,40)
            pygame.draw.ellipse(self.orig, body_color, (s*0.25, s*0.3, s*0.5, s*0.5))
        else:                       # normal
            body_color = (200,60,60)  # red
            head_color = (90,30,30)
            chest_color = (150,30,30)
            pygame.draw.rect(self.orig, body_color, (s*0.22, s*0.32, s*0.56, s*0.46), border_radius=8)

        # head
        pygame.draw.circle(self.orig, head_color, (s//2, int(s*0.18)), int(s/10))
        # chest/vest
        pygame.draw.rect(self.orig, chest_color, (s*0.35, s*0.5, s*0.3, s*0.15), border_radius=6)

        # Attributes by type
        if etype == "runner":
            self.speed = random.uniform(180, 250)       # fast
            self.health = random.randint(15, 35)        # weak
            self.fire_timer = random.uniform(2.0, 4.0)  # rarely shoots
            self.max_health = self.health   # 👈 add this
        elif etype == "tank":
            self.speed = random.uniform(200, 300)         # slow
            self.health = random.randint(100, 160)      # strong
            self.fire_timer = random.uniform(0.3, 0.7)  # shoots normally
            self.max_health = self.health   # 👈 add this
        elif etype == "sniper":
            self.speed = random.uniform(30, 60)         # slow
            self.health = random.randint(30, 50)        # moderate HP
            self.fire_timer = random.uniform(1.5, 2.5)  # shoots less often
            self.shoot_distance = random.randint(300, 600)  # only shoots if far
            self.max_health = self.health   # 👈 add this
        else:
            # default enemy
            self.speed = random.uniform(40, 120)
            self.health = random.randint(22, 68)
            self.fire_timer = random.uniform(0.8, 2.0)
            self.max_health = self.health   # 👈 add this

    def flash_red(self):
        self.flash_timer = 5.15  # show red tint for 0.15s
    def update(self, dt, player, bullets_group):
        # handle flash effect
        if self.flash_timer > 0:
            self.flash_timer -= dt
            temp = self.orig.copy()
            temp.fill((255, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
            self.image = temp
        # Move toward player
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
        # ---- Draw health bar ----
        max_width = self.rect.width * 0.6   # bar width inside body
        height = 5                          # bar height
        health_ratio = max(self.health, 0) / self.max_health
        filled_width = int(max_width * health_ratio)

        # Position bar slightly below head
        bar_x = self.rect.width * 0.2
        bar_y = self.rect.height * 0.8

        pygame.draw.rect(self.image, (180, 0, 0), (bar_x, bar_y, max_width, height))  # red bg
        pygame.draw.rect(self.image, (0, 255, 0), (bar_x, bar_y, filled_width, height))  # green fill
        # -------------------------#
        # shooting logic
        self.fire_timer -= dt
        shoot_condition = True
        if self.type == "runner":
            shoot_condition = random.random() < 10000
        elif self.type == "sniper":
            shoot_condition = dist >= getattr(self, "shoot_distance", 300)

        if self.fire_timer <= 0 and shoot_condition:
            if self.type == "runner":
                self.fire_timer = random.uniform(2.0, 4.0)
            elif self.type == "sniper":
                self.fire_timer = random.uniform(1.5, 2.5)
            else:
                self.fire_timer = random.uniform(0.8, 2.0)
            
            direction = Vector2(dx, dy)
            if direction.length_squared() == 0:
                direction = Vector2(1,0)
            direction = direction.normalize()
            b = Bullet(self.pos.x + direction.x*10, self.pos.y + direction.y*10,
                       direction, ENEMY_BULLET_SPEED, random.randint(6,12), 'enemy')
            bullets_group.add(b)
class Boss(Enemy):
    def __init__(self, surf, x, y):
        super().__init__(surf, x, y)
        self.orig = pygame.transform.smoothscale(surf, (200, 200))
        #
        self.is_boss = True

        self.size = 200
        pygame.draw.polygon(
            self.orig, 
            (180, 40, 40), 
            [
                (self.size*0.5, 0),
                (self.size*0.93, self.size*0.25),
                (self.size*0.93, self.size*0.75),
                (self.size*0.5, self.size),
                (self.size*0.07, self.size*0.75),
                (self.size*0.07, self.size*0.25)
            ]
        )
        pygame.draw.circle(self.orig, (255, 255, 0), (int(self.size*0.3), int(self.size*0.35)), int(self.size*0.08))
        pygame.draw.circle(self.orig, (255, 255, 0), (int(self.size*0.7), int(self.size*0.35)), int(self.size*0.08))
        # Mouth: black rectangle
        pygame.draw.rect(self.orig, (0,0,0), (self.size*0.3, self.size*0.6, self.size*0.4, self.size*0.1))

        #
        self.image = self.orig.copy()
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = Vector2(self.rect.center)
        self.speed = 60
        self.health = 800 + random.randint(-50, 50)  # Boss HP
        self.fire_timer = 2.0  # slower fire
        self.special_timer = 5.0  # special attack cooldown

    def update(self, dt, player, bullets_group):
        super().update(dt, player, bullets_group)
        # Boss special attack
        self.special_timer -= dt
        if self.special_timer <= 0:
            self.special_timer = random.uniform(4, 7)
            self.special_attack(player, bullets_group)

    def special_attack(self, player, bullets_group):
        # Shoot 3 bullets in spread toward player
        direction = (player.pos - self.pos).normalize()
        angles = [-15, 0, 15]  # degrees spread
        for ang in angles:
            rad = math.radians(ang)
            rotated = Vector2(
                direction.x * math.cos(rad) - direction.y * math.sin(rad),
                direction.x * math.sin(rad) + direction.y * math.cos(rad)
            )
            b = Bullet(self.pos.x + rotated.x*20, self.pos.y + rotated.y*20, rotated, ENEMY_BULLET_SPEED, 25, 'enemy')
            bullets_group.add(b)
            
class Explosion(pygame.sprite.Sprite):
    def __init__(self, pos, radius):
        super().__init__()
        self.image = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (255, 150, 0, 120), (radius, radius), radius)
        self.rect = self.image.get_rect(center=pos)
        self.timer = 0.3  # visible for 0.3s

    def update(self, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.kill()

class Grenade(pygame.sprite.Sprite):
    def __init__(self, pos, target, speed=400, fuse_time=1.2, radius=100, damage=100):
        super().__init__()
        self.image = pygame.Surface((12, 12), pygame.SRCALPHA)
        pygame.draw.circle(self.image, (0, 255, 0), (6, 6), 6)  # green circle
        self.rect = self.image.get_rect(center=pos)
        self.pos = pygame.Vector2(pos)
        self.vel = (pygame.Vector2(target) - self.pos).normalize() * speed
        self.fuse_time = fuse_time  # seconds before explosion
        self.timer = 0
        self.radius = radius
        self.damage = damage
        self.exploded = False

    def update(self, dt, enemies, all_sprites):
        if not self.exploded:
            self.timer += dt
            self.pos += self.vel * dt
            self.rect.center = self.pos

            # Explode after fuse_time
            if self.timer >= self.fuse_time:
                self.explode(enemies, all_sprites)

    def explode(self, enemies, all_sprites):
        global cntboss
        self.exploded = True
        
        granad_sound = pygame.mixer.Sound("E:/PYGAME PROJECTS/assets/grenade.wav")
        granad_sound.play()
        
        # Create explosion effect
        explosion = Explosion(self.rect.center, self.radius)
        all_sprites.add(explosion)

        # Damage enemies in radius
       # for enemy in enemies:
            #if pygame.Vector2(enemy.rect.center).distance_to(self.rect.center) <= self.radius:
           # if pygame.Vector2(enemy.rect.center).distance_to(self.rect.center) <= GRANADE_EXPLOSION_RADIOUS:
             #   if isinstance(enemy, Boss):
              #      cntboss-=1
                    #enemy.health -= 400  # high damage to boss
               # enemy.kill()  # simple: instant kill
        for enemy in enemies:
          if enemy.rect and self.rect:   # <--- make sure rect exists
              if pygame.Vector2(enemy.rect.center).distance_to(self.rect.center) <= GRANADE_EXPLOSION_RADIOUS:
                   if isinstance(enemy, Boss):
                     cntboss -= 1
          enemy.kill()
        cntboss=0
        self.kill()
        
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
class AirDrop(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        self.kind = random.choice(['double_damage', 'speed_boost'])
        #self.kind = random.choice(['BEST_GUN',  'double_damage'])
        self.image = pygame.Surface((28,28), pygame.SRCALPHA)
        #pygame.draw.rect(self.image, (255,215,0), (0,0,28,28), border_radius=6)  # gold crate
        #pygame.draw.rect(self.image, (0,0,0), (4,4,20,20), 2)  # outline
          # --- Draw vibrant box ---
        # main body
        size = 36  # bigger than pickups
        pygame.draw.rect(self.image, (255, 50, 50), (0, 0, size, size), border_radius=6)  # bright red
        # border
        pygame.draw.rect(self.image, (255, 215, 0), (0, 0, size, size), 4, border_radius=6)  # golden border
        # stripe / cross
        pygame.draw.line(self.image, (0, 200, 255), (0, size//2), (size, size//2), 4)  # horizontal stripe
        pygame.draw.line(self.image, (0, 200, 255), (size//2, 0), (size//2, size), 4)  # vertical stripe

        self.rect = self.image.get_rect(center=(x,y))
        self.pos = pygame.Vector2(self.rect.center)   # <--- ADD THIS

class PowerUpEffect:
    def __init__(self):
        self.double_damage = 0
        self.speed_boost = 0

    def update(self, dt):
        if self.double_damage > 0:
            self.double_damage -= dt
        if self.speed_boost > 0:
            self.speed_boost -= dt

    def is_active(self, kind):
        if kind == 'double_damage':
            return self.double_damage > 0
        if kind == 'speed_boost':
            return self.speed_boost > 0
        return False

# ---------- MAIN ----------
def main():
    
    pygame.init()
    # sound effects
    pygame.mixer.init()

# --- Load sounds ---
   # shoot_sound = pygame.mixer.Sound("assets/sounds/shoot.wav")
    #enemy_hit_sound = pygame.mixer.Sound("assets\\gunshoot.wav")
    enemy_hit_sound = pygame.mixer.Sound("E:\\PYGAME PROJECTS\\assets\\gunshoot.wav")
    boss_hit_sound= pygame.mixer.Sound("E:\\PYGAME PROJECTS\\assets\\boss.wav")
   # granad_sound = pygame.mixer.Sound("E:\PYGAME PROJECTS\assets\granade2.mp3")

# Adjust volume if needed
    #shoot_sound.set_volume(0.4)   # medium
    enemy_hit_sound.set_volume(0.5)  # louder
    boss_hit_sound.set_volume(0.1)
    #granad_sound.set_volume(0.1)
    
    # # #----- #
    boss_slider_value = 0.5   # between 0 and 1
    boss_dragging = False
    MAX_BOSSES_ON_SCREEN = int(BOSS_MIN_LIMIT + boss_slider_value * (BOSS_MAX_LIMIT - BOSS_MIN_LIMIT))

    
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("FreeFire-like (Procedural Art, Offline)")
    clock = pygame.time.Clock()
    game_start_time = pygame.time.get_ticks()
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
 
    #grenede stuff
    all_sprites = pygame.sprite.Group()   # <--- ADD THIS
    grenades = pygame.sprite.Group()      # <--- ADD THIS
    # AIR DROP GROUP
    airdrops = pygame.sprite.Group()
    powerup_effects = PowerUpEffect()
    airdrop_timer = 15.0  # first drop after 15s

    # grenade timing
    grenade_cooldown = 0                  # <--- ADD THIS
    grenade_delay = 2.0  
    
    player = Player(player_surf)
    player_group.add(player)
    all_sprites.add(player)               # <--- so explosions & grenades can be managed here too
    #teamates
    teammates = pygame.sprite.Group()
    for i in range(2):  # spawn 2 AI teammates
        tx = player.pos.x + random.randint(-120, 120)
        ty = player.pos.y + random.randint(-120, 120)
        mate = Teammate(player_surf, tx, ty)
        teammates.add(mate)
        all_sprites.add(mate)

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
    enemy_slider_value = 0.1  # between 0 and 1
    enemy_dragging = False
    max_enemies = int(ENEMY_MIN_LIMIT + enemy_slider_value * (ENEMY_MAX_LIMIT - ENEMY_MIN_LIMIT))
    
    ##
    wave_counter = 0
    global cntboss
    while running:
        dt = clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_g and grenade_cooldown <= 0:
                  grenade = Grenade(player.rect.center, mouse_pos)
                  all_sprites.add(grenade)
                  grenades.add(grenade)
                  grenade_cooldown = grenade_delay
                if ev.key == pygame.K_ESCAPE:
                    running = False
                if ev.key == pygame.K_p:
                    paused = not paused
                if ev.key == pygame.K_1:
                    player.switch_weapon('rifle')
                if ev.key == pygame.K_2:
                    player.switch_weapon('pistol')
                if ev.key == pygame.K_3:
                    player.switch_weapon('BEST_GUN')
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
                if ev.key == pygame.K_e:  # melee attack
                   player.melee_attack(enemies, all_sprites)
         
            if ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:   # Left mouse button
                  mouse_shooting = True
                mx, my = ev.pos
                handle_rect = pygame.Rect(
                ENEMY_SLIDER_X + int(enemy_slider_value * (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W)),
                ENEMY_SLIDER_Y - (ENEMY_SLIDER_HANDLE_H - ENEMY_SLIDER_H) // 2,
                ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H)
                if handle_rect.collidepoint(mx, my):
                  enemy_dragging = True
            if ev.type == pygame.MOUSEBUTTONDOWN:#max boss number control panel
               if ev.button == 1:
                  mx, my = ev.pos
                  boss_handle_rect = pygame.Rect(
            BOSS_SLIDER_X + int(boss_slider_value * (BOSS_SLIDER_W - BOSS_SLIDER_HANDLE_W)),
            BOSS_SLIDER_Y - (BOSS_SLIDER_HANDLE_H - BOSS_SLIDER_H)//2,
            BOSS_SLIDER_HANDLE_W, BOSS_SLIDER_HANDLE_H
        )
                  if boss_handle_rect.collidepoint(mx, my):
                     boss_dragging = True
            if ev.type == pygame.MOUSEBUTTONUP:
                if ev.button == 1:   # Left mouse button
                  mouse_shooting = True
                  boss_dragging = False
                enemy_dragging = False

            elif ev.type == pygame.MOUSEMOTION and enemy_dragging:
                mx, my = ev.pos
                enemy_slider_value = max(0, min(1, (mx - ENEMY_SLIDER_X) / (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W)))
                max_enemies = int(ENEMY_MIN_LIMIT + enemy_slider_value * (ENEMY_MAX_LIMIT - ENEMY_MIN_LIMIT))
            elif ev.type == pygame.MOUSEMOTION and boss_dragging:
                 mx, my = ev.pos
                 boss_slider_value = max(0, min(1, (mx - BOSS_SLIDER_X) / (BOSS_SLIDER_W - BOSS_SLIDER_HANDLE_W)))
                 MAX_BOSSES_ON_SCREEN = int(BOSS_MIN_LIMIT + boss_slider_value * (BOSS_MAX_LIMIT - BOSS_MIN_LIMIT))

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        shooting = keys[pygame.K_RSHIFT] or  keys[pygame.K_LSHIFT] or pygame.mouse.get_pressed()[0]
        #if mouse_shooting:
           # shooting = True

        if not paused:
            player.update(dt, keys, mouse_pos, shooting, bullets)
            teammates.update(dt, player, enemies, bullets)

            # spawn enemies from edges
            spawn_timer -= dt
            if spawn_timer <= 0:
                spawn_timer = max(0.75 - (player.score * 0.0015), 0.28)
                #
                wave_counter += 1
                elapsed_time = (pygame.time.get_ticks() - game_start_time) / 1000
    # Every 5th wave spawn a boss
                isboss=False
                if wave_counter% BOSS_APPERENCE_DURATION == 0 :#atmax 3 boss
                   x = random.choice([-200, SCREEN_W+200])
                   y = random.randint(0, SCREEN_H)
                   boss = Boss(enemy_surf, x, y)
                   if(cntboss<MAX_BOSSES_ON_SCREEN):
                     enemies.add(boss)
                     #isboss=True
                     cntboss+=1
                #
                side = random.choice(['top','bottom','left','right'])
                if side == 'top':
                    x = random.randint(0, SCREEN_W); y = -60
                elif side == 'bottom':
                    x = random.randint(0, SCREEN_W); y = SCREEN_H + 60
                elif side == 'left':
                    x = -60; y = random.randint(0, SCREEN_H)
                else:
                    x = SCREEN_W + 60; y = random.randint(0, SCREEN_H)
                if len(enemies)<max_enemies :
                 etype = random.choices( ["runner", "tank", "sniper", "normal"], 
                                        weights=[0.1, 0.2, 0.2, 0.5])[0]
                 e = Enemy(enemy_surf, x, y, etype)
                 enemies.add(e)
            airdrop_timer -= dt
            if airdrop_timer <= 0:
                angle = random.uniform(0, 2*math.pi)
                dist = random.uniform(0, safe_radius * 0.8)
                drop_x = int(safe_center.x + math.cos(angle)*dist)
                drop_y = int(safe_center.y + math.sin(angle)*dist)
                airdrops.add(AirDrop(drop_x, drop_y))
                airdrop_timer = random.uniform(20, 35)  # next drop     

        # update ---> ADD THSIS SECTION
        
            # update enemies
            for e in list(enemies):
             e.update(dt, player, bullets)
             if e.health <= 0:
                 # enemy is dead sound
                if isinstance(e, Boss):
                       boss_hit_sound.play()
                       cntboss-=1
                       player.score += 200  # high reward
                else:
                    enemy_hit_sound.play()
                    player.score += 10
                    if random.random() < 0.33:
                        pickups.add(Pickup(random.choice(['health','ammo']), e.pos.x, e.pos.y))
                e.kill()
                   

            bullets.update(dt)#// FIX THIS
            
                # update grenades
            grenades.update(dt, enemies, all_sprites)

            # reduce grenade cooldown
            if grenade_cooldown > 0:
             grenade_cooldown -= dt


            # bullets collisions
            for b in [bb for bb in bullets if bb.owner == 'player']:
                hit = pygame.sprite.spritecollideany(b, enemies)
                if hit:
                    hit.health -= b.damage * (2 if powerup_effects.is_active('double_damage') else 1)
                    b.kill()

            for b in [bb for bb in bullets if bb.owner == 'enemy']:
                if pygame.sprite.collide_rect(b, player):
                    player.health -= b.damage
                    b.kill()

            # pickups
            # pickups
            for p in pygame.sprite.spritecollide(player, pickups, True):
                if p.kind == 'health':
                   player.health = min(PLAYER_MAX_HEALTH, player.health + 40)
                   player.score += 6
                else:
                   player.ammo += 40
                   player.score += 4

# airdrop pickups
            for a in pygame.sprite.spritecollide(player, airdrops, True):
                if a.kind == 'BEST_GUN':
                   player.switch_weapon('BEST_GUN')
                elif a.kind == 'health':
                   player.health = min(PLAYER_MAX_HEALTH, player.health + 200)
                elif a.kind == 'double_damage':
                   powerup_effects.double_damage = 12.0  # 12s effect
                elif a.kind == 'speed_boost':
                   powerup_effects.speed_boost = 10.0  # 10s effect
                player.score += 50

            powerup_effects.update(dt)
            if powerup_effects.is_active('speed_boost'):
                   player.speed = PLAYER_SPEED * 1.6
            else:
                   player.speed = PLAYER_SPEED


            #for p in pygame.sprite.spritecollide(player, pickups, True):
                #if p.kind == 'health':
                 #   player.health = min(PLAYER_MAX_HEALTH, player.health + 40)
                  #  player.score += 6
              #  else:
                   # player.ammo = min(PLAYER_MAX_AMMO, player.ammo + 40)
                  #  player.ammo +=40
                  #  player.score += 4

            # safe zone shrink behavior
            safe_shrink_timer -= dt
            if safe_shrink_timer <= 0:
                safe_shrink_timer = SAFE_ZONE_SHRINK_INTERVAL
                safe_radius = max(MIN_SAFE_ZONE_RADIOUS, int(safe_radius * SAFE_ZONE_SHRINK_FACTOR))
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
        grenades.draw(screen)
       # all_sprites.draw(screen)
        pickups.draw(screen)
        player_group.draw(screen)
        #all_sprites.draw(screen)
        #air drop events
        airdrops.draw(screen)

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
       
        grenade_text = font.render(f"Grenade CD: {max(0, round(grenade_cooldown,1))}s", True, (0,255,0))
        
        # power-up effects
        if powerup_effects.is_active('double_damage'):
          dd_text = font.render(f"Double DMG: {powerup_effects.double_damage:.1f}s", True, (255,0,0))
          screen.blit(dd_text, (hud_x, hud_y+150))

        if powerup_effects.is_active('speed_boost'):
           sb_text = font.render(f"Speed Boost: {powerup_effects.speed_boost:.1f}s", True, (0,255,255))
           screen.blit(sb_text, (hud_x, hud_y+170))
    #
        draw_minimap(screen, player, enemies, airdrops, safe_center, safe_radius)


        
        #
        # Draw boss slider track
        pygame.draw.rect(screen, (180,180,180), (BOSS_SLIDER_X, BOSS_SLIDER_Y, BOSS_SLIDER_W, BOSS_SLIDER_H))
# Draw boss slider handle
        handle2_x = BOSS_SLIDER_X + int(boss_slider_value * (BOSS_SLIDER_W - BOSS_SLIDER_HANDLE_W))
        boss_handle_rect = pygame.Rect(handle2_x, BOSS_SLIDER_Y - (BOSS_SLIDER_HANDLE_H - BOSS_SLIDER_H)//2,
                          BOSS_SLIDER_HANDLE_W, BOSS_SLIDER_HANDLE_H)
        pygame.draw.rect(screen, (255,180,0), boss_handle_rect)

# Display slider value
        font = pygame.font.SysFont(None, 22)
        text = font.render(f'Max Bosses: {MAX_BOSSES_ON_SCREEN}', True, (255,255,255))
        screen.blit(text, (BOSS_SLIDER_X, BOSS_SLIDER_Y - 25))

        # Enemy count slider bar
        
# Handle
        ENEMY_SLIDER_X, ENEMY_SLIDER_Y = hud_x,hud_y+160
        handle_x = ENEMY_SLIDER_X + int(enemy_slider_value * (ENEMY_SLIDER_W - ENEMY_SLIDER_HANDLE_W))
        handle_y = ENEMY_SLIDER_Y - (ENEMY_SLIDER_HANDLE_H - ENEMY_SLIDER_H)//2

# Label
        font_small = pygame.font.SysFont("Arial", 20)
        label = font_small.render(f"Max Enemies: {max_enemies}", True, (255,255,255))
        
        pygame.draw.rect(screen, (100,200,255), (handle_x, handle_y, ENEMY_SLIDER_HANDLE_W, ENEMY_SLIDER_HANDLE_H))
        pygame.draw.rect(screen, (180,180,180), (ENEMY_SLIDER_X, ENEMY_SLIDER_Y, ENEMY_SLIDER_W, ENEMY_SLIDER_H))
        screen.blit(health_text, (hud_x, hud_y))
        screen.blit(ammo_text, (hud_x, hud_y+24))
        screen.blit(score_text, (hud_x, hud_y+48))
        screen.blit(weapon_text, (hud_x, hud_y+72))
        screen.blit(safe_text, (hud_x, hud_y+100))
        screen.blit(grenade_text, (hud_x, hud_y+130))
        screen.blit(label, (hud_x, hud_y+180))
       # screen.blit(label, (ENEMY_SLIDER_X + ENEMY_SLIDER_W + 20, ENEMY_SLIDER_Y - 10))
# draw knife swings / hit sparks / explosions
        
        #
        if paused and player.health <= 0:
            gg = big_font.render('YOU DIED', True, (255,80,80))
            sub = font.render('Press R to restart or ESC to quit', True, (220,220,220))
            cntboss=0
            screen.blit(gg, gg.get_rect(center=(SCREEN_W/2, SCREEN_H/2 - 20)))
            screen.blit(sub, sub.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 30)))

        pygame.display.flip()

    pygame.quit()

if __name__ == '__main__':
    main()