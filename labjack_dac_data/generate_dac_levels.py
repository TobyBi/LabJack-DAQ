# TODO: remove this when converting to a package
import sys
sys.path.append("..")
import pandas as pd
import numpy as np

import lj_helpers as ljh

save = True
df = pd.DataFrame()

handle = ljh.open_lj("T7")
ljh.reset_dac(handle)

V_steps_binary = np.arange(0, 2**16, 1)
df["binary_input"] = V_steps_binary

labjack_ports = ["DAC0", "DAC1", "AIN0", "AIN1"]

for i in range(1, 11):
    V_save_16 = {ports: [] for ports in labjack_ports}
    print("at run no. {0}".format(i))

    for binary in V_steps_binary:
        print("step no. {0}".format(binary), end="\r")
        ljh.ljm.eWriteName(handle, "DAC0_BINARY", binary)
        ljh.ljm.eWriteName(handle, "DAC1_BINARY", binary)
        
        for ports in labjack_ports:
            V_save_16[ports].append(ljh.ljm.eReadName(handle, ports))
        
    df["D0_set_output_{0}".format(i)] = V_save_16["DAC0"]
    df["D0_actual_output_{0}".format(i)] = V_save_16["AIN0"]
    
    df["D1_set_output_{0}".format(i)] = V_save_16["DAC1"]
    df["D1_actual_output_{0}".format(i)] = V_save_16["AIN1"]

if save:
    df.to_csv("./t7_dac_levels.csv", index=False)