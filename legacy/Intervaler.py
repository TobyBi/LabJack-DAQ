import numpy as np
from random import randint
from labjack import ljm

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
        self, operations_inside: function, operations_outside: function=None,
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

    # def start_interval(
    #     self, operations_inside: function, operations_outside: function=None,
    #     **operation_kwargs) -> dict:
    #     """
    #     Start the timed interval with operations inside and outside an interval.
    #     Any functions; operations_inside and operations_outside must accept
    #     - curr_iter as an argument
    #     - all of the optional operation_kwargs
    #     and must return
    #     - curr_iter as an argument, the curr_iter must be incremented within the operations_inside
    #     otherwise an infinite loop may occur
    #     - any read data, can be an empty string

    #     Parameters
    #     ----------
    #     operations_inside : func
    #         Functions to execute inside a timed interval
    #     operations_outside : func, optional
    #         Functions to execute outside the timed interval, right after the timed interval has finished,
    #         by default None
    #     operation_kwargs : optional
    #         Keyworded arguments for operations_inside or operations_outside, if requried

    #     Returns
    #     -------
    #     dict
    #         Dictionary containing interval metrics;
    #         - interval_time; interval time
    #         - total_time; total run time (interval_time * num_iter)
    #         - response; any responses from the Labjack if there any reading occurred in the interval

    #     Raises
    #     ------
    #     KeyboardInterrupt
    #         Interval has been stopped by user
    #     """
    #     curr_iter = 0
    #     all_interval_t = []
    #     interval_responses = []
    #     ljm.startInterval(self._interval_handle, self.interval_time)
    #     t_before_loop = ljm.getHostTick()

    #     try:
    #         while curr_iter < self.num_iter:
    #             t_start_interval = ljm.getHostTick()
    #             # run the operation inside a loop, allowing operation to
    #             # change iteration number
    #             curr_iter, resp = operations_inside(
    #                 curr_iter, **operation_kwargs
    #                 )
    #             skipped = ljm.waitForNextInterval(self._interval_handle)
    #             t_end_interval = ljm.getHostTick()

    #             interval_responses = self._add_responses(
    #                 interval_responses, resp
    #                 )
    #             all_interval_t.append(t_end_interval - t_start_interval)

    #             if operations_outside != None:
    #                 # operations outside of the timed loop, called
    #                 # *immediately* after the timed interval has ended
    #                 dummy_iter, resp = operations_outside(
    #                     curr_iter, **operation_kwargs
    #                     )

    #                 interval_responses = self._add_responses(
    #                     interval_responses, resp
    #                     )

    #             if skipped > 0:
    #                 print("Iteration {0} skipped intervals: {1}".format(
    #                     curr_iter, skipped
    #                     ))
    #     except KeyboardInterrupt:
    #         if not all_interval_t:
    #             all_interval_t.append(0)
    #         # KeyboardInterrupt is raised and sent to the laser for nicely
    #         # exiting the UC2000Controller
    #         raise KeyboardInterrupt("Interval stopped by user")
    #     finally:
    #         total_time = ljm.getHostTick() - t_before_loop
    #         ljm.cleanInterval(self._interval_handle)

    #         response = {
    #             "interval_time": np.mean(all_interval_t),
    #             "total_time": total_time,
    #             "response": interval_responses
    #         }

    #     return response
