from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
import random

app = Ursina()

# --- Window settings ---
window.title = "Mini 3D Valorant"
window.borderless = False
window.fullscreen = False
window.exit_button.visible = True
window.fps_counter.enabled = True

# --- Terrain ---
ground = Entity(model='plane', scale=(50,1,50), texture='white_cube',
                texture_scale=(50,50), collider='box', color=color.light_gray)

# --- Walls / obstacles ---
walls = []
for i in range(5):
    w = Entity(model='cube', scale=(2,4,6),
               position=(random.randint(-20,20),2,random.randint(-20,20)),
               color=color.gray, collider='box')
    walls.append(w)

# --- Player body ---
player_body = Entity(model='cube', scale=(1,2,1), color=color.azure)

player = FirstPersonController(model=None)
player.gravity = 0.5
player.speed = 6
player.position = (0,2,0)
player.health = 100

# --- Camera (3rd person view) ---
camera.parent = player
camera.position = (0,3,-6)
camera.rotation_x = 15

# --- Bullets ---
class Bullet(Entity):
    def __init__(self, position, direction, owner="player"):
        super().__init__(
            model='sphere',
            scale=0.2,
            color=color.yellow if owner=="player" else color.red,
            position=position,
            collider='box'
        )
        self.direction = direction
        self.speed = 20
        self.owner = owner

    def update(self):
        self.position += self.direction * time.dt * self.speed
        # collide with walls
        for w in walls:
            if self.intersects(w).hit:
                destroy(self)
                return
        # collide with bots
        if self.owner == "player":
            for b in bots:
                if b.enabled and self.intersects(b).hit:
                    b.health -= 50
                    destroy(self)
                    return
        # collide with player
        elif self.owner == "bot":
            if self.intersects(player_body).hit:
                player.health -= 20
                destroy(self)
                return

bullets = []

def shoot():
    direction = player.forward
    b = Bullet(player.position + direction*1.5, direction, owner="player")
    bullets.append(b)

# --- Bots (enemies) ---
class Bot(Entity):
    def __init__(self, position=(0,2,0)):
        super().__init__(
            model='sphere',
            scale=(1.2,1.2,1.2),
            position=position,
            color=color.red,
            collider='box'
        )
        self.speed = 3
        self.health = 100
        self.shoot_timer = 0

    def update(self):
        if self.health <= 0:
            self.disable()
            # Respawn after 3 sec
            invoke(self.respawn, delay=3)
            return
        # Move toward player
        dir = player.position - self.position
        dist = dir.length()
        if dist > 3:
            self.position += dir.normalized() * time.dt * self.speed
        # Shoot at player
        self.shoot_timer += time.dt
        if dist < 20 and self.shoot_timer > 1.5:
            direction = dir.normalized()
            b = Bullet(self.position + direction*1.5, direction, owner="bot")
            bullets.append(b)
            self.shoot_timer = 0

    def respawn(self):
        self.enable()
        self.position = (random.randint(-20,20), 1, random.randint(-20,20))
        self.health = 100

bots = [Bot(position=(random.randint(-20,20),1,random.randint(-20,20))) for _ in range(3)]

# --- Input ---
def input(key):
    if key == 'left mouse down':
        shoot()

# --- Update loop ---
def update():
    # Keep player body synced
    player_body.position = player.position
    player_body.y = 1  # align properly

    # Remove destroyed bullets
    for b in bullets[:]:
        if not b.enabled:
            bullets.remove(b)

    # Update bots
    for bot in bots:
        if bot.enabled:
            bot.update()

    # Handle player death & respawn
    if player.health <= 0:
        player.health = 100
        player.position = (random.randint(-20,20), 2, random.randint(-20,20))

# --- Lighting ---
DirectionalLight(y=2, z=3, shadows=True)
Sky()

app.run()
