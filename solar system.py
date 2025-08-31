"""
solar_system.py

Standalone animation of a simplified solar system (2D projection).

Features:
- 8 planets orbiting the Sun with relative distance ratios (Mercury...Neptune).
- Each planet shows a day/night side (simple hemisphere shading based on Sun direction).
- Moons for Earth, Jupiter, Saturn with their own orbits.
- Basic eclipse detection: if a planet/moon lies in the shadow cast by an occluder (another body),
  its night overlay darkens (simple 2D projection test).
- Animated with matplotlib.animation.FuncAnimation.

Run:
    python solar_system.py

Optional: to save animation as MP4/GIF, install ffmpeg and uncomment the anim.save(...) line.
"""
import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation, patches

# ----------------------------
# System parameters (visual scale)
# ----------------------------
planet_names = ["Mercury","Venus","Earth","Mars","Jupiter","Saturn","Uranus","Neptune"]
# relative semi-major axes (AU-like)
a_vals = np.array([0.39, 0.72, 1.00, 1.52, 5.20, 9.58, 19.2, 30.05])
# scale to fit figure
DIST_SCALE = 0.25
a = a_vals * DIST_SCALE

# visual radii (exaggerated for visibility)
r_planets = np.array([0.02, 0.05, 0.06, 0.04, 0.12, 0.10, 0.08, 0.08])

# planet colors (visual)
planet_colors = [
    "#9e9e9e", "#e6c07b", "#2a7bff", "#c1440e",
    "#d9a066", "#e6d4a6", "#9bd3e6", "#3b3f9f"
]

# orbital periods approximate T ~ a^(3/2) — angular speed omega = 2π/T
periods = a_vals ** 1.5
omega = 2 * np.pi / periods

# Moons: map planet index -> list of moons (distance, radius, color, angular speed)
moons = {
    2: [  # Earth -> Moon
        {"a": 0.12, "r": 0.015, "color":"#cccccc", "omega": 2*np.pi/0.3}
    ],
    4: [  # Jupiter -> two big-ish moons for visualization
        {"a": 0.28, "r": 0.03,  "color":"#dddddd", "omega": 2*np.pi/0.4},
        {"a": 0.40, "r": 0.025, "color":"#bbbbbb", "omega": 2*np.pi/0.6}
    ],
    5: [  # Saturn -> one moon
        {"a": 0.22, "r": 0.02, "color":"#eeeeee", "omega": 2*np.pi/0.5}
    ]
}

# Sun
sun_radius = 0.25
sun_color = "#ffd24d"

# animation controls
NUM_FRAMES = 800
DT = 0.02  # time increment per frame
FIG_SIZE = 10

# ----------------------------
# Utility functions
# ----------------------------
def normalize(v):
    n = np.linalg.norm(v)
    return v / (n + 1e-12)

def in_shadow(target_pos, target_r, occluder_pos, occluder_r, sun_pos=(0.0,0.0)):
    """
    Very simple 2D shadow test:
    - check if the line segment from sun -> target intersects the occluder circle (occluder_pos, occluder_r)
    - and occluder lies between sun and target (projection parameter u in (0,1))
    If both true, consider target in shadow (umbra approx).
    """
    s = np.array(sun_pos, dtype=float)
    t = np.array(target_pos, dtype=float)
    o = np.array(occluder_pos, dtype=float)
    st = t - s
    if np.linalg.norm(st) < 1e-8:
        return False
    u = np.dot(o - s, st) / np.dot(st, st)
    if not (0.0 < u < 1.0):
        return False
    closest = s + u * st
    dist = np.linalg.norm(closest - o)
    return dist < occluder_r

# ----------------------------
# Setup figure and static artists
# ----------------------------
fig, ax = plt.subplots(figsize=(FIG_SIZE, FIG_SIZE))
ax.set_aspect('equal', adjustable='box')
R_LIMIT = 8 * DIST_SCALE
ax.set_xlim(-R_LIMIT, R_LIMIT)
ax.set_ylim(-R_LIMIT, R_LIMIT)
ax.axis('off')
ax.set_title("Simplified Solar System — Orbits, Illumination & Eclipses", fontsize=14)

