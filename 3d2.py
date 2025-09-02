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
ground = Entity(model='plane', scale=(50,1,50), texture='white_cube', texture_scale=(50,50), collider='box', color=color.light_gray)

# --- Walls / obstacles ---
walls = []
for i in range(5):
    w = Entity(model='cube', scale=(2,4,6),
               position=(random.randint(-20,20),2,random.randint(-20,20)),
               color=color.gray, collider='box')
    walls.append(w)

# --- Player ---
player = FirstPersonController()
player.gravity = 0.5
player.speed = 6
player.position = (0,2,0)

# --- Bots ---
class Bot(Entity):
    def __init__(self, position=(0,2,0), color=color.red):
        super().__init__(
            model='cube',
            scale=(1,2,1),
            position=position,
            color=color,
            collider='box'
        )
        self.speed = 4
        self.health = 100
    
    def update(self):
        if self.health <= 0:
            self.disable()
            return
        # simple AI: follow player
        dir = player.position - self.position
        dist = dir.length()
        if dist > 2:
            self.position += dir.normalized() * time.dt * self.speed

bots = [Bot(position=(random.randint(-20,20),1,random.randint(-20,20))) for _ in range(3)]

# --- Bullets ---
class Bullet(Entity):
    def __init__(self, position, direction):
        super().__init__(
            model='sphere',
            scale=0.2,
            color=color.yellow,
            position=position,
            collider='box'
        )
        self.direction = direction
        self.speed = 20

    def update(self):
        self.position += self.direction * time.dt * self.speed
        # collide with walls
        for w in walls:
            if self.intersects(w).hit:
                destroy(self)
                return
        # collide with bots
        for b in bots:
            if b.enabled and self.intersects(b).hit:
                b.health -= 50
                destroy(self)
                return

bullets = []

def shoot():
    # spawn bullet from player forward
    direction = player.forward
    b = Bullet(player.position + direction*1.5, direction)
    bullets.append(b)

# --- Input ---
def input(key):
    if key == 'left mouse down':
        shoot()

# --- Update loop ---
def update():
    for b in bullets[:]:
        if not b.enabled:
            bullets.remove(b)
    for bot in bots:
        bot.update()

# --- Lighting ---
DirectionalLight(y=2, z=3, shadows=True)
Sky()

app.run()
