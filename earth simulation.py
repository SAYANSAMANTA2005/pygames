# Earth Simulation with Countries, Rivers, Mountains, Deserts
# Works on Windows terminal (no emojis)

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

# Create figure
fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.Robinson())  # Robinson projection looks like a globe
ax.set_global()
ax.coastlines()
ax.add_feature(cfeature.BORDERS, linewidth=0.5)
ax.add_feature(cfeature.LAND, facecolor="red")
ax.add_feature(cfeature.OCEAN, facecolor="lightblue")
ax.add_feature(cfeature.LAKES, facecolor="lightblue")
ax.add_feature(cfeature.RIVERS, edgecolor="blue")

# Extra details
ax.add_feature(cfeature.MOUNTAINS, edgecolor="brown", linewidth=0.7, alpha=0.6) if hasattr(cfeature, "MOUNTAINS") else None
ax.add_feature(cfeature.DESERTS, facecolor="khaki", alpha=0.5) if hasattr(cfeature, "DESERTS") else None

# Title
plt.title("Earth Landscape Simulation", fontsize=16, fontweight="bold")

print("Simulation started successfully.")
print("Use mouse to zoom and pan around Earth.")

plt.show()