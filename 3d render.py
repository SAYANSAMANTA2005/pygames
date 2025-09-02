from ursina import *

app = Ursina()

# --- Camera ---
camera.position = (0, 30, -30)
camera.rotation_x = 60

# --- Floor ---
floor = Entity(
    model='plane',
    scale=(50,1,50),
    color=color.gray,
    texture='white_cube',
    texture_scale=(10,10)
)

# --- Walls (like Valorant map obstacles) ---
walls = []

# Simple rectangular walls
wall_positions = [
    ((0,1,10), (10,2,1)),
    ((-10,1,0), (1,2,20)),
    ((10,1,0), (1,2,20)),
    ((0,1,-10), (10,2,1)),
    ((5,1,5), (3,2,1)),
]

for pos, scale in wall_positions:
    w = Entity(
        model='cube',
        color=color.dark_gray,
        position=pos,
        scale=scale
    )
    walls.append(w)

# --- Player (movable camera target) ---
player = Entity(model='cube', color=color.blue, scale=(1,2,1), position=(0,1,0))

# Movement speed
SPEED = 5

def update():
    move = Vec3(
        (held_keys['d'] - held_keys['a']),
        0,
        (held_keys['w'] - held_keys['s'])
    ) * time.dt * SPEED
    player.position += move
    # Camera follows player
    camera.position = player.position + Vec3(0, 20, -20)
    camera.look_at(player)

app.run()
