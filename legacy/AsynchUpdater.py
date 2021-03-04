import time
from labjack import ljm

MIN_TIME_INTERVAL = 50e3 # in microseconds should be 50ms

ASYNCH_CONFIG_REGISTERS = {
    "microdisk_reflow" : {
        "ASYNCH_TX_DIONUM": 5,
        "ASYNCH_RX_DIONUM": 4,
        "ASYNCH_BAUD": 9600,
        "ASYNCH_RX_BUFFER_SIZE_BYTES": 6,
        "ASYNCH_NUM_DATA_BITS": 0,          # 0 = 8 bits
        "ASYNCH_NUM_STOP_BITS": 1,
        "ASYNCH_PARITY": 0,
        "ASYNCH_ENABLE": 1
    },
    "microrod_machine": {
        "ASYNCH_TX_DIONUM": 1,
        "ASYNCH_RX_DIONUM": 0,
        "ASYNCH_BAUD": 9600,
        "ASYNCH_RX_BUFFER_SIZE_BYTES": 6,
        "ASYNCH_NUM_DATA_BITS": 0,          # 0 = 8 bits
        "ASYNCH_NUM_STOP_BITS": 1,
        "ASYNCH_PARITY": 0,
        "ASYNCH_ENABLE": 1
    }
}

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
