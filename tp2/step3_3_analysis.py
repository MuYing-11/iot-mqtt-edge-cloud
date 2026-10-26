"""TP2 - Step 3.3: offline analysis.

1. Centred moving average x_i = 1/(2M+1) * sum_{j=-M..M} x[i+j] on the whole dataset
   (original vs smoothed curves, like the "Melbourne temperatures" figure of the lab sheet).
2. Accuracy of the two edge reductions recorded in steps 2 and 3: each value received by the
   cloud is compared with the centred moving average of the raw data at the same instant
   (reference trend), and the jitter of each reduced curve is measured.

usage: python step3_3_analysis.py <img_dir>
"""
import json
import os
import sys

import matplotlib.pyplot as plt
import numpy as np

from sensor_sim import generate_dataset

out_dir = sys.argv[1] if len(sys.argv) > 1 else "."

# ---------- 1. centred moving average on the dataset
M = 25
data = np.array(generate_dataset(5000))
smooth = np.convolve(data, np.ones(2 * M + 1) / (2 * M + 1), mode="valid")
plt.figure(figsize=(11, 4.2))
plt.plot(data, label="Original", color="#1f77b4", linewidth=0.7)
plt.plot(np.arange(M, M + len(smooth)), smooth, label=f"Smooth (moving average, M={M})", color="#ff7f0e", linewidth=2)
plt.title("Centred moving average on the simulated dataset")
plt.xlabel("sample index")
plt.ylabel("temperature (°C)")
plt.legend()
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, "tp2_step3_3_offline_ma.png"), dpi=130)


# ---------- 2. accuracy of the recorded reductions
def evaluate(path, half_window_s=1.5, shift_s=0.0):
    with open(path) as f:
        d = json.load(f)
    raw = np.array(d["raw"])
    red = np.array(d["reduced"])
    errors = []
    for t, v in red:
        t += shift_s
        sel = raw[(raw[:, 0] >= t - half_window_s) & (raw[:, 0] <= t + half_window_s)]
        if len(sel):
            errors.append(v - sel[:, 1].mean())
    errors = np.array(errors)
    return {
        "raw_msgs": len(raw), "cloud_msgs": len(red),
        "raw_bytes": d["raw_bytes"], "cloud_bytes": d["cloud_bytes"],
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "bias": float(errors.mean()),
        "jitter": float(np.std(np.diff(red[:, 1]))),
    }


results = {}
# sampling values are stamped at the end of their 2 s period; "sampling_centred" re-times them
# at the middle of the period for a fair comparison with the centred moving average
for name, f, shift in (("sampling", "tp2_step2_sampling_vs_raw.json", 0.0),
                       ("sampling_centred", "tp2_step2_sampling_vs_raw.json", -1.0),
                       ("moving_average", "tp2_step3_moving_vs_raw.json", 0.0)):
    p = os.path.join(out_dir, f)
    if os.path.exists(p):
        results[name] = evaluate(p, shift_s=shift)
print(json.dumps(results, indent=2))
with open(os.path.join(out_dir, "tp2_metrics.json"), "w") as f:
    json.dump(results, f, indent=2)
