import math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# ----------------------------
# Utility functions
# ----------------------------
def normalize(v):
    return v / np.linalg.norm(v)

def reflect(direction, normal):
    # Reflect a vector about a normal
    return direction - 2 * np.dot(direction, normal) * normal

def schlick_fresnel(cos_theta, n1=1.0, n2=1.5):
    # Schlick's approximation for Fresnel reflectance
    r0 = ((n1 - n2) / (n1 + n2)) ** 2
    return r0 + (1 - r0) * ((1 - cos_theta) ** 5)

def rotate(vec, theta):
    # 2D rotation of a vector by angle theta
    c, s = math.cos(theta), math.sin(theta)
    R = np.array([[c, -s], [s, c]])
    return R.dot(vec)

# ----------------------------
# Mirror definition
# ----------------------------
mirror_center = np.array([0.0, 0.0])
mirror_length = 6.0
mirror_angle = math.radians(20)  # mirror tilt
mirror_dir = np.array([math.cos(mirror_angle), math.sin(mirror_angle)])
mirror_normal = np.array([-mirror_dir[1], mirror_dir[0]])  # perpendicular
mirror_half = mirror_dir * (mirror_length / 2.0)
mirror_p1 = mirror_center - mirror_half
mirror_p2 = mirror_center + mirror_half

# ----------------------------
# Light source
# ----------------------------
source = np.array([-6.0, -1.5])  # point source
num_rays = 400
max_bounces = 6
n_air = 1.0
n_mirror = 1.5

cone_direction = normalize(np.array([1.0, 0.2]))
cone_angle = math.radians(40)  # spread angle
angles = np.linspace(-cone_angle, cone_angle, num_rays)
rays_dirs = [normalize(rotate(cone_direction, th)) for th in angles]

# ----------------------------
# Intersection helper
# ----------------------------
def intersect_ray_segment(p, d, p1, p2):
    v = p2 - p1
    mat = np.array([d, -v]).T  # 2x2 system
    try:
        sol = np.linalg.solve(mat, p1 - p)
    except np.linalg.LinAlgError:
        return None
    t, u = sol[0], sol[1]
    if t > 1e-8 and 0 <= u <= 1:
        return t, u
    return None

# ----------------------------
# Plot setup
# ----------------------------
fig, ax = plt.subplots(figsize=(10, 6))
ax.set_aspect('equal', adjustable='box')
ax.set_xlim(-8, 8)
ax.set_ylim(-6, 6)
ax.set_title('Light Reflection Simulation (Fresnel + Multiple Bounces)')

# Draw mirror
ax.plot([mirror_p1[0], mirror_p2[0]], [mirror_p1[1], mirror_p2[1]], linewidth=4, color="black")

# Draw source
ax.scatter([source[0]], [source[1]], s=40, color="red", label="Light Source")

# ----------------------------
# Ray tracing
# ----------------------------
all_segments = []  # (x0, y0, x1, y1, intensity)

for d0 in rays_dirs:
    p = source.copy()
    d = d0.copy()
    intensity = 1.0
    for bounce in range(max_bounces):
        hit = intersect_ray_segment(p, d, mirror_p1, mirror_p2)
        if hit is None:
            # No intersection, draw until out of bounds
            t_far = 20.0
            p2 = p + d * t_far
            all_segments.append((p[0], p[1], p2[0], p2[1], intensity))
            break
        t, u = hit
        hit_point = p + d * t
        all_segments.append((p[0], p[1], hit_point[0], hit_point[1], intensity))
        normal = mirror_normal.copy()
        if np.dot(normal, d) > 0:  # flip normal if pointing wrong way
            normal = -normal
        cos_theta = np.dot(-d, normal)
        cos_theta = max(0.0, min(1.0, cos_theta))
        R = schlick_fresnel(cos_theta, n_air, n_mirror)
        intensity *= R
        d = normalize(reflect(d, normal))
        p = hit_point + d * 1e-6
        if intensity < 1e-3:
            p2 = p + d * 0.5
            all_segments.append((p[0], p[1], p2[0], p2[1], intensity))
            break

# ----------------------------
# Draw all rays
# ----------------------------
for (x0, y0, x1, y1, I) in all_segments:
    alpha = max(0.05, min(1.0, I))
    lw = 0.3 + 2.5 * alpha
    ax.plot([x0, x1], [y0, y1], linewidth=lw, alpha=alpha, color="blue")

ax.legend()
ax.grid(True)

# ----------------------------
# Save image in same folder as script
# ----------------------------
script_dir = Path(__file__).parent
out_path = script_dir / "light_reflection_simulation.png"
plt.savefig(out_path, dpi=150, bbox_inches='tight')
plt.show()

print(f"Saved simulation image to: {out_path}")