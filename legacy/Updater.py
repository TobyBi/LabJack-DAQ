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
