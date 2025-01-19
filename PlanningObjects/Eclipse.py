from typing import List, Dict
from PlanningObjects.Schedule import Schedule

class Eclipse:
    """
    A class to represent an eclipse during which certain targets are available for observation.

    Attributes
    ----------
    eclipse_number : int
        The unique identifier or number of the eclipse.
    targets_available : dict
        A dictionary mapping target IDs or names to some status or availability.
    targets_names : list of str
        A list of names of the available targets during the eclipse.
    targets_exp_times : list of int
        A list of exposure times (in seconds) for each target during the eclipse.
    schedule_indices : list of int
        A list of indices representing the time slots during which the eclipse occurs.
    operations : Schedule
        A schedule object representing the operations during the eclipse.
    """
    
    def __init__(self,
                 eclipse_number: int,
                 targets_available: Dict[str, bool],
                 targets_names: List[str],
                 targets_exp_times: List[int],
                 schedule_indices: List[int],
                 operations: 'Schedule'):
        """
        Initialize a new Eclipse object.
        
        Parameters
        ----------
        eclipse_number : int
            The unique identifier or number of the eclipse.
        targets_available : dict
            A dictionary mapping target IDs or names to their availability status.
        targets_names : list of str
            A list of names of the available targets during the eclipse.
        targets_exp_times : list of int
            A list of exposure times (in seconds) for each target during the eclipse.
        schedule_indices : list of int
            A list of indices representing the time slots during which the eclipse occurs.
        operations : Schedule
            A schedule object representing the operations during the eclipse.
        """
        self.eclipse_number = eclipse_number
        self.targets_available = targets_available
        self.targets_names = targets_names
        self.targets_exp_times = targets_exp_times
        self.schedule_indices = schedule_indices
        self.operations = operations
