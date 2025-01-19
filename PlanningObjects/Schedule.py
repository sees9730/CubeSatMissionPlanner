from datetime import datetime
from typing import List, Dict

class Schedule:
    """
    A class to represent a schedule over time, tracking status changes at specific time points.
    
    Attributes
    ----------
    start_time : datetime
        The start time of the schedule.
    end_time : datetime
        The end time of the schedule.
    time_step_sec : float
        The time step between each time point in the schedule (in seconds).
    time : list of float
        A list of time points (in seconds) from the start time.
    status : list of int
        A list of status codes corresponding to the time points.
    status_enum : dict
        A dictionary mapping status codes to their respective meanings (e.g., {0: 'Inactive', 1: 'Active'}).
    """
    
    def __init__(self,
                 name: str,
                 start_time: datetime,
                 end_time: datetime,
                 time_step_sec: float,
                 time: List[float],
                 status: List[int],
                 status_enum: Dict[int, str]):
        """
        Initialize a new Schedule object.
        
        Parameters
        ----------
        start_time : datetime
            The start time of the schedule.
        end_time : datetime
            The end time of the schedule.
        time_step_sec : float
            The time step between each time point in the schedule (in seconds).
        time : list of float
            A list of time points (in seconds) from the start time.
        status : list of int
            A list of status codes corresponding to the time points.
        status_enum : dict
            A dictionary mapping status codes to their respective meanings.
        """
        self.name = name
        self.start_time = start_time
        self.end_time = end_time
        self.time_step_sec = time_step_sec
        self.time = time
        self.status = status
        self.status_enum = status_enum