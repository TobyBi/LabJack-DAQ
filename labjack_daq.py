import numpy as np
import time
from random import randint
from labjack import ljm

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


class LabJackDaq:
    """Wrapper for LabJack LJM library, to execute read and write timings and data loading.

    Written for T-Series products such as the T4 and T7.

    The handle and ``Updater``, ``AsynchUpdater``, ``Intervaler``, and
    ``Streamer``.

    Parameters
    ----------
    device_type : str
        From LJM docs: A string containing the type of the device to be
        connected, optionally prepended by "LJM_dt". Possible values include
        "ANY", "T4", "T7", and "DIGIT".
    connection_type : str
        From LJM docs: A string containing the type of the connection desired,
        optionally prepended by "LJM_ct". Possible values include "ANY", "USB",
        "TCP", "ETHERNET", and "WIFI".
    identifier : str
        From LJM docs: A string identifying the device to be connected or
        "LJM_idANY"/"ANY". This can be a serial number, IP address, or device
        name. Device names may not contain periods.

    Notes
    -----
    Please refer to the following links for more details:
    https://labjack.com/support/datasheets/t-series
    https://labjack.com/support/datasheets/t-series/communication/modbus-map
    https://labjack.com/support/software/api/ljm
    """
    def __init__(
        self, device_type="ANY", connection_type="ANY", identifier="ANY"):
        """Init a LabJackControl object."""
        self.handle = ljm.openS(device_type, connection_type, identifier)
        print(
            "Device type: {0}, connection type: {1}, ID: {2}, IP: {3}, port: {4}, Max {5} MB per packet".format(
                *ljm.getHandleInfo(self.handle)
                )
            )
        # TODO: error handling

    def __enter__(self):
        self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is KeyboardInterrupt:
            # disable and stop stream-out
            try:
                self.stream_out.disable_stream_out()
                self.stream_out.stop_stream()
            except NameError:
                pass

            # clean interval
            try:
                ljm.cleanInterval(self.interval._interval_handle)
            except:
                pass

            return False

        return exc_type is None

    # def open(self, device_type="ANY", connection_type="ANY", identifier="ANY"):
    #     self.handle = ljm.openS(device_type, connection_type, identifier)
    #     print("Device type: {0}, connection type: {1}, ID: {2}, IP: {3}, port: {4}, Max {5} MB per packet".format(
    #         *ljm.getHandleInfo(self.handle)))
    #     self._open = True
    #     # error handling

    @classmethod
    def experiment(cls, exp_name: str):
        """Init a LabJack object and other components based on experiment name."""
        if exp_name == "reflow":
            lj = cls(device_type="T4")
            lj.add_asynch(exp_name)
        elif exp_name == "machine":
            lj = cls(device_type="T7")
            lj.add_asynch(exp_name)
            lj.add_update(
                write_names=["DAC0_BINARY", "DAC1_BINARY"],
                read_names=["DAC0", "DAC1"]
                )
            lj.add_stream_out(out_names=["DAC0", "DAC1"])
        else:
            raise ValueError("Please choose a valid experiment name.")
        return lj

    def close(self):
        """Close connection between host and LabJack."""
        try:
            ljm.close(self.handle)
        except ljm.LJMError as e:
            if e.errorString != "LJME_DEVICE_NOT_OPEN":
                raise ljm.LJMError("Cannot close LabJack - unsure why.")

    def add_update(self, write_names, read_names):
        """Add an ``Updater``, refer to the class for more info."""
        self.update = Updater(self.handle, write_names, read_names)

    def add_stream_out(self, out_names, in_names=None):
        """Add a ``Streamer``, refer to the class for more info."""
        self.stream_out = Streamer.init_reset(
            self.handle, out_names, in_names=in_names
            )

    def add_asynch(self, exp_name: str):
        """Add a ``AsynchUpdater``, refer to the class for more info."""
        self.asynch = AsynchUpdater.experiment(self.handle, exp_name=exp_name)

    def add_interval(self, interval_time: float, num_iter: int):
        """Add a ``Intervaler``, refer to the class for more info."""
        self.interval = Intervaler(interval_time, num_iter)


