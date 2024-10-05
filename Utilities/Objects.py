# Typing imports
from typing import List, Type, Dict
from datetime import datetime
# General imports
import pandas as pd
import numpy as np

# Plotting imports
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

class ScienceMission:
    """
    A class to represent the scientific mission details.
    
    Attributes
    ----------
    master_target_list : list[Target]
        A list of target objects for the science mission.
    eclipses : list[Eclipse]
        A list of eclipse periods affecting the mission.
    surveys : list[Survey]
        A list of surveys associated with the mission.
    """

    def __init__(self,
                 master_target_list: List['Target'],
                 eclipses: List['Eclipse'],
                 surveys: List['Survey']):
        """
        Initialize a new ScienceMission object.
        
        Parameters
        ----------
        master_target_list : list[Target]
            A list of target objects for the science mission.
        eclipses : list[Eclipse]
            A list of eclipse periods affecting the mission.
        surveys : list[Survey]
            A list of surveys associated with the mission.
        """
        self.master_target_list = master_target_list
        self.eclipses = eclipses
        self.surveys = surveys

    def __repr__(self) -> str:
        """
        Provide a string representation of the ScienceMission.
        
        Returns
        -------
        str
            A string representation of the ScienceMission object.
        """
        return (f"ScienceMission(master_target_list={len(self.master_target_list)} targets, "
                f"eclipses={len(self.eclipses)} eclipses, "
                f"surveys={len(self.surveys)} surveys)")

class Target:
    """
    A class to represent a target in a science mission.
    
    Attributes
    ----------
    name : str
        The name of the target.
    skyfield_object : SkyField
        A SkyField object representing the celestial object for the target.
    rotation_angle : float
        The rotation angle of the target.
    priority : int
        The priority level of the target.
    current_exp_time : float
        The current exposure time allocated to this target.
    visibility : Schedule
        The visibility schedule for the target.
    """

    def __init__(self,
                 name: str,
                 skyfield_object: 'Star',
                 rotation_angle: float,
                 priority: int,
                 current_exp_time: float,
                 visibility: 'Schedule'):
        """
        Initialize a new Target object.
        
        Parameters
        ----------
        name : str
            The name of the target.
        skyfield_object : SkyField
            A SkyField object representing the celestial object for the target.
        rotation_angle : float
            The rotation angle of the target.
        priority : int
            The priority level of the target.
        current_exp_time : float
            The current exposure time allocated to this target.
        visibility : Schedule
            The visibility schedule for the target.
        """
        self.name = name
        self.skyfield_object = skyfield_object
        self.rotation_angle = rotation_angle
        self.priority = priority
        self.current_exp_time = current_exp_time
        self.visibility = visibility

    def plotSchedule(self) -> None:
        """
        Plot the visibility schedule for the target.
        """
        return

    def __repr__(self) -> str:
        """
        Provide a string representation of the Target.
        
        Returns
        -------
        str
            A string representation of the Target object.
        """
        return (f"Target name = {self.name}, \n"
                f"Skyfield Object = {self.skyfield_object}, \n"
                f"Rotation Angle = {self.rotation_angle}, \n"
                f"Priority = {self.priority}, \n"
                f"Current exposure time = {self.current_exp_time}")

class Eclipse:
    """
    A class to represent an eclipse period in the science mission.

    Attributes
    ----------
    eclipse_number : int
        The identifier number of the eclipse.
    targets_available : dict
        A dictionary mapping target identifiers to their availability status.
    targets_names : list of str
        A list of the names of available targets during the eclipse.
    targets_exp_times : list of int
        A list of exposure times (in seconds or any relevant unit) for the targets.
    schedule_indices : list of int
        A list of indices that map the eclipse's operations to the schedule.
    operations : Schedule
        A schedule of operations during the eclipse period.
    """

    def __init__(self,
                 eclipse_number: int,
                 targets_available: Dict,
                 targets_names: List[str],
                 targets_exp_times: List[int],
                 schedule_indices: List[int],
                 operations: 'Schedule'):
        """
        Initialize a new Eclipse object.
        
        Parameters
        ----------
        eclipse_number : int
            The identifier number of the eclipse.
        targets_available : dict
            A dictionary mapping target identifiers to their availability status.
        targets_names : list of str
            A list of the names of available targets during the eclipse.
        targets_exp_times : list of int
            A list of exposure times (in seconds or any relevant unit) for the targets.
        schedule_indices : list of int
            A list of indices that map the eclipse's operations to the schedule.
        operations : Schedule
            A schedule of operations during the eclipse period.
        """
        self.eclipse_number = eclipse_number
        self.targets_available = targets_available
        self.targets_names = targets_names
        self.targets_exp_times = targets_exp_times
        self.schedule_indices = schedule_indices
        self.operations = operations

    def __repr__(self) -> str:
        """
        Provide a string representation of the Eclipse.
        
        Returns
        -------
        str
            A string representation of the Eclipse object.
        """
        return (f"Eclipse number = {self.eclipse_number}, \n"
                f"Targets available = {len(self.targets_available)} targets, \n"
                f"Targets names = {self.targets_names}, \n"
                f"Targets exposure times = {self.targets_exp_times}, \n"
                f"Schedule indices = {self.schedule_indices}, \n")

