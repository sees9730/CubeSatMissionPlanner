# Import libraries
from skyfield.api import EarthSatellite, load, wgs84
from datetime import datetime
import requests
import pandas as pd
import numpy as np

class Satellite:
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
    tle_lines : str
        Two-line element set for the satellite, representing its orbital parameters.
    start_time : datetime
        Start time of the data collection or observation period.
    end_time : datetime
        End time of the data collection or observation period.
    time_step : int
        Time step between data points, in seconds.
    """

    def __init__(self,
                 tle_url: str,
                 tle_file: str,
                 satellite_name: str,
                 start_time: datetime,
                 end_time: datetime,
                 time_step: int):
        """
        Initialize a new Satellite object.
        
        Parameters
        ----------
            TODO: UPDATE
        """
        self.tle_url = tle_url
        self.tle_file = tle_file
        self.satellite_name = satellite_name
        self.start_time = start_time
        self.end_time = end_time
        self.time_step = time_step

        self.longitudes = []
        self.latitudes = []
        self.altitudes = []
        self.times = []

        self.earth_satellite = self.createEarthSatellite()

    def createEarthSatellite(self) -> EarthSatellite:
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
            tle_lines = self.fetchTLEData()
            if tle_lines:
                self.saveTLEData(tle_lines)
                print(f"Loaded {self.satellite_name} TLE from URL.")
        else:
            print(f"Loaded existing TLE data for {self.satellite_name}.")

        # Load and return the TLE data as an EarthSatellite object
        return load.tle_file(self.tle_file)[0]

    def fetchTLEData(self) -> list:
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
            
            # Extract the TLE lines for the satellite 'CUTE'
            tle_data = response.text.splitlines()
            tle_lines = [tle_data[i:i+3] for i in range(0, len(tle_data), 3) if tle_data[i].strip() == 'CUTE']
            
            # Handle case where TLE is not found
            if not tle_lines:
                raise ValueError("CUTE TLE not found in the provided data.")
            
            return tle_lines[0]  # Return the first match of TLE lines

        except requests.exceptions.RequestException as e:
            print(f"Error fetching TLE data: {e}")
        except ValueError as e:
            print(e)
        
        return []  # Return an empty list if fetching fails or TLE is not found

    def saveTLEData(self, tle_lines: list) -> None:
        """
        Save TLE lines to a specified file.
        
        Parameters
        ----------
        tle_lines : list of str
            The lines of TLE data to be saved.
        """
        with open(self.tle_file, 'w') as f:
            f.write('\n'.join(tle_lines) + '\n')
        print(f"TLE data saved to {self.tle_file}.")

    def calculateSatellitePositions(self) -> None:
        """
        Calculates the positions of the specified satellite over the specified time interval.

        Returns
        -------
        positions : wgs84.geographic_position_of
            The positions of the satellite (latitude, longitude, altitude) over the time interval.
        times : skyfield.timelib.Time
            The time points of the satellite over the time interval.
        """
        # Load the timescale for generating time points
        ts = load.timescale()

        # Convert start and end times to Python datetime
        start_time_dt = pd.to_datetime(self.start_time).to_pydatetime()
        end_time_dt = pd.to_datetime(self.end_time).to_pydatetime()

        # Calculate the number of time steps based on the interval and time_step
        total_seconds = (end_time_dt - start_time_dt).total_seconds()
        num_steps = int(total_seconds / self.time_step) + 1

        # Generate an array of time points using Skyfield's timescale
        times = ts.utc(start_time_dt.year, start_time_dt.month, start_time_dt.day,
                    start_time_dt.hour, start_time_dt.minute + (np.arange(num_steps) * self.time_step / 60))

        # Compute the satellite's geocentric positions at the specified times
        geocentric = self.earth_satellite.at(times)

        # Convert geocentric positions to WGS84 geographic positions (latitude, longitude, elevation)
        subpoint = wgs84.subpoint(geocentric)

        # Store the positions and times in the class attributes
        self.latitudes = subpoint.latitude.degrees
        self.longitudes = subpoint.longitude.degrees
        self.altitudes = subpoint.elevation.km
        self.times = times

        print(f"Calculated {len(self.times)} position points for {self.satellite_name}.")

    # def createEarthSatellite(self) -> EarthSatellite:
    #     """
    #     Create an EarthSatellite object from the skyfield library using the TLE lines.
    #     """
    #     # Age of file in days before it is reloaded
    #     max_age_days = 10

    #     # Check if TLE file exists and is recent enough
    #     if not load.exists(self.tle_file) or load.days_old(self.tle_file) >= max_age_days:
    #         try:
    #             # Fetch TLE data from the specified URL
    #             response = requests.get(self.tle_url, timeout = 10)
    #             response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    #             tle_data = response.text

    #             # Extract the TLE lines for satellite
    #             tle_lines = []
    #             for i in range(0, len(tle_data.splitlines()), 3):
    #                 if tle_data.splitlines()[i].strip() == 'CUTE':
    #                     tle_lines.extend(tle_data.splitlines()[i:i+3])

    #             # Handle case where TLE is not found
    #             if not tle_lines:
    #                 raise ValueError("CUTE TLE not found in the provided data.")

    #             # Save the TLE lines to the specified file
    #             with open(self.tle_file, 'w') as f:
    #                 f.write('\n'.join(tle_lines) + '\n')

    #             print(f'Loaded {self.satellite_name} TLE')
    #             # satellite = Utilities.PlanningObjects.Satellite(load.tle_file(filename), satellite_name, filename)
    #             # return satellite  # Load and return the TLE data
    #             return load.tle_file(self.tle_file)
    #             # with open(filename + '.pkl', 'wb') as file:
    #                 # pkl.dump(satellite, file)
    #             # raise KeyboardInterrupt('a')
    #             # print(satellite)
    #             # print(f'Loaded {satellite_name} TLE')
    #             # return load.tle_file(filename)  # Load and return the TLE data


    #         # Handle potential errors during the fetching process
    #         except requests.exceptions.RequestException as e:
    #             print(f"Error fetching TLE data: {e}")
    #         except ValueError as e:
    #             print(e)

    #     else:
    #         # If the TLE file is recent enough, load and return it directly
    #         # print('Loaded existing TLE data')
    #         # satellite = Utilities.PlanningObjects.Satellite(load.tle_file(filename), satellite_name, filename)
    #         # return satellite
    #         return load.tle_file(self.tle_file)
    #         # return EarthSatellite(self.tle_lines)

    # def insertNans(self) -> (np.ndarray, np.ndarray):
    #     """
    #     Insert NaNs into latitude and longitude lists where significant jumps occur.
        
    #     Parameters
    #     ----------
    #     lat : List[float]
    #         List of latitudes.
    #     lon : List[float]
    #         List of longitudes.
            
    #     Returns
    #     -------
    #     Tuple[np.ndarray, np.ndarray]
    #         Latitude and longitude arrays with NaNs inserted.
    #     """
    #     new_lat = [self.latitudes[0]]
    #     new_lon = [self.longitudes[0]]
        
    #     for i in range(1, len(self.latitudes)):
    #         # Check for wrap-around in longitude or significant jumps in latitude
    #         if abs(self.longitudes[i] - self.longitudes[i - 1]) > 30 or abs(self.latitudes[i] - self.latitudes[i - 1]) > 90:
    #             new_lat.append(np.nan)
    #             new_lon.append(np.nan)
    #         else:
    #             new_lat.append(self.latitudes[i])
    #             new_lon.append(self.longitudes[i])

    #     return np.array(new_lat), np.array(new_lon)
    
    # def plotGroundtrack(plan) -> None:
    #     """
    #     Plot the groundtrack of the satellite along with other relevant regions and activities.
        
    #     Parameters
    #     ----------
    #     plan : object
    #         An object containing satellite positions, schedule, and other plan details.
    #     """
    #     # Initialize the plot
    #     fig, ax = plt.subplots(figsize=(12, 6), subplot_kw={'projection': ccrs.PlateCarree()})
    #     ax.stock_img()
    #     ax.coastlines()
        
    #     # Retrieve times and positions from plan
    #     # plan_start_time, plan_end_time, plan_timestep = user_input.getPlanTimes()
    #     # satellite_positions, satellite_times = Utilities.OrbitCalculations.calculateSatellitePosition(plan.satellite, plan_start_time, plan_end_time, plan_timestep)
    #     # satellite_lat = satellite_positions.latitude.degrees
    #     # satellite_lon = satellite_positions.longitude.degrees
        
    #     # Plot the main groundtrack
    #     plotTrackSegment(ax, self.latitudes, self.longitudes, '-', label = 'Groundtrack')
        
    #     # Plot segments that are in the dark side of Earth
    #     eclipse_indices = np.where(plan.schedule != 1)[0]
    #     plot_track_segment(ax, satellite_lat[eclipse_indices], satellite_lon[eclipse_indices], '--', label='Dark-Side', color=[0.4940, 0.1840, 0.5560])
        
    #     # Plot segments above the upper polar keepout zone
    #     plot_track_segment(ax, satellite_lat[satellite_lat > POLAR_KEEPOUT_UPPER], satellite_lon[satellite_lat > POLAR_KEEPOUT_UPPER], 's', label='Polar Keepout', color='red')
        
    #     # Plot segments below the lower polar keepout zone
    #     plot_track_segment(ax, satellite_lat[satellite_lat < POLAR_KEEPOUT_LOWER], satellite_lon[satellite_lat < POLAR_KEEPOUT_LOWER], 's', color='red')
        
    #     # Plot the South Atlantic Anomaly (SAA) regions
    #     saa_indices = np.where(plan.schedule == 5)[0]
    #     plot_track_segment(ax, satellite_lat[saa_indices], satellite_lon[saa_indices], 'r*', label='SAA')

    #     # Plot the SAA border
    #     saa_lat_border, saa_lon_border = user_input.getSAAInfo()
    #     ax.plot(saa_lon_border, saa_lat_border, linestyle='dashdot', color='red', linewidth=2)

    #     # Plot downlinks
    #     downlink_indices = np.where(plan.schedule == 4)[0]
    #     plot_track_segment(ax, satellite_lat[downlink_indices], satellite_lon[downlink_indices], 's', label='Downlink', color='#FF9933')
        
    #     # Plot exposures for target 1
    #     exposure_indices_target1 = np.where(plan.schedule == -1)[0]
    #     plot_track_segment(ax, satellite_lat[exposure_indices_target1], satellite_lon[exposure_indices_target1], 's', label='Exposure', color='seagreen')

    #     # Plot exposures for target 2
    #     if any(plan.schedule == -2):
    #         exposure_indices_target2 = np.where(plan.schedule == Utilities.Dictionaries.MissionTarget.TARGET2.value)[0]
    #         plot_track_segment(ax, satellite_lat[exposure_indices_target2], satellite_lon[exposure_indices_target2], 's', label='Exposure', color='darkgreen')
        
    #     # Plot pointing commands
    #     pointing_indices = np.where(plan.schedule == Utilities.Dictionaries.MissionTarget.POINTING.value)[0]
    #     plot_track_segment(ax, satellite_lat[pointing_indices], satellite_lon[pointing_indices], 's', label='Pointing', color='darkblue')

    #     # Finalize plot
    #     plt.title('Ground Track for the MANTIS satellite', fontsize=20)
    #     plt.legend(fontsize=14, loc='center right')
    #     plt.savefig(fname='Basic_Groundtrack.png', dpi=300)
    #     plt.show()