class Updater:
    """LabJack reader and writer to registers.

    Read and write registers can be the same or different.

    Parameters
    ----------
    handle : int
        Labjack handle.
    write_names : list, tuple, or str
        Write register names.
    read_names : list, tuple or str
        Read register names.

    """

    def __init__(self, handle: int, write_names, read_names):
        """Inits an Updater object."""
        self._handle = handle

        self.write_names = convert_input(write_names)
        self.read_names = convert_input(read_names)

    @classmethod
    def same_registers(cls, handle: int, reg_names):
        """Inits an Updater object with the same read and write registers."""
        return cls(handle, reg_names, reg_names)

    @property
    def same_registers(self) -> bool:
        """Checks if the read and write registers are the same."""
        same = set(self.write_names) == set(self.read_names)
        return same

    def read(self) -> dict:
        """Read from Labjack registers.

        Returns
        -------
        read_dict : dict
            Dict in the format ``{register_name : data}``.
        """
        read_data = ljm.eReadNames(
            self._handle, len(self.read_names), self.read_names
            )
        read_dict = {
            name: data for name, data in zip(self.read_names, read_data)
            }
        return read_dict

    def write(self, datas):
        """Write to Labjack registers with input data.

        Parameters
        ----------
        datas : tuple, list or anything
        """
        # Single-valued data is converted into a list
        iter_datas = convert_input(datas)

        if len(iter_datas) != len(self.write_names):
            raise ValueError

        ljm.eWriteNames(
            self._handle, len(self.write_names), self.write_names, iter_datas
            )

    def update(self, datas) -> dict:
        """Write to and read from Labjack.

        If read and write registers are different then reads from
        object-defined read registers.

        Parameters
        ----------
        datas : tuple, list or anything
            Input data.

        Returns
        -------
        read_dict : dict
            See ``Updater.read``.

        Raises
        ------
        ValueError
            Length of data to write doesn't match number of write registers.
        """
        # ljm.eReadNames only works with list/tuple names so must be converted
        iter_datas = convert_input(datas)

        if len(iter_datas) != len(self.write_names):
            raise ValueError(
                "Length of data to write doesn't match number of write registers"
                )

        ljm.eWriteNames(
            self._handle, len(self.write_names), self.write_names, iter_datas
            )

        if self.same_registers:
            # Read the same registers after writing to them.
            read_data = ljm.eReadNames(
                self._handle, len(self.write_names), self.write_names
                )
            read_dict = {
                name: data for name, data in zip(self.write_names, read_data)
                }
        else:
            read_dict = self.read()

        return read_dict


