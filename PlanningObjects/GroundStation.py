from typing import Type
from PlanningObjects.Schedule import Schedule
from PlanningObjects.Satellite import Satellite

class GroundStation:
    """
    A class to represent a ground station, including its geographical location and visibility constraints.
    
    Attributes
    ----------
    name : str
        The name of the ground station.
    latitude : float
        The latitude of the ground station (in degrees).
    longitude : float
        The longitude of the ground station (in degrees).
    altitude : float
        The altitude of the ground station (in meters or kilometers).
    elevation_constraint : float
        The minimum elevation angle constraint for communication (in degrees).
    visibility : Schedule
        A schedule object representing the visibility of the ground station over time.
    """
    
    def __init__(self,
                 name: str,
                 latitude: float,
                 longitude: float,
                 altitude: float,
                 elevation_constraint: float,
                 satellite: Satellite):
        """
        Initialize a new GroundStation object.
        
        Parameters
        ----------
        name : str
            The name of the ground station.
        latitude : float
            The latitude of the ground station (in degrees).
        longitude : float
            The longitude of the ground station (in degrees).
        altitude : float
            The altitude of the ground station (in meters or kilometers).
        elevation_constraint : float
            The minimum elevation angle constraint for communication (in degrees).
        visibility : Schedule
            A schedule object representing the visibility of the ground station over time.
        """
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.elevation_constraint = elevation_constraint
        self.visibility = self._calculate_visibility(satellite)

    def _calculate_visibility(self, satellite: Satellite) -> Schedule:
        """
        Calculate the visibility of the ground station over time.

        Parameters
        ----------
        satellite : Satellite
            The satellite object.

        Returns
        -------
        Schedule
            The visibility schedule.
        """

        # Convert latitudes and longitudes to WGS84 geographic positions
        ground_station_object = satellite.earth_ephemeris + satellite.wgs84.latlon(self.latitude, self.longitude, self.altitude)
        satellite_object = satellite.earth_ephemeris + satellite.wgs84.latlon(satellite.latitudes, satellite.longitudes, satellite.altitudes)
        
        # Calculate the elevation angles
        apparent = ground_station_object.at(satellite.times).observe(satellite_object)
        elevation, _, _ = apparent.apparent().altaz()

        # Calculate the visibility schedule
        visibility_schedule = elevation.degrees > self.elevation_constraint

        # Create the visibility schedule
        return Schedule(
            name = "Ground Station Visibility",
            start_time = satellite.times[0],
            end_time = satellite.times[-1],
            time_step_sec = satellite.time_step_sec,
            time = satellite.times,
            status = visibility_schedule,
            status_enum = {True: "Visible", False: "Not Visible"})
            
        
