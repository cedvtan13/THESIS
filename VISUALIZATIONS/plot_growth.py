import os
import matplotlib.pyplot as plt
import pandas as pd

# Path to your thesis growth dataset
CSV_PATH = "/home/crk/thesis/growth_dataset.csv"

# Fallback to local working directory if running on your laptop
if not os.path.exists(CSV_PATH):
  CSV_PATH = "growth_dataset.csv"

df = pd.read_csv(CSV_PATH)

# Clean and enforce correct numeric datatypes
df["day"] = pd.to_numeric(df["day"], errors="coerce")
df["raw_gpr"] = pd.to_numeric(df["raw_gpr"], errors="coerce")
df["sm_pct"] = pd.to_numeric(df["sm_pct"], errors="coerce")

# Pivot tables: Day on rows, Pots on columns
gpr_pivot = df.pivot(index="day", columns="pot_id", values="raw_gpr")
sm_pivot = df.pivot(index="day", columns="pot_id", values="sm_pct")

# Define distinct color & marker styles for 9 pots
markers = ["o", "s", "^", "D", "v", "<", ">", "p", "h"]
colors = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10), sharex=True)

# ----------------- Subplot 1: GPR vs. Day -----------------
for idx, pot in enumerate(gpr_pivot.columns):
  ax1.plot(
      gpr_pivot.index,
      gpr_pivot[pot],
      marker=markers[idx % len(markers)],
      color=colors[idx % len(colors)],
      linewidth=1.8,
      markersize=6,
      label=pot,
  )

ax1.set_title(
    "Pechay Canopy Growth: Daily Green Pixel Ratio (GPR)",
    fontsize=13,
    fontweight="bold",
)
ax1.set_ylabel("Green Pixel Ratio (%)", fontsize=11)
ax1.grid(True, linestyle="--", alpha=0.6)
ax1.legend(title="Pot ID", bbox_to_anchor=(1.02, 1), loc="upper left")

# ----------------- Subplot 2: SM% vs. Day -----------------
for idx, pot in enumerate(sm_pivot.columns):
  ax2.plot(
      sm_pivot.index,
      sm_pivot[pot],
      marker=markers[idx % len(markers)],
      color=colors[idx % len(colors)],
      linewidth=1.8,
      markersize=6,
      label=pot,
  )

# Add reference lines for germination baseline band (50% - 60%)
ax2.axhspan(
    50,
    60,
    color="green",
    alpha=0.15,
    label="Uniform Target Band (50-60%)",
)

ax2.set_title(
    "Soil Moisture Dynamics: Volumetric Water Content (% VWC)",
    fontsize=13,
    fontweight="bold",
)
ax2.set_xlabel("Growth Cycle (Days)", fontsize=11)
ax2.set_ylabel("Soil Moisture (% VWC)", fontsize=11)
ax2.set_ylim(0, 105)
ax2.grid(True, linestyle="--", alpha=0.6)
ax2.legend(title="Pot ID", bbox_to_anchor=(1.02, 1), loc="upper left")

plt.tight_layout()

# Save publication-ready figure
output_path = "/home/crk/growth_visualization.png"
if not os.path.exists("/home/crk"):
  output_path = "growth_visualization.png"

plt.savefig(output_path, dpi=300)
print(f"Chart saved successfully to: {output_path}")