class AsynchUpdater:
    """LabJack universial asynchronous receiver-transmitter (UART) serial communication.

    If asynchronous communication is used with the same AsynchUpdater object,
    then also ensures a 50ms delay between each receive or transmit action.

    Parameters
    ----------
    handle : int
        LabJack handle.

    Raises
    ------
    ValueError
        Must be either "microdisk_reflow" or "microrod_machine", to set which
        registers are used for asynchronous communication.

    Notes
    -----
    LabJack T4/T7 UART serial communication has the same timing and protocol as
    RS-232, however, the electrical specifications are different.
    T4/T7:
        low = 0V (0-0.5)
        high = 3.3V (2.64-5.8)
    RS-232:
        low = 3-25V
        high = -3-25V
    Connection using RS-232 requires a converter chip such as MAX233.

    For more details on UART serial communication on a LabJack, please visit:
    https://labjack.com/support/datasheets/t-series/digital-io/asynchronous-serial
    """
    min_time_interval = 50e3
    """Time interval between sending commands to allow command to be received.
    Unit in μs should be 50ms"""

    def __init__(self, handle: int):
        """Inits an AsynchUpdater object."""
        self._handle = handle
        self._last_host_tick = ljm.getHostTick()

        # if experiment in ASYNCH_CONFIG_REGISTERS.keys():
        #     self.experiment = experiment
        # else:
        #     raise ValueError("Experiment '{0}' doesn't exist! Please choose '{1}' or '{2}'".format(experiment, *ASYNCH_CONFIG_REGISTERS.keys()))

    @property
    def _asynch_enabled(self) -> bool:
        """Return if asynch communications is enabled."""
        enabled = bool(ljm.eReadName(self._handle, "ASYNCH_ENABLE"))
        return enabled

    @classmethod
    def experiment(cls, handle: int, exp_name: str):
        """Inits an AsynchUpdater object and Asynch communication based on experiment.

        Raises
        ------
        ValueError
            Must be either "reflow" or "machine", to set which registers are
            used for Asynch communication.
        """
        au = cls(handle)
        if exp_name == "reflow":
            reflow_asynch_conf = {
                "tx":               5,
                "rx":               4,
                "baud":             9600,
                "rx_buffer":        6,
                "num_data_bits":    0,
                "num_stop_bits":    1,
                "parity":           0
            }
            au.init_asynch(**reflow_asynch_conf)
        elif exp_name == "machining":
            machine_asynch_conf = {
                "tx":               1,
                "rx":               0,
                "baud":             9600,
                "rx_buffer":        6,
                "num_data_bits":    0,
                "num_stop_bits":    1,
                "parity":           0
            }
            au.init_asynch(**machine_asynch_conf)
        else:
            raise ValueError("Experiment '{0}' doesn't exist!")
        return au

    @classmethod
    def with_configuration(cls, handle: int, **kwargs):
        """Inits an AsynchUpdater object and Asynch communication configuration.

        Raises
        ------
        TypeError
            Configuration registers are not valid LabJack registers.
        """
        au = cls(handle)
        try:
            au.init_asynch(**kwargs)
        except TypeError:
            raise TypeError(
                "Please enter valid Asynch configuration register names."
                )
        return au

    def _check_interval(self):
        """Check interval time between two asynch actions is greater than 50ms."""
        # TODO: needs sleep here?
        if (ljm.getHostTick() - self._last_host_tick) < self.min_time_interval:
            time.sleep(self.min_time_interval/1e6)

    def init_asynch(
        self, tx: int=0, rx: int=0, baud: int=0, rx_buffer: int=0,
        num_data_bits: int=0, num_stop_bits: int=0, parity: int=0
        ):
        """Configure LabJack for Asynch communication.

        After configuring each LabJack register, ASYNCH_ENABLE is passed 1 to
        turn on Asynch communication.

        Parameters
        ----------
        tx : int, optional
            ASYNCH_TX_DIONUM, digital I/O line that transmits data, by default 0.
        rx : int, optional
            ASYNCH_RX_DIONUM, digital I/O line that receives data, by default 0.
        baud : int, optional
            ASYNCH_BAUD, symbol rate for communication, by default 0. Typical
            values are 9600 and 38600 is the maximum.
        rx_buffer : int, optional
            ASYNCH_RX_BUFFER_SIZE_BYTES, number of bytes of receiving buffer,
            by default 0. Max is 2048 and 0 = 200.
        num_data_bits : [0, 1, 2, 3, 4, 5, 6, 7, 8], optional
            ASYNCH_NUM_DATA_BITS, number of bits per frame, by default 0. 0 = 8.
        num_stop_bits : [0, 1, 2], optional
            ASYNCH_NUM_STOP_BITS, number of stop bits, by default 0.
            0 = zero stop bits,
            1 = one stop bit,
            2 = two stop bits.
        parity : [0, 1, 2], optional
            ASYNCH_PARITY, by default 0.
            0 = none,
            1 = odd,
            2 = even.
        """

        if self._asynch_enabled:
            ljm.eWriteName(self._handle, "ASYNCH_ENABLE", 0)

        ljm.eWriteName(self._handle, "ASYNCH_TX_DIONUM", tx)
        ljm.eWriteName(self._handle, "ASYNCH_RX_DIONUM", rx)
        ljm.eWriteName(self._handle, "ASYNCH_BAUD", baud)
        ljm.eWriteName(self._handle, "ASYNCH_RX_BUFFER_SIZE_BYTES", rx_buffer)
        ljm.eWriteName(self._handle, "ASYNCH_NUM_DATA_BITS", num_data_bits)
        ljm.eWriteName(self._handle, "ASYNCH_NUM_STOP_BITS", num_stop_bits)
        ljm.eWriteName(self._handle, "ASYNCH_PARITY", parity)
        # Turn on Asynch communication
        ljm.eWriteName(self._handle, "ASYNCH_ENABLE", 1)

        # reg_names = [key for key in ASYNCH_CONFIG_REGISTERS[self.experiment].keys()]
        # reg_datas = [val for val in ASYNCH_CONFIG_REGISTERS[self.experiment].values()]
        # ljm.eWriteNames(self._handle, len(reg_names), reg_names, reg_datas)

        print("Initialisation of Asynch comms. successful!")

    def transmit(self, data: list):
        """Asynchronously transmit serial data to device via LabJack TX line.

        Parameters
        ----------
        data : list
            List containing serial frame message.

        TODO: check if tuple, list works - then can use same function from
        Updater
        """
        self._check_interval()
        ljm.eWriteName(self._handle, "ASYNCH_NUM_BYTES_TX", len(data))
        ljm.eWriteNameArray(self._handle, "ASYNCH_DATA_TX", len(data), data)
        # Initiate a transmission via the buffer
        ljm.eWriteName(self._handle, "ASYNCH_TX_GO", 1)

        self._last_host_tick = ljm.getHostTick()

    def receive(self) -> list:
        """Asynchronously receive serial data from device via LabJack RX line.

        Returns
        -------
        asynch_rx_vals : list
            Asynch response from device via LabJack RX line.
        """
        self._check_interval()
        num_rx_vals = int(ljm.eReadName(self._handle, "ASYNCH_NUM_BYTES_RX"))
        asynch_rx_vals = ljm.eReadNameArray(
            self._handle, "ASYNCH_DATA_RX", num_rx_vals
            )
        self._last_host_tick = ljm.getHostTick()
        return asynch_rx_vals