class Schedule:
    """
    A class to represent the schedule of operations within a time frame.
    
    Attributes
    ----------
    start_time : datetime
        The start time of the schedule.
    end_time : datetime
        The end time of the schedule.
    time_step_sec : float
        The time step in seconds between entries in the time list.
    time : list of float
        A list of times in seconds since the start_time.
    status : list of int
        A list of statuses represented as integers corresponding to the times.
    status_enum : dict
        A dictionary mapping status codes to their meanings.
    """
    
    def __init__(self,
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
            The time step in seconds between entries in the time list.
        time : list of float
            A list of times in seconds since the start_time.
        status : list of int
            A list of statuses represented as integers corresponding to the times.
        status_enum : dict
            A dictionary mapping status codes to their meanings.
        """
        self.start_time = start_time
        self.end_time = end_time
        self.time_step_sec = time_step_sec
        self.time = time
        self.status = status
        self.status_enum = status_enum

    def plotSchedule(self, plan, old_schedule: np.ndarray, new_schedule: np.ndarray, xlims: List[int] = [0, 400]):
        """
        Visualize the schedule before and after an update.

        Parameters
        ----------
        plan : object
            An object containing eclipse information and time schedules.
        old_schedule : np.ndarray
            Array representing the schedule before changes.
        new_schedule : np.ndarray
            Array representing the schedule after changes.
        xlims : list of int, optional
            Limits for the x-axis to zoom in on a specific portion of the time schedule (default is [0, 400]).
        dt : int, optional
            Time step for plotting (default is 6).
        
        Returns
        -------
        None
        """
        # Retrieve eclipse indices for visualization
        eclipse_indices = [eclipse.getEclipseIndices() for eclipse in plan.getEclipses()]
        t_ax = plan.getTimeSchedule()

        # Define schedules for before and after plots
        schedules = [(old_schedule, 'Schedule Before Pointing Allocation'),
                    (new_schedule, 'Schedule After Pointing Allocation')]

        fig, axes = plt.subplots(2, 1, figsize=(24, 6))

        # Loop over schedules to plot old and new schedule
        for i, (schedule, title) in enumerate(schedules):
            ax = axes[i]

            # Plot the schedule with step-like behavior
            ax.plot(t_ax, schedule, drawstyle='steps-mid', label=title)

            # Add eclipse periods as shaded regions
            for start_index, end_index in eclipse_indices:
                ax.axvspan(t_ax[start_index], t_ax[end_index], color='lightsteelblue', alpha=0.3)

            # Set y-ticks based on mission target
            mission_targets = plan.getMissionTargets()
            ax.set_yticks([targ.value for targ in mission_targets])
            ax.set_yticklabels([targ.name for targ in mission_targets])

            # Add markers for status transitions
            markers = ['s', 'd', 'o', '^', 'X', '*', 'D']
            for j, targ in enumerate(mission_targets):
                ax.plot(
                    t_ax[np.where(schedule == targ.value)],
                    schedule[np.where(schedule == targ.value)],
                    marker=markers[j % len(markers)],
                    linestyle='',
                    label=targ.name
                )

            ax.set_ylabel("Status", fontsize=25)
            ax.set_xlim([t_ax[xlims[0]], t_ax[xlims[1]]])
            ax.set_title(title, fontsize=30)
            ax.legend()
            ax.tick_params(labelsize=16)

        # Label x-axis for the second plot and format the time display
        axes[1].set_xlabel("Time in UTC", fontsize=25)
        x_fmt = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
        axes[1].xaxis.set_major_formatter(x_fmt)
        plt.xticks(rotation=45)

        fig.tight_layout()
        plt.grid()
        plt.show()

        return