# draw orbit paths (thin dashed)
orbit_lines = []
for ai in a:
    theta = np.linspace(0, 2*np.pi, 360)
    xs = ai * np.cos(theta)
    ys = ai * np.sin(theta)
    line, = ax.plot(xs, ys, lw=0.6, linestyle='--', color='0.5')
    orbit_lines.append(line)

# Sun patch
sun_patch = patches.Circle((0,0), sun_radius, facecolor=sun_color, edgecolor='orange', zorder=6)
ax.add_patch(sun_patch)

# planet patches and night overlays + labels
planet_patches = []
night_patches = []
labels = []
for i in range(len(a)):
    p = patches.Circle((0,0), r_planets[i], facecolor=planet_colors[i], edgecolor='k', zorder=8)
    night = patches.Circle((0,0), r_planets[i], facecolor='k', alpha=0.4, zorder=9)
    ax.add_patch(p)
    ax.add_patch(night)
    planet_patches.append(p)
    night_patches.append(night)
    lab = ax.text(0, 0, planet_names[i], fontsize=7, ha='center', va='bottom', zorder=10)
    labels.append(lab)

# moon patches
moon_patches = {i: [] for i in range(len(a))}
for pi, mlist in moons.items():
    for m in mlist:
        mp = patches.Circle((0,0), m["r"], facecolor=m["color"], edgecolor='k', zorder=9)
        ax.add_patch(mp)
        moon_patches[pi].append(mp)

# simple "observer direction" used to compute apparent illuminated fraction
observer_dir = normalize(np.array([1.0, -0.25]))

# ----------------------------
# Animation update function
# ----------------------------
def update(frame):
    t = frame * DT
    artists = []

    # update each planet
    for i, ai in enumerate(a):
        ang = omega[i] * t
        x = ai * math.cos(ang)
        y = ai * math.sin(ang)
        planet_patches[i].center = (x, y)
        labels[i].set_position((x, y + r_planets[i] + 0.01))

        # illuminated side: compute vector from planet to sun
        v_to_sun = normalize(np.array([0.0 - x, 0.0 - y]))
        # place the night overlay center offset opposite sun direction
        offset = 0.55 * r_planets[i]
        night_center = (x - v_to_sun[0] * offset, y - v_to_sun[1] * offset)
        night_patches[i].center = night_center

        # check for eclipses: if planet in shadow of ANY other planet/occluder, darken
        hidden = False
        for j in range(len(a)):
            if j == i:
                continue
            oc_pos = planet_patches[j].center
            oc_r = r_planets[j]
            if in_shadow((x,y), r_planets[i], oc_pos, oc_r):
                hidden = True
                break
        # also check sun occlusion by moons (rare) - omitted for clarity

        if hidden:
            night_patches[i].set_alpha(0.95)
        else:
            # approximate phase: cosine of angle between sun_dir and observer_dir
            sun_dir = normalize(-v_to_sun)  # direction from planet toward sun
            cos_phase = np.dot(sun_dir, observer_dir)
            frac_illuminated = (1.0 + cos_phase) / 2.0  # between 0 and 1
            # night overlay alpha = inverse of illuminated fraction, clamped
            alpha = max(0.12, 1.0 - frac_illuminated)
            night_patches[i].set_alpha(alpha)

        artists += [planet_patches[i], night_patches[i], labels[i]]

        # update moons for this planet if present
        if i in moons:
            for mi, m in enumerate(moons[i]):
                m_ang = m["omega"] * t + 0.3*mi
                mx = x + m["a"] * math.cos(m_ang)
                my = y + m["a"] * math.sin(m_ang)
                moon_patches[i][mi].center = (mx, my)
                # check if moon in shadow of parent planet
                if in_shadow((mx,my), m["r"], (x,y), r_planets[i]):
                    moon_patches[i][mi].set_alpha(0.25)
                else:
                    moon_patches[i][mi].set_alpha(1.0)
                artists.append(moon_patches[i][mi])

    return artists

# ----------------------------
# Create animation
# ----------------------------
anim = animation.FuncAnimation(fig, update, frames=NUM_FRAMES, interval=30, blit=False)

# To save the animation uncomment and ensure you have ffmpeg installed:
# anim.save("solar_system.mp4", dpi=150, fps=30, extra_args=['-vcodec', 'libx264'])

# Display animation window (will pop up when run normally)
plt.show()