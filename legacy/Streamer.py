import time
from labjack import ljm
import numpy as np

def convert_input(val):
    """Convert single length input to iterable (``list`` or ``tuple``).

    Parameters
    ----------
    val : any type
        Can be ``list``, ``tuple``, ``numpy.ndarray`` or any type.

    Returns
    -------
    iter_val : ``list`` or ``tuple``
        Iterable output.
    """
    if not isinstance(val, tuple) and not isinstance(val, list):
        if isinstance(val, np.ndarray):
            # np.ndarray can only be converted to list this way
            iter_val = list(val)
        else:
            # any other variable needs this way
            iter_val = [val]
    else:
        iter_val = val
    return iter_val

class Streamer:
    """Streaming data from buffer to output mode via the LabJack.

    Parameters
    ----------
    handle : int
        LabJack handle.
    out_names : any
        List of register names for stream-out.
    in_names : any, optional
        NotImplemented, by default None

    Notes
    -----
    Please refer to the following links for further details on the registers:
    https://labjack.com/support/datasheets/t-series/communication/stream-mode/stream-out
    https://labjack.com/support/datasheets/t-series/communication/stream-mode/stream-out/stream-out-description
    """

    def __init__(self, handle: int, out_names, in_names=None):
        """Inits a Streamer object."""
        self._handle = handle

        self.out_names = convert_input(out_names)
        self.in_names = in_names    # Not yet implemented

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.disable_stream_out()
        self.stop_stream()

        if exc_type is KeyboardInterrupt:
            print("Streaming stopped by user.")
            return False

        return exc_type is None

    @classmethod
    def init_reset(cls, handle: int, out_names, in_names=None):
        """Inits and resets a Streamer object."""
        s = cls(handle, out_names, in_names)
        s.reset_stream()
        return s

    @property
    def out_addresses(self) -> list:
        """Return a list of addresses for stream-out targets."""
        out_address = [
            ljm.nameToAddress(out_name)[0] for out_name in self.out_names]
        return out_address

    @property
    def stream_nums(self) -> list:
        """Return a list of numbers corresponding to stream-out targets."""
        nums = ["{0}".format(no) for no in range(len(self.out_names))]
        return nums

    @property
    def scan_list(self) -> list:
        """Return a list of stream-out targets for a single scan."""
        scan_list = [
            ljm.nameToAddress("STREAM_OUT{0}".format(num))[0]
            for num in self.stream_nums
            ]
        return scan_list

    def reset_stream(self):
        """Reset stream configurations for purely stream-out.

        Notes
        -----
        Please refer to the following links for more information on the default
        configurations:
        https://labjack.com/support/datasheets/t-series/communication/stream-mode#ain-stream
        https://labjack.com/support/datasheets/t-series/communication/stream-mode#externally-clocked
        https://labjack.com/support/datasheets/t-series/communication/stream-mode#triggered

        TODO: non-default configurations
        """
        ljm.eWriteName(self._handle, "STREAM_SETTLING_US", 0)
        ljm.eWriteName(self._handle, "STREAM_RESOLUTION_INDEX", 0)
        ljm.eWriteName(self._handle, "STREAM_CLOCK_SOURCE", 0)
        ljm.eWriteName(self._handle, "STREAM_TRIGGER_INDEX", 0)

    def configure_stream(self, loop_num_vals: int=0):
        """Configure stream-out buffer size and target and update buffer.

        What is changed?
            - setting the buffer size which must be a power of 2, max is 14 bits,
            - adding the out addresses to stream-out targets,
            - enabling a stream target so that for every scan a data value is
            taken from the available stream targets,
            - number of values from the end of the data array to repeat when
            reaching the end of the loop,
            - telling stream-out to immediate use new data loaded in

        Parameters
        ----------
        loop_num_vals : int, optional
            The number of values, from the end of the array to loop, by
            default 0.

        Notes
        -----
        Section 2 and 3 on LabJack T-series datasheets.
        """
        for stream_num, out_address in zip(self.stream_nums, self.out_addresses):
            ljm.eWriteName(
                self._handle,
                "STREAM_OUT{0}_BUFFER_ALLOCATE_NUM_BYTES".format(
                    stream_num), 2**14
                )
            ljm.eWriteName(
                self._handle,
                "STREAM_OUT{0}_TARGET".format(stream_num), out_address
                )
            ljm.eWriteName(
                self._handle, "STREAM_OUT{0}_ENABLE".format(stream_num), 1
                )
            # Update Buffer
            ljm.eWriteName(
                self._handle,
                "STREAM_OUT{0}_LOOP_SIZE".format(stream_num), loop_num_vals
                )
            # This register is an alias for STREAM_OUT{0}_LOOP_NUM_VALUES
            ljm.eWriteName(
                self._handle, "STREAM_OUT{0}_SET_LOOP".format(stream_num), 1
                )

    def load_data(self, datas: tuple, buffer_type: str):
        """Load data array into stream-out buffer registers.

        Expecting input datas to be tuple of list or a list for a single stream out target

        Parameters
        ----------
        datas : tuple
        buffer_type : str
            Chooses whether integer or floating point data is loaded onto buffer

        Raises
        ------
        ValueError
            Invalid buffer type
        """
        if isinstance(datas, tuple):
            for d in datas:
                if (
                    not isinstance(d, tuple) or
                    not isinstance(d, list) or
                    not isinstance(d, np.ndarray)):
                    raise TypeError(
                        "Input data must be a tuple containing lists."
                        )

        if buffer_type == "int":
            buffer_name = "STREAM_OUT{0}_BUFFER_U16"
        elif buffer_type == "float":
            buffer_name = "STREAM_OUT{0}_BUFFER_F32"
        else:
            raise ValueError(
                "Buffer type '{0}' is invalid - choose either 'int' or 'float'".format(
                    buffer_type
                    )
                )

        self._data_lengths = []

        for stream_num, data in zip(self.stream_nums, datas):
            ljm.eWriteNameArray(
                self._handle, buffer_name.format(stream_num), len(data), data)
            self._data_lengths.append(len(data))

    def start_stream(self, stream_time: float, scans_per_read: int=1) -> float:
        """Stream-out loaded data to scan list at a given scan frequency.

        Parameters
        ----------
        stream_time : float
            Total time (in s) the stream will run for, converted into scan
            rate (Hz).
        scans_per_read : int, optional
            Number of times the stream targets or scan list is scanned per
            iteration, by default 1.

        Returns
        -------
        actual_time : float
            Actual time the stream ran for which is 1.02x more than the
            predicted stream-out time.

        Raises
        ------
        ValueError
            No data loaded into Streamer, only needs to be loaded in once.
        KeyboardInterrupt
            Streaming stopped by user
        """
        try:
            # determine scan rate based on loaded in data
            scan_rate = max(self._data_lengths) / stream_time
        except:
            raise ValueError("Load some data in!")

        # stream actually starts here by setting STREAM_ENABLE=1 but doesn't
        # block execution
        actual_scan_rate = ljm.eStreamStart(
            self._handle, scans_per_read,
            len(self.scan_list), self.scan_list, scan_rate
            )
        # the sleep here is what blocks execution
        # sleeping for 2% more time than stream out time just incase
        actual_time = 1.02*(max(self._data_lengths) / actual_scan_rate)
        time.sleep(actual_time)

        return actual_time


    # def start_stream(self, stream_time: float, scans_per_read: int=1) -> float:
    #     """Stream-out loaded data to scan list at a given scan frequency.

    #     Parameters
    #     ----------
    #     stream_time : float
    #         Total time (in s) the stream will run for, converted into scan
    #         rate (Hz).
    #     scans_per_read : int, optional
    #         Number of times the stream targets or scan list is scanned per
    #         iteration, by default 1.

    #     Returns
    #     -------
    #     actual_time : float
    #         Actual time the stream ran for which is 1.02x more than the
    #         predicted stream-out time.

    #     Raises
    #     ------
    #     ValueError
    #         No data loaded into Streamer, only needs to be loaded in once.
    #     KeyboardInterrupt
    #         Streaming stopped by user
    #     """
    #     try:
    #         # determine scan rate based on loaded in data
    #         scan_rate = max(self._data_lengths) / stream_time
    #     except:
    #         raise ValueError("Load some data in!")

    #     try:
    #         # stream actually starts here by setting STREAM_ENABLE=1 but doesn't block execution
    #         actual_scan_rate = ljm.eStreamStart(
    #             self._handle, scans_per_read,
    #             len(self.scan_list), self.scan_list, scan_rate
    #             )
    #         actual_time = 1.02*(max(self._data_lengths) / actual_scan_rate)
    #         # the sleep here is what blocks execution
    #         # sleeping for 2% more time than stream out time just incase
    #         time.sleep(actual_time)
    #     except KeyboardInterrupt:
    #         # using set scan rates and times if stopped before initialising the parameters
    #         try:
    #             actual_scan_rate
    #         except NameError:
    #             actual_scan_rate = scan_rate
    #         try:
    #             actual_time
    #         except NameError:
    #             actual_time = stream_time

    #         raise KeyboardInterrupt("Streaming stopped by user!")
    #     finally:
    #         self.disable_stream_out()
    #         self.stop_stream()

    #     return actual_time

    def disable_stream_out(self):
        """Disable stream-out."""
        for stream_num in self.stream_nums:
            ljm.eWriteName(
                self._handle, "STREAM_OUT{0}_ENABLE".format(stream_num), 0
                )

    def stop_stream(self):
        """Stop a running stream-out."""
        try:
            ljm.eStreamStop(self._handle)
        except ljm.LJMError as e:
            if e.errorString != "STREAM_NOT_RUNNING":
                raise ljm.LJMError("Cannot stop stream - unsure why.")
