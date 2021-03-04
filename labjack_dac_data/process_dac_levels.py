import numpy as np
import pandas as pd
from collections import Counter

save = True
df = pd.read_csv("./t7_dac_levels.csv")

all_runs = {
    "DAC0": np.array(df[["D0_set_output_{0}".format(i) for i in range(1, 11)]]),
    "DAC1": np.array(df[["D1_set_output_{0}".format(i) for i in range(1, 11)]]),
    "AIN0": np.array(df[["D0_actual_output_{0}".format(i) for i in range(1, 11)]]),
    "AIN1": np.array(df[["D1_actual_output_{0}".format(i) for i in range(1, 11)]])
}

most_common = {key: [max(arr, key=Counter(arr).get) for arr in all_runs[key]] for key in all_runs.keys()}

binary_df = pd.DataFrame(df["binary_input"])

for key in most_common.keys():
    binary_df[key] = most_common[key]

df_12bit = pd.DataFrame(index=np.arange(2**12))
df_12bit["AIN0"] = None
df_12bit["AIN1"] = None

# obtaining most common voltage value in the set 
for i in range(0, len(binary_df), 16):
    df_12bit["AIN0"][int(i/16)] = max(binary_df["AIN0"][i:i+16], key=Counter(binary_df["AIN0"][i:i+16]).get)
    df_12bit["AIN1"][int(i/16)] = max(binary_df["AIN1"][i:i+16], key=Counter(binary_df["AIN1"][i:i+16]).get)


if save:
    binary_df.to_csv("./t7_aggr_dac_levels.csv", index=False)
    df_12bit.to_csv("./t7_12bit_dac_levels.csv", index=False)