class Intervaler:
    """Sets up a timed interval loop using a LabJack.

    A timed interval loop ensures that operations within the loop (before
    ljm.waitForNextInterval) occurs within the specified interval time. If it
    cannot, then it tries to perform the operations in the next interval and
    skipped intervals are reported.

    Parameters
    ----------
    interval_time : float
        Time of each iteration of the interval in μs.
    num_iter : int
        Number of iterations.

    Notes
    -----
    For more details about timing, refer to:
    https://labjack.com/support/software/api/ljm/function-reference/timing-functions/ljmstartinterval

    TODO: LUA scripting instead
    """

    def __init__(self, interval_time: float, num_iter: int):
        """Inits an Intervaler object."""
        # each interval has its own handle as well
        self._interval_handle = randint(1, 999)
        self.interval_time = interval_time
        self.num_iter = num_iter

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        ljm.cleanInterval(self._interval_handle)
        if exc_type is KeyboardInterrupt:
            print("Interval stopped by user.")
            return False

        return exc_type is None

    @staticmethod
    def _add_responses(resp_list: list, resp) -> list:
        """Either add or concatenate responses."""
        if isinstance(resp, list):
            resp_list += resp
        elif resp != "":
            resp_list.append(resp)
        return resp_list

    def start_interval(
        self, operations_inside, operations_outside=None,
        **operation_kwargs) -> dict:
        """Start a timed interval with operations inside and outside an interval.

        Functions operations_inside and operations_outside must accept as
        arguments:
            - curr_iter as an argument,
            - all of the optional operation_kwargs
        and must return
            - curr_iter as an argument (curr_iter must be incremented within
            operations_inside otherwise an infinite loop will occur
            - any read data (can be an empty string).

        Parameters
        ----------
        operations_inside : function
            Functions to execute inside a timed interval.
        operations_outside : function, optional
            Functions to execute outside a timed interval, right after the
            timed interval has finished, by default None.
        operation_kwargs : optional
            Keyword arguments for operations_inside or operations_outside,
            if requried.

        Returns
        -------
        response : dict
            Contains metrics on interval_time, total_time (total run time) and
            any responses from the LabJack.
        """
        curr_iter = 0
        all_interval_t = []
        interval_responses = []
        ljm.startInterval(self._interval_handle, self.interval_time)
        t_before_loop = ljm.getHostTick()

        while curr_iter < self.num_iter:
            t_start_interval = ljm.getHostTick()
            # run the operation inside a loop, allowing operation to
            # change iteration number
            curr_iter, resp = operations_inside(
                curr_iter, **operation_kwargs
                )
            skipped = ljm.waitForNextInterval(self._interval_handle)
            t_end_interval = ljm.getHostTick()

            interval_responses = self._add_responses(
                interval_responses, resp
                )
            all_interval_t.append(t_end_interval - t_start_interval)

            if operations_outside != None:
                # operations outside of the timed loop, called
                # *immediately* after the timed interval has ended
                dummy_iter, resp = operations_outside(
                    curr_iter, **operation_kwargs
                    )

                interval_responses = self._add_responses(
                    interval_responses, resp
                    )

            if skipped > 0:
                print("Iteration {0} skipped intervals: {1}".format(
                    curr_iter, skipped
                    ))

        total_time = ljm.getHostTick() - t_before_loop
        ljm.cleanInterval(self._interval_handle)

        response = {
            "interval_time": np.mean(all_interval_t),
            "total_time": total_time,
            "response": interval_responses
        }

        return response

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
