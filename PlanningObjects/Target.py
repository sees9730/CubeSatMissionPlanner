from typing import Type
from PlanningObjects.Schedule import Schedule

from skyfield.api import Topos
import matplotlib.pyplot as plt

# Assuming the Schedule class is defined somewhere in your project
# from your_module import Schedule

class Target:
    """
    A class to represent a target in a science mission.
    
    Attributes
    ----------
    name : str
        The name of the target.
    skyfield_object : Topos
        A SkyField object representing the celestial object for the target.
    rotation_angle : float
        The rotation angle of the target (in degrees or radians).
    priority : int
        The priority level of the target.
    current_exp_time : float
        The current exposure time allocated to this target (in seconds).
    visibility : Schedule
        A schedule object representing the visibility of the target over time.
    """
    
    def __init__(self,
                 name: str,
                 skyfield_object: 'Topos',
                 rotation_angle: float,
                 base_priority: int,
                 current_exp_time: float,
                 schedule: 'Schedule',
                 target_altitude: list[float],
                 moon_separation: list[float] = None,
                 max_exp_time: float = None):
        """
        Initialize a new Target object.

        Parameters
        ----------
        name : str
            The name of the target.
        skyfield_object : Topos
            A SkyField object representing the celestial object for the target.
        rotation_angle : float
            The rotation angle of the target (in degrees or radians).
        priority : int
            The priority level of the target.
        current_exp_time : float
            The current exposure time allocated to this target (in seconds).
        visibility : Schedule
            A schedule object representing the visibility of the target over time.
        """
        self.name = name
        self.skyfield_object = skyfield_object
        self.rotation_angle = rotation_angle
        self.eclipse_priority = base_priority
        self.base_priority = base_priority
        self.current_exp_time = current_exp_time
        self.schedule = schedule
        self.target_altitude = target_altitude
        self.moon_separation = moon_separation
        self.max_exp_time = max_exp_time
