from datetime import datetime
import requests
import pandas as pd
import numpy as np
from skyfield.api import EarthSatellite, load, wgs84
import logging
from matplotlib.path import Path

class Satellite:
    # TODO: FIX THIS DESCRIPTION
    """
    A class to represent a satellite and its position data over time.
    
    Attributes
    ----------
    longitudes : list of float
        List of longitudes of the satellite's position.
    latitudes : list of float
        List of latitudes of the satellite's position.
    altitudes : list of float
        List of altitudes (in kilometers or relevant unit) of the satellite's position.
    times : list of float
        List of time points in seconds since start_time.
    tle_file : str
        The file containing TLE data.
    satellite_name : str
        The name of the satellite.
    start_time : datetime
        Start time of the data collection or observation period.
    end_time : datetime
        End time of the data collection or observation period.
    time_step_sec : int
        Time step between data points, in seconds.
    """

    def __init__(self,
                 tle_url: str,
                 tle_file: str,
                 satellite_name: str,
                 start_time: datetime,
                 end_time: datetime,
                 time_step_sec: int,
                 saa_latitudes_area: list,
                 saa_longitudes_area: list,
                 polar_constraint: int,
                 earth_constraint: int,
                 moon_constraint: int):
        """
        Initialize a new Satellite object.
        
        Parameters
        ----------
        tle_url : str
            The URL to fetch the TLE data from.
        tle_file : str
            The file path to store TLE data.
        satellite_name : str
            The name of the satellite.
        start_time : datetime
            The start time of the simulation.
        end_time : datetime
            The end time of the simulation.
        time_step_sec : int
            Time step for calculating satellite positions, in seconds.
        """
        self.tle_url = tle_url
        self.tle_file = tle_file
        self.satellite_name = satellite_name
        self.start_time = start_time
        self.end_time = end_time
        self.time_step_sec = time_step_sec
        self.latitudes = []
        self.longitudes = []
        self.altitudes = []
        self.times = []
        
        # Initialize the physical constraints
        self.saa_latitudes_area = saa_latitudes_area
        self.saa_longitudes_area = saa_longitudes_area
        self.polar_constraint = polar_constraint
        self.earth_constraint = earth_constraint
        self.moon_constraint = moon_constraint
        self.moon_altitudes = []
        
        # Initialize the WGS84 coordinate system
        self.wgs84 = wgs84
        
        # Load the DE421 ephemeris and get the Earth and Moon ephemeris
        self.ephemeris = load('de421.bsp')
        self.earth_ephemeris = self.ephemeris['earth']
        self.moon_ephemeris = self.ephemeris['moon']
        self.sun_ephemeris = self.ephemeris['sun']

        # Calculate the satellite's position over the specified time interval
        self.earth_satellite = self._create_earth_satellite()
        self._calculate_satellite_positions()

        # Calculate the SAA ground track for the specified time interval
        self._get_saa_groundtrack_coordinates()

    def _create_earth_satellite(self) -> EarthSatellite:
        """
        Create an EarthSatellite object from the skyfield library using the TLE lines.
        
        Returns
        -------
        EarthSatellite
            The EarthSatellite object created from the TLE data.
        """
        max_age_days = 10  # Maximum age of the TLE file before reloading

        # Check if the TLE file exists and is recent
        if not load.exists(self.tle_file) or load.days_old(self.tle_file) >= max_age_days:
            # Fetch and save new TLE data if the file is outdated or missing
            tle_lines = self.fetch_tle_data()
            if tle_lines:
                self.save_tle_data(tle_lines)
                logging.info(f"Loaded {self.satellite_name} TLE from URL.")
        else:
            logging.info(f"Loaded existing TLE data for {self.satellite_name}.")

        # Load and return the TLE data as an EarthSatellite object
        return load.tle_file(self.tle_file)[0]

    def fetch_tle_data(self) -> list:
        """
        Fetch and extract TLE data for the satellite from the specified URL.
        
        Returns
        -------
        list of str
            A list of TLE lines if found; otherwise, an empty list.
        """
        try:
            # Fetch TLE data from the specified URL
            response = requests.get(self.tle_url, timeout=10)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            # Extract the TLE lines for the satellite
            tle_data = response.text.splitlines()
            tle_lines = [tle_data[i:i+3] for i in range(0, len(tle_data), 3) 
                         if tle_data[i].strip() == self.satellite_name]

            if not tle_lines:
                raise ValueError(f"TLE data for {self.satellite_name} not found in the provided data.")

            return tle_lines[0]  # Return the first match of TLE lines

        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching TLE data: {e}")
        except ValueError as e:
            logging.error(e)

        return []  # Return an empty list if fetching fails or TLE is not found

    def save_tle_data(self, tle_lines: list) -> None:
        """
        Save TLE lines to a specified file.
        
        Parameters
        ----------
        tle_lines : list of str
            The lines of TLE data to be saved.
        """
        with open(self.tle_file, 'w') as f:
            f.write('\n'.join(tle_lines) + '\n')
        logging.info(f"TLE data saved to {self.tle_file}.")

    def _calculate_satellite_positions(self) -> None:
        """
        Calculate the positions of the specified satellite over the specified time interval.
        """
        # Load the timescale for generating time points
        ts = load.timescale()

        # Generate time array
        times = self._generate_times(ts)

        # Compute the satellite's geocentric positions at the specified times
        geocentric = self.earth_satellite.at(times)

        # Check if the first index has the spacecraft sunlit
        # charging_schedule = self.satellite.earth_satellite.at(self.satellite.times).is_sunlit(self.satellite.ephemeris)
        sunlit_schedule = self.earth_satellite.at(times).is_sunlit(self.ephemeris)

        print(f'First index: {sunlit_schedule[0]}')
        print(f'Last index: {sunlit_schedule[-1]}')

        # If the first index is not sunlit, then we need to adjust the times
        if not sunlit_schedule[0]:
            start_sunlit_index = np.where(sunlit_schedule)[0][0]
            times = times[start_sunlit_index:]
            geocentric = geocentric[start_sunlit_index:]

        # If the last index is not sunlit, then we need to adjust the times
        if not sunlit_schedule[-1]:
            end_sunlit_index = np.where(sunlit_schedule)[0][-1]
            times = times[:end_sunlit_index + 1]
            geocentric = geocentric[:end_sunlit_index + 1]

        # Convert geocentric positions to WGS84 geographic positions
        self._convert_geocentric_to_lat_lon_alt(geocentric, times)

        logging.info(f"Calculated {len(self.times)} position points for {self.satellite_name}.")

    def _generate_times(self, ts) -> 'skyfield.timelib.Time':
        """
        Generate time array for satellite position calculations.

        Parameters
        ----------
        ts : skyfield.api.Timescale
            A timescale object from Skyfield.

        Returns
        -------
        skyfield.timelib.Time
            An array of times.
        """
        start_time_dt = pd.to_datetime(self.start_time).to_pydatetime()
        end_time_dt = pd.to_datetime(self.end_time).to_pydatetime()

        total_seconds = (end_time_dt - start_time_dt).total_seconds()
        num_steps = int(total_seconds / self.time_step_sec) + 1

        # Generate array of time points
        return ts.utc(start_time_dt.year, start_time_dt.month, start_time_dt.day,
                      start_time_dt.hour, start_time_dt.minute + (np.arange(num_steps) * self.time_step_sec / 60))

    def _convert_geocentric_to_lat_lon_alt(self, geocentric, times) -> None:
        """
        Convert geocentric positions to latitude, longitude, and altitude.

        Parameters
        ----------
        geocentric : skyfield.positionlib.Geocentric
            The geocentric positions of the satellite.
        times : skyfield.timelib.Time
            The time points of the satellite over the time interval.
        """
        # Convert geocentric positions to WGS84 geographic positions
        subpoint = wgs84.subpoint(geocentric)

        # Store the positions and times in the class attributes
        self.latitudes = np.array(subpoint.latitude.degrees)
        self.longitudes = np.array(subpoint.longitude.degrees)
        self.altitudes = np.array(subpoint.elevation.m)
        self.times = times

    # def _calculate_ground_station_visibilities(self) -> None:

    def _get_saa_groundtrack_coordinates(self) -> None:
        """
        Get the SAA groundtrack times
        """
        # Create a path and find the lat and lon points that are in the SAA
        saa_path = Path(list(zip(self.saa_longitudes_area, self.saa_latitudes_area)))
        in_saa = saa_path.contains_points(list(zip(self.longitudes, self.latitudes)))

        self.saa_latitudes = np.array(self.latitudes[in_saa])
        self.saa_longitudes = np.array(self.longitudes[in_saa])
