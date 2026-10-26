3
000000000000000"""TP2 - Step 1.1: generate the simulated dataset and plot it."""
import sys

import matplotlib.pyplot as plt

from sensor_sim import generate_dataset

N = 5000
dataset = generate_dataset(N, seed=12345, mean=20, sd=5)
print(f"{N} values generated, min={min(dataset):.2f} max={max(dataset):.2f} "
      f"mean={sum(dataset) / N:.2f}")

plt.figure(figsize=(11, 4))
plt.plot(range(N), dataset, color="black", linewidth=0.7)
plt.xlabel("sample index")
plt.ylabel("temperature (°C)")
plt.title("Simulated sensor dataset (seed=12345, mean=20, sd=5)")
plt.grid(alpha=0.3)
plt.tight_layout()
if len(sys.argv) > 1:
    plt.savefig(sys.argv[1], dpi=130)
else:
    plt.show()
