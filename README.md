# LabJack-DAQ

Object-oriented wrapper of LabJack LJM  to control LabJack [T-Series DAQs](https://labjack.com/products/t7). Classes are provided for timed interval control, asynchronous communication, and output steaming of DACs.



## Requirements

- Python >= 3.8.5
- numpy >= 1.19.5
- [LabJack LJM library](https://labjack.com/support/software/installers/ljm)

Only written and tested with LabJack T7 DAQ.



## Installation

To install simply clone the git directory using the following commands:

```bash
git clone https://github.com/TobyBi/LabJack-DAQ
```

Move `tdaq.py` to your own directory and import it to use.



## Usage

Create a `LabJackDaq` object and add desired components to use it. The available components are

- `Updater` for reading and writing to LabJack registers,
- `AsynchUpdater` for using asynchronous read and write to LabJack registers,
- `Intervaler` which allows ensures commands run within a certain interval, and
- `Streamer` which streams data from the LabJack at a set rate.



More details are included in the documentation [here](https://tobybi.github.io/LabJack-DAQ/tdaq.html).