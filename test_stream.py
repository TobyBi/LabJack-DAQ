from labjack import ljm
import numpy as np

import time

def round_nearest_power_of_base(val, base, power=False):
    """
    Rounds value to the nearest power of given base.

    Parameters
    ----------
    val : float
        value to round
    base : float
        base to find closest power of

    Returns
    -------
    ans : float
        base**rounded_power
    """
    rounded_power = int(round(np.log(val) / np.log(base)))
    if power:
        ans = rounded_power
    else:
        ans = base**rounded_power
    return ans


def reset_dac(handle):
    ljm.eWriteNames(handle, 2, ["DAC0", "DAC1", [0, 0]])

def init_stream(handle, stream_num, data, out_target, loop_size):
    max_data_length = 0
    scan_list = []
    scan_list.append(ljm.nameToAddress("STREAM_OUT{0}".format(stream_num))[0])
    max_data_length = len(data) if len(data) > max_data_length else max_data_length

    if max_data_length > 2**14:
        raise ValueError

    buffer_size = 2**(round_nearest_power_of_base(len(data), 2, power=True) + 1)
    print("{0} buffer size and {1} data length".format(buffer_size, len(data)))

    ljm.eWriteName(handle, "STREAM_OUT{0}_BUFFER_SIZE".format(stream_num), buffer_size)
    ljm.eWriteName(handle, "STREAM_OUT{0}_TARGET".format(stream_num), ljm.nameToAddress(out_target)[0])
    ljm.eWriteName(handle, "STREAM_OUT{0}_ENABLE".format(stream_num), 1)
    ljm.eWriteName(handle, "STREAM_OUT{0}_LOOP_SIZE".format(stream_num), loop_size)
    ljm.eWriteName(handle, "STREAM_OUT{0}_SET_LOOP".format(stream_num), 1)

    ljm.eWriteNameArray(handle, "STREAM_OUT{0}_BUFFER_U16".format(stream_num), len(data), data)

    return scan_list

def test_buffer_size(handle):
    data_1 = np.arange(0, int(2**16), 25)
    data_2 = np.repeat(np.arange(0, int(2**16), 25), 2)

    print("data_1 len: {0}, first: {1}, last: {2}".format(len(data_1), data_1[0], data_1[-1]))
    print("data_2 len: {0}, first: {1}, last: {2}".format(len(data_2), data_2[0], data_2[-1]))

    scan_rate = 1000

    scan_list = init_stream(handle, 0, data_1, "DAC0", 0) + init_stream(handle, 1, data_2, "DAC1", 0)

    reset_dac(handle)

    slp = 1.02*(max([len(data_2), len(data_1)]) / scan_rate)

    print("time: {0}s".format(slp))
    user = input("default or custom sleep time? ")
    try:
        slp = int(user)
    except:
        print("quiting")

    if user != "q":
        print("default sleep time!")

        try:
            ljm.eStreamStart(handle, 1, len(scan_list), scan_list, scan_rate)
            time.sleep(slp)

        except ljm.LJMError:
            print("error")

        reset_dac(handle)
        ljm.eStreamStop(handle)
        ljm.close(handle)

def test_stream_time(handle):
    reset_dac(handle)
    full_data = np.arange(0, int(2**16), 1)
    chunk_size = 2**13 - 1
    print("full_data len: {0}, first: {1}, last: {2}".format(len(full_data), full_data[0], full_data[-1]))
    scan_rate = 1000
    scan_list = init_stream(handle, 0, full_data[:2**13-1], "DAC0", chunk_size)

    slp = 1.02*(chunk_size/ scan_rate)

    print("sleep time: {0}s".format(slp))

    try:
        print("starting scan no. 1")
        ljm.eStreamStart(handle, 1, len(scan_list), scan_list, scan_rate)
        time.sleep(0.5)
        buffer_status = ljm.eReadName(handle, "STREAM_OUT0_BUFFER_STATUS")
        print(buffer_status)
        time.sleep(slp)


        # while True:
        #     buffer_status = ljm.eReadName(handle, "STREAM_OUT0_BUFFER_STATUS")
        #     time.sleep(1/scan_rate)


        # for i, bit in enumerate([12, 13, 14, 15]):
        #     print("starting scan no. {0}".format(i + 2))
        #     ljm.eWriteNameArray(
        #         handle, "STREAM_OUT{0}_BUFFER_U16".format(0),
        #         len(full_data[2**bit: 2**(bit + 1)]), full_data[2**bit: 2**(bit + 1)])

        #     while True:


    except ljm.LJMError:
        print("error'")

    reset_dac(handle)
    ljm.eStreamStop(handle)
    ljm.close(handle)


if __name__ == "__main__":
    handle = ljm.openS(deviceType="T7")

    test_stream_time(handle)