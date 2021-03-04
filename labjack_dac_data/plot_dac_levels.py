import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("./t7_aggr_dac_levels.csv")

print("minium DAC0 set {0}V and actual {1}V".format(min(df["DAC0"]), min(df["AIN0"])))
print("maximum DAC0 set {0}V and actual {1}V".format(max(df["DAC0"]), max(df["AIN0"])))
print("minium DAC1 set {0}V and actual {1}V".format(min(df["DAC1"]), min(df["AIN1"])))
print("maximum DAC1 set {0}V and actual {1}V".format(max(df["DAC1"]), max(df["AIN1"])))

plt.close(0)
fig, ax = plt.subplots(num=0, ncols=2, figsize=(15, 7))

ax[0].plot(df["binary_input"], df["DAC0"], label="set")
ax[0].plot(df["binary_input"], df["AIN0"], marker="x", ls="None", label="actual")

ax[0].set_xlabel("bit input")
ax[0].set_ylabel("voltage")
ax[0].set_title("DAC0")
ax[0].legend()
ax[0].grid(True, which="both", axis="both")

ax[1].plot(df["binary_input"], df["DAC1"], label="set")
ax[1].plot(df["binary_input"], df["AIN1"], marker="x", ls="None", label="actual")

ax[1].set_xlabel("bit input")
ax[1].set_ylabel("voltage")
ax[1].set_title("DAC1")
ax[1].legend()
ax[1].grid(True, which="both", axis="both")

fig.tight_layout()