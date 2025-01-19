from typing import List, Type, Dict
from PlanningObjects.Satellite import Satellite
from PlanningObjects.MissionConfig import MissionConfig
from PlanningObjects.ScienceMission import ScienceMission
from PlanningObjects.GroundStation import GroundStation
from PlanningObjects.Schedule import Schedule
from PlanningObjects.Target import Target
from PlanningObjects.Eclipse import Eclipse
from PlanningObjects.Survey import Survey
from PlanningObjects.CommandList import CommandList, Node, ActionChunk

# Other libraries
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.path import Path
import numpy as np
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter

import cartopy.feature as cfeature
from skyfield.api import Star
from enum import Enum
import pandas as pd
# import time
import datetime
from scipy.ndimage import binary_dilation
from scipy.interpolate import make_interp_spline

class CubeSatMission:
    """
    A class to represent a CubeSat Mission configuration.

    Attributes
    ----------
    science_mission : ScienceMission
        The scientific mission details for the CubeSat.
    mission_config : MissionConfig
        Configuration parameters for the mission.
    satellite : Satellite
        The satellite associated with this mission.
    ground_stations : List[GroundStation]
        A list of ground stations to be used during the mission.
    visibilities : Schedule
        A schedule of the satellite's visibilities.
    operations : Schedule
        A schedule of the operations for the mission.
    """

    class MissionStatus(Enum):
        TARGET2 = -2
        TARGET1 = -1
        DOWNTIME = 0
        CHARGING = 1
        OBSERVING = 2
        POINTING = 3
        DOWNLINK = 4
        SAA = 5
        POLAR = 6

        def get_key(value: int) -> None:
            """
            Get the key (name) of an enum value
            """
            for member in CubeSatMission.MissionStatus:
                if member.value == value:
                    return member.name
            raise ValueError(f"Value '{value}' not found in Enum.")
        
        def get_value(key: str) -> None:
            """
            Get the value of an enum key (name)
            """
            for member in CubeSatMission.MissionStatus:
                if member.name.casefold() == key.casefold():
                    return member.value
            return None

        # DONE
        def plot_color(value = -10) -> str:
            """
            Get the color of an enum value

            Args:
                value (int): The value of the enum

            Returns:
                str: The color used to plot
            """
            color_mapping = {
                CubeSatMission.MissionStatus.TARGET2.value: 'darkgoldenrod',
                CubeSatMission.MissionStatus.TARGET1.value: 'firebrick',
                CubeSatMission.MissionStatus.DOWNTIME.value: 'red',
                CubeSatMission.MissionStatus.CHARGING.value: 'mediumseagreen',
                CubeSatMission.MissionStatus.POINTING.value: 'steelblue',
                CubeSatMission.MissionStatus.DOWNLINK.value: 'tab:orange',
                CubeSatMission.MissionStatus.SAA.value: 'khaki',
                CubeSatMission.MissionStatus.POLAR.value: 'khaki'
            }
            return color_mapping.get(value, 'black')

        
    class Helpers:

        def inclusive_slice(array: np.ndarray, start: int, end: int) -> np.ndarray:
            """Return a slice of the array from start to end, inclusive."""
            return array[start:end + 1]
        
        def get_pointing_cost() -> int:
            return 80
        
        def isInsideEclipse(satellite, eclipses, time):
            
            # Get the times
            times = satellite.times

            # Get the indices of the eclipses
            eclipse_indices = np.array([eclipse.schedule_indices for eclipse in eclipses])
            
            # Find the index of the given time in the time schedule
            time_index = np.where(times == time)[0]

            # If the time is not found in the time schedule, it's definitely not in an eclipse
            if not time_index.size:
                return False, None

            time_index = time_index[0]  # Extract the index from the array

            # Determine if the time index is inside any of the eclipse index ranges
            inside_eclipse = np.logical_and(
                eclipse_indices[:, 0] <= time_index,
                time_index <= eclipse_indices[:, 1]
            )

            # Return if the time is inside an eclipse
            if any(inside_eclipse):
                eclipse_num = [eclipse.eclipse_number for eclipse, inside in zip(eclipses, inside_eclipse) if inside]
                return True, eclipse_num[0]

            return False, None
        
        def get_energy_dict(mission_config: 'MissionConfig') -> Dict[str, int]:

            # Change the column names to more readable/code friendly names
            ColumnMappingPowerBudget = {
                'Initial Charge [J]': 'INITIAL_CHARGE',
                'Maximum Charge [J]': 'MAXIMUM_CHARGE',
                'Charging [W]': 'CHARGING',
                'Pointing [W]': 'POINTING',
                'Observation [W]': 'TARGET1',
                'Downlink [W]': 'DOWNLINK',
                'Idle [W]': 'DOWNTIME'
            }

            # Get the energy data frame and rename the columns
            df = mission_config.power_info
            df.rename(columns = ColumnMappingPowerBudget, inplace = True)

            # Add the extra columns for equal power values
            df['TARGET2'] = df['TARGET1']
            df['SAA'] = df['DOWNTIME']
            df['POLAR'] = df['DOWNTIME']

            # Convert the DataFrame to a dictionary and extract the first value from each list (assuming single-value columns)
            data_dict = df.to_dict(orient='list')
            result_dict = {k: v[0] for k, v in data_dict.items()}

            return result_dict
            
    

    def __init__(self, excel_file_path: str,
                 debug_vars: Dict[str, bool]):
                #  science_mission: 'ScienceMission',
                #  mission_config: 'MissionConfig',
                #  satellite: 'Satellite',
                #  ground_stations: List['GroundStation'],
                #  visibilities: 'Schedule',
                #  operations: 'Schedule'):

        # Initialize a new CubeSatMission object
        self.pointing_debug = debug_vars['Pointing Debug']

        self.schedules = []
        self._create_mission_config(excel_file_path)
        self._create_satellite()
        self._create_ground_stations()
        self._create_science_mission()
        self._create_operations()
        self._create_commands_list()
        self.getBatteryChargePlot(self.commands_list)

    def _create_mission_config(self, excel_file_path: str) -> None:
        """
        Create a new mission configuration object.

        Parameters
        ----------
        excel_file_path : str
            The path to the Excel file containing the mission configuration data.

        Returns
        -------
        MissionConfig
            The created mission configuration object.
        """
        self.mission_config = MissionConfig(excel_file_path)

        return
    
    def _create_satellite(self) -> None:
        """
        Create a new Satellite object based on the data in the plan_info DataFrame.
        
        Returns
        -------
        Satellite
            A new Satellite object with the data from the plan_info DataFrame.
        """

        self.satellite = Satellite(self.mission_config.plan_info['TLE URL'].values[0],
                         self.mission_config.plan_info['TLE File'].values[0],
                         self.mission_config.plan_info['Satellite Name'].values[0],
                         self.mission_config.plan_info['Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.mission_config.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.mission_config.plan_info['Timestep [sec]'].values[0],
                         self.mission_config.saa_info['Latitude'].values,
                         self.mission_config.saa_info['Longitude'].values,
                         self.mission_config.constraints_info['Polar Constraint'].values[0],
                         self.mission_config.constraints_info['Earth Angle Constraint'].values[0],
                         self.mission_config.constraints_info['Moon Angle Constraint'].values[0])

        return

    def _create_ground_stations(self) -> None:
        """
        Create a new list of GroundStation objects based on the data in the ground_stations_info DataFrame.
        
        Returns
        -------
        List[GroundStation]
            A list of GroundStation objects with the data from the ground_stations_info DataFrame.
        """
        self.ground_stations = []

        for (name, latitude, longitude, altitude, elevation_constraint) in zip(self.mission_config.ground_stations_info['Name'].values,
                                                                                 self.mission_config.ground_stations_info['Latitude'].values,
                                                                                 self.mission_config.ground_stations_info['Longitude'].values,
                                                                                 self.mission_config.ground_stations_info['Altitude [m]'].values,
                                                                                 self.mission_config.ground_stations_info['Elevation Constraint [deg]'].values):

            self.ground_stations.append(GroundStation(name, latitude, longitude, altitude, elevation_constraint, self.satellite))
        
        # Create the overall ground station visibility
        ground_stations_visibility = np.zeros_like(self.ground_stations[0].visibility.status)
        for ground_station in self.ground_stations:
            ground_stations_visibility = ground_station.visibility.status | ground_stations_visibility

        # Create the overall ground station visibilities schedule and add it to the list of visibilities        
        ground_station_visibilities_schedule = Schedule("Ground Stations Schedule",
                                                        self.satellite.start_time, self.satellite.end_time,
                                                        self.satellite.time_step_sec, self.satellite.times,
                                                        ground_stations_visibility, {True: "Visible", False: "Not Visible"})
        self.schedules.append(ground_station_visibilities_schedule)

        return

    def _create_science_mission(self) -> None:
        """
        Create a new ScienceMission object based on the data in the plan_info DataFrame.
        
        Returns
        -------
        ScienceMission
            A new ScienceMission object with the data from the plan_info DataFrame.
        """

        self.science_mission = None

        ## SURVEYS ##
        survey_info = self.mission_config.survey_info
        surveys_data = zip(survey_info['Survey'].values, survey_info['N Targets'].values,
                           survey_info['Pointings Per Target'].values, survey_info['ExpTime Per Pointing [s]'].values,
                           survey_info['ExpTime Per Target [s]'].values, survey_info['Total ExpTime'].values,
                           survey_info['Obs Mode'].values, survey_info['Repeat Targets'].values,
                           survey_info['SurveyPriority'].values, survey_info['Minimum ExpTime [s]'].values)
        
        # Sort surveys_data based on SurveyPriority
        sorted_surveys_data = sorted(surveys_data, key=lambda x: x[8])  # x[8] is the SurveyPriority

        surveys = []

        # Create the survey objects
        for survey_data in sorted_surveys_data:
            survey_name, n_targets, pntngs_per_target, exp_time_per_pntng, exp_time_per_target, total_exp_time, obs_mode, repeat_targets, priority, min_exp_time = survey_data

            surveys.append(Survey(survey_name, n_targets, [], pntngs_per_target, exp_time_per_pntng, min_exp_time, exp_time_per_target, total_exp_time, repeat_targets, obs_mode))
            
        ## TARGETS ##

        # Calculate the visibilities that play a role in calculating target visibility
        saa_keepout_schedule = np.isin(self.satellite.latitudes, self.satellite.saa_latitudes)
        self.schedules.append(Schedule("SAA Keepout Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, saa_keepout_schedule,
                                          {True: "In SAA", False: "Not in SAA"}))
        
        polar_keepout_schedule = (
            (self.satellite.latitudes > (90 - self.satellite.polar_constraint)) |
            (self.satellite.latitudes < (-90 + self.satellite.polar_constraint))
        )
        self.schedules.append(Schedule("Polar Keepout Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, polar_keepout_schedule,
                                          {True: "In Polar Keepout", False: "Not in Polar Keepout"}))

        charging_schedule = self.satellite.earth_satellite.at(self.satellite.times).is_sunlit(self.satellite.ephemeris)
        self.schedules.append(Schedule("Charging Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, charging_schedule,
                                          {True: "Charging", False: "Not Charging"}))
                                          

        # Calculate the targets' visibilities and create the target objects
        targets_info = self.mission_config.targets_info
        targets_data = zip(targets_info['Target'].values, targets_info['HH'].values, targets_info['MM'].values,
                           targets_info['SS'].values, targets_info['dd'].values, targets_info['mm'].values,
                           targets_info['ss'].values, targets_info['Rotation Angle'].values, targets_info['Base Priority'].values,
                           targets_info['Survey'].values)
        
        # Sort targets_data based on Base Priority
        sorted_targets_data = sorted(targets_data, key=lambda x: x[8])  # x[8] is the Base Priority
        
        master_targets_list = []

        survey_names = [survey.name for survey in surveys]

        # Calculate the times at which the moon is invisible
        observer = self.satellite.earth_ephemeris + self.satellite.wgs84.latlon(self.satellite.latitudes, self.satellite.longitudes, self.satellite.altitudes)
        moon_apparent = observer.at(self.satellite.times).observe(self.satellite.moon_ephemeris)
        alt_moon, _, _ = moon_apparent.apparent().altaz()
        moon_invisible = alt_moon.degrees < self.satellite.moon_constraint
        self.satellite.moon_altitudes = alt_moon.degrees
        
        for target_data in sorted_targets_data:
            target_name, ra_hr, ra_min, ra_sec, dec_deg, dec_min, dec_sec, rotation_angle, priority, target_survey = target_data

            # Create the skyfield target object
            target_skyfield_object = Star(ra_hours=(ra_hr, ra_min, ra_sec), dec_degrees=(dec_deg, dec_min, dec_sec))
            
            # Get the target visibility constraints
            apparent = observer.at(self.satellite.times).observe(target_skyfield_object)
            alt, _, _ = apparent.apparent().altaz()
            visible_times = alt.degrees > self.satellite.earth_constraint
            
            # Create the target schedule
            target_schedule = visible_times & ~saa_keepout_schedule & ~polar_keepout_schedule & ~charging_schedule & moon_invisible
            target_schedule_object = Schedule(target_name, self.satellite.start_time, self.satellite.end_time,
                                            self.satellite.time_step_sec, self.satellite.times, target_schedule,
                                            {True: "Visible", False: "Not Visible"})
            
            # Create the target object and store it in the survey
            target_object = Target(target_name, target_skyfield_object, rotation_angle, priority, 0, target_schedule_object, alt.degrees)
            master_targets_list.append(target_object)

            target_survey_index = survey_names.index(target_survey)
            survey = surveys[target_survey_index]
            survey.targets.append(target_object)

        ## ECLIPSES ##
        # Create the eclipse schedules based on the charging schedule
        overall_eclipse_schedule = ~charging_schedule
        
        # Get the start and end indices of contiguous ones (start and ends are inclusive)
        is_one = overall_eclipse_schedule == 1
        eclipse_starts = np.where(np.diff(np.concatenate(([0], is_one.astype(int)))) == 1)[0]
        eclipse_ends = np.where(np.diff(np.concatenate((is_one.astype(int), [0]))) == -1)[0] - 1

        # Create the Eclipse objects
        eclipse_objects = []

        for i, (start, end) in enumerate(zip(eclipse_starts, eclipse_ends)):
            targets_available = {}

            # Get the indices in this chunk and the start and end. Have to add 1 to the end index to include it
            eclipse_schedule = self.Helpers.inclusive_slice(overall_eclipse_schedule, start, end)
            eclipse_schedule = ~eclipse_schedule # Flip the schedule to have it be all zeros (standard status)

            # Get the times of the eclipse
            start_time = self.satellite.times[start]
            end_time = self.satellite.times[end]
            eclipse_times = self.Helpers.inclusive_slice(self.satellite.times, start, end)

            operations = Schedule("Operations", start_time, end_time,
                                  self.satellite.time_step_sec, eclipse_times, eclipse_schedule,
                                  self.MissionStatus)
            
            for survey in surveys:
                for target in survey.targets:
                    target_eclipse_schedule = self.Helpers.inclusive_slice(target.schedule.status, start, end)

                    # Check if the target is available during the eclipse and if it is for long enough
                    if np.any(target_eclipse_schedule) and np.sum(target_eclipse_schedule) * target.schedule.time_step_sec > survey.target_min_exp_time:
                        targets_available[target.name] = target_eclipse_schedule
            
            # Placeholder for now
            targets_names = []
            targets_exp_times = []

            # Create Eclipse object
            eclipse = Eclipse(
                eclipse_number = i,
                targets_available = targets_available,
                targets_names = targets_names,
                targets_exp_times = targets_exp_times,
                schedule_indices = [start, end],
                operations = operations
            )

            eclipse_objects.append(eclipse)

        self.science_mission = ScienceMission(master_targets_list, eclipse_objects, surveys)

        return
    
    def _create_operations(self):
        # Create the master operations schedule
        operations_schedule = np.zeros_like(self.satellite.times, dtype=int)

        # Allocate constraints
        self._allocate_constraints(operations_schedule)

        # Allocate target availability and update eclipses
        self._allocate_targets_and_update_eclipses(operations_schedule)

        # Allocate downlink windows
        self._allocate_downlink_windows(operations_schedule)

        # Save the operations schedule before pointing operations
        operations_schedule_bp = np.copy(operations_schedule)
        self.operations = []
        self.operations.append(Schedule("Before Pointing Operations Schedule", self.satellite.start_time, self.satellite.end_time,
                                        self.satellite.time_step_sec, self.satellite.times, operations_schedule_bp, self.MissionStatus))

        # Allocate pointing operations and choose targets to observe
        self._allocate_pointing_operations(operations_schedule, self.pointing_debug)

        # Allocate pointing windows for charging
        self._allocate_pointing_windows_for_charging(operations_schedule)

        # Handle edge cases for downtime
        self._handle_edge_cases_for_downtime(operations_schedule)

        # Update the eclipses with the final operations schedule
        self._update_eclipses(operations_schedule)
        
        # Save the operations schedule after pointing operations
        operations_schedule_ap = np.copy(operations_schedule)
        self.operations.append(Schedule("Final Operations Schedule", self.satellite.start_time, self.satellite.end_time,
                                self.satellite.time_step_sec, self.satellite.times, operations_schedule_ap, self.MissionStatus))

    def _create_commands_list(self):

        # Initialize the commands list
        commands_list = CommandList()

        # Get the indices of the changes in the operations schedule
        operations_schedule = self.get_operation_by_name("Final Operations Schedule").status
        change_indices = self.getChangeIndices(operations_schedule, index = 'after', change_type = 'both')
        change_indices = np.concatenate(([0], change_indices))  # Include the starting index

        # Get the net eneregy dictionary
        net_energy_dict = self.Helpers.get_energy_dict(self.mission_config)

        # Get the times
        times = self.satellite.times.utc_datetime()

        # Loop through the changes in the operations schedule
        for j, index in enumerate(change_indices):

            # Get the time of the action
            action_time = times[index]

            # Get the duration of the action
            next_index = change_indices[j + 1] if j + 1 < len(change_indices) else -1  # Handle last index
            action_duration_sec = times[next_index] - action_time
            action_duration_min = datetime.timedelta(minutes = action_duration_sec.total_seconds() / 60)

            # Get the key of the action, the power value, the excel text, and json text
            action_key = self.MissionStatus.get_key(operations_schedule[index])
            energy_value = net_energy_dict[action_key] * action_duration_sec.total_seconds()
            action_text = f'{action_key} for {action_duration_min} min'
            action_json = 'TEST'
            # print(f"Time: {action_time}, Duration: {action_duration_min}, Action: {action_key}, Power: {power_value}")

            # Determine if the action is inside an eclipse
            action_inside_eclipse, action_eclipse_num = self.Helpers.isInsideEclipse(self.satellite, self.science_mission.eclipses, action_time)

            # Add the action to the list
            action = ActionChunk(
                action_id = j,
                time = action_time,
                duration = action_duration_min,
                energy = energy_value,
                key = action_key,
                text = action_text,
                json = action_json,
                in_eclipse = action_inside_eclipse,
                eclipse_num = action_eclipse_num
            )
            commands_list.addToTail(action)

        self.commands_list = commands_list
    
    def getBatteryChargePlot(self, actions_list):
        """
            Generates a battery charge plot based on power budget and action list.

            Args:
                file_path (str): Path to the power budget file.
                sheet_name (str): Name of the sheet within the file containing power data.
                actions_list (LinkedList): Linked list of Action objects representing planned actions.
                plan (str): Name or identifier of the plan being analyzed.

            Returns:
                None (plots the battery charge profile)
        """

        # Get the power budget information
        net_energy_dict =  self.Helpers.get_energy_dict(self.mission_config)
        initial_charge = net_energy_dict['INITIAL_CHARGE']
        max_charge = net_energy_dict['MAXIMUM_CHARGE']

        # Loop through the actions
        current_node = actions_list.head_node
        
        # Initialize the arrays for plotting
        battery_charge_joules = [initial_charge]
        battery_charge_time = [current_node.getData().getTime()]

        while current_node:

            # Get the data for the current node
            action = current_node.getData()
            action_time = action.getTime()
            action_duration = action.getDuration()
            action_energy = action.getEnergy()

            # Update the arrays
            print(battery_charge_joules[-1], action.getKey(), action_energy)
            battery_charge_joules.append(min(battery_charge_joules[-1] + action_energy, max_charge))
            print(battery_charge_joules[-1])
            print()
            battery_charge_time.append(action_time + action_duration)

            # Move to the next node
            current_node = current_node.getNextNode()

        # Plot the battery charge
        eclipse_times = []
        for eclipse in self.science_mission.eclipses:
            for i in range(2):
                eclipse_times.append(self.satellite.times.utc_datetime()[eclipse.schedule_indices[i]])
        self.plotBatteryCharge(battery_charge_time, battery_charge_joules, eclipse_times)

    def plotBatteryCharge(self, date_time, y, eclipse_times):
        """
            Plots the battery charge over time with eclipse highlighting.

            Args:
                x (list): List of time values (in minutes).
                y (list): List of corresponding onboard energy values (in Joules).
                plan (Plan object): Plan object containing schedule and eclipse information.

            Returns:
                None (displays the plot)
        """

        # Create a smooth interpolated curve
        x = [(time - date_time[0]).total_seconds() for time in date_time]
        interp_line = make_interp_spline(x, y)
        X = np.linspace(min(x), max(x), len(self.get_operation_by_name("Final Operations Schedule").status) * 1)  # Denser sampling for smoothness
        Y = interp_line(X)
        X = [date_time[0] + datetime.timedelta(seconds = time) for time in X]

        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.title('Power Profile Through Plan')
        plt.plot(X, Y, color='#FF5003', linewidth=4)  # Plot the energy curve
        # plt.plot(x, y, color='#FF5003', linewidth=4)
        
        # Highlight eclipse periods
        for i in range(0, len(eclipse_times), 2):
            start_index = eclipse_times[i]
            if i + 1 < len(eclipse_times):
                end_index = eclipse_times[i + 1]
                plt.axvspan(start_index, end_index, color='lightsteelblue', alpha=0.3)
        
        # Format the plot
        plt.ylabel('Total Energy [J]')
        plt.xlabel('Time in UTC')
        plt.grid(which='both', linestyle='--', linewidth=0.2)
        plt.xticks(rotation = 45)
        x_fmt = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
        plt.gca().xaxis.set_major_formatter(x_fmt)
        # plt.gca().yaxis.set_major_formatter(FuncFormatter(formatFunc))
        
    # def formatFunc(value, position = None):
    #     """
    #         Formats a numerical value into scientific notation with two decimal places.

    #         Args:
    #             value: The numerical value to be formatted.
    #             position: (Optional) The position for matplotlib tick formatting (not used in this implementation).

    #         Returns:
    #             A string representing the value in scientific notation.
    #     """
    #     exponent = int(np.log10(value))
    #     coefficient = value / (10 ** exponent)
    #     return f'{coefficient:.2f}e{exponent}'



    def _allocate_constraints(self, operations_schedule):
        """Allocate the constraints (SAA, Polar Keepout, Charging) in the operations schedule."""
        saa_schedule = self.get_schedule_by_name("SAA Keepout Schedule").status
        polar_schedule = self.get_schedule_by_name("Polar Keepout Schedule").status
        charging_schedule = self.get_schedule_by_name("Charging Schedule").status

        operations_schedule[saa_schedule] = self.MissionStatus.SAA.value
        operations_schedule[polar_schedule] = self.MissionStatus.POLAR.value
        operations_schedule[charging_schedule] = self.MissionStatus.CHARGING.value

    def _allocate_targets_and_update_eclipses(self, operations_schedule):
        """Allocate the availability of the targets and update the eclipses."""
        for eclipse in self.science_mission.eclipses:

            # Get the eclipse schedule
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            eclipse_schedule = self.Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end)

            # Update the eclipse schedule
            # for target_schedule in eclipse.targets_available.values():
            for _, target_schedule in eclipse.targets_available.items():
                if np.any(target_schedule):

                    # Mark the eclipse as observing a target
                    eclipse_schedule[target_schedule] = self.MissionStatus.OBSERVING.value

                    if np.all(eclipse_schedule != self.MissionStatus.DOWNTIME.value):
                        break  # Stop if there is no downtime in the eclipse

            # Save the eclipse schedule
            eclipse.operations.status = eclipse_schedule

    def _allocate_downlink_windows(self, operations_schedule):
        """Allocate the downlink windows in the operations schedule."""
        # Get the downlink schedule
        downlink_schedule = self.get_schedule_by_name("Ground Stations Schedule").status
        operations_schedule[downlink_schedule] = self.MissionStatus.DOWNLINK.value

        # Allocate the pointing windows for downlink
        dilated_downlink = self.getMovesOutside(operations_schedule == self.MissionStatus.DOWNLINK.value, pointing_cost=self.Helpers.get_pointing_cost())
        operations_schedule[dilated_downlink == 1] = self.MissionStatus.POINTING.value

        # Update the eclipses
        for eclipse in self.science_mission.eclipses:
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            eclipse_schedule = np.copy(self.Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end))
            eclipse.operations.status = eclipse_schedule

    def _allocate_pointing_operations(self, operations_schedule, pointing_debug):
        """Allocate the pointing operations and choose targets to observe."""
        min_exp_time = min([survey.target_min_exp_time for survey in self.science_mission.surveys])

        for eclipse_num, eclipse in enumerate(self.science_mission.eclipses):
            eclipse_schedule = eclipse.operations.status
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            if pointing_debug:
                self.plot_eclipse_operations(eclipse_num)

            self.update_targets_priorities(eclipse, pointing_debug)

            # Allocate the pointing operations if there is at least one target available
            if np.any(eclipse_schedule == self.MissionStatus.OBSERVING.value):
                target_num = self.MissionStatus.TARGET1.value
                for target_name, target_schedule in eclipse.targets_available.items():
                    if np.any(target_schedule):
                        self._allocate_target_pointing_operations(eclipse, eclipse_schedule, operations_schedule, target_name, target_schedule, target_num, eclipse_start, eclipse_end, min_exp_time, pointing_debug)
                        # Break if all targets pointing windows have been allocated
                        if target_num == -3:
                            break
            else:
                print(f'Eclipse {eclipse_num} has no targets available')

    def _allocate_target_pointing_operations(self, eclipse, eclipse_schedule, operations_schedule, target_name, target_schedule, target_num, eclipse_start, eclipse_end, min_exp_time, pointing_debug):
        """Allocate a target in the eclipse schedule."""
        exception = False

        # Get the other target's number status
        other_target_num = {
            self.MissionStatus.TARGET1.value: self.MissionStatus.OBSERVING.value,
            self.MissionStatus.TARGET2.value: self.MissionStatus.TARGET1.value
        }.get(target_num, None)

        # Check if there is enough time to observe the target
        free_target_slots = target_schedule & (eclipse_schedule == self.MissionStatus.OBSERVING.value)
        remaining_time = (np.sum(free_target_slots) - self.Helpers.get_pointing_cost()) * self.satellite.time_step_sec if other_target_num == self.MissionStatus.OBSERVING.value else np.sum(free_target_slots) * self.satellite.time_step_sec
        target_min_exp_time = self.science_mission.get_survey_of_target(target_name).target_min_exp_time
        enough_time = remaining_time >= target_min_exp_time

        # Target 1 has priority if it has 80% of the observing time
        if np.sum(free_target_slots) != 0:
            if (target_num == self.MissionStatus.TARGET1.value) and ((np.sum(free_target_slots) / np.sum(eclipse_schedule == self.MissionStatus.OBSERVING.value)) >= 0.8) and enough_time:
                eclipse_schedule[free_target_slots == 1] = target_num
                self._update_eclipse_and_operations(eclipse, eclipse_schedule, operations_schedule, target_name, target_num, eclipse_start, eclipse_end, pointing_debug)
                target_num = -3 # Break out of the outer loop
            
            # Only allocate pointing operations if there is enough time for a second target
            elif enough_time:
                eclipse_schedule[free_target_slots == 1] = target_num
                pointing_moves = np.zeros(len(eclipse_schedule))
                other_target_size = np.sum(eclipse_schedule == other_target_num)

                if other_target_size * self.satellite.time_step_sec >= min_exp_time:
                    first_target_num = self.findFirstTarget(eclipse_schedule, 1)
                    index_start_pointing, index_end_pointing = self._get_pointing_indices(eclipse_schedule, target_num, other_target_num, first_target_num)

                    if index_end_pointing < len(eclipse_schedule) and eclipse_schedule[index_end_pointing] != target_num:
                        indices = self.getChangeIndices(eclipse_schedule, target_num, 'after', 'both')
                        visibility_start_index, visibility_end_index = indices[0], indices[1]
                        eclipse_schedule[visibility_start_index: visibility_end_index] = self.MissionStatus.DOWNTIME.value
                        exception = True

                    if not exception:
                        pointing_moves[index_start_pointing: index_end_pointing] = 1
                        eclipse_schedule[pointing_moves == 1] = self.MissionStatus.POINTING.value

                # Update the eclipse and operations
                self._update_eclipse_and_operations(eclipse, eclipse_schedule, operations_schedule, target_name, target_num, eclipse_start, eclipse_end, pointing_debug)

                # Update the target number
                target_num -= 1

    def _get_pointing_indices(self, eclipse_schedule, target_num, other_target_num, first_target_num):
        """Get the start and end indices for pointing."""
        if first_target_num == target_num:
            index_end_pointing = self.getChangeIndices(eclipse_schedule, other_target_num, 'after', 'start')[0]
            index_start_pointing = index_end_pointing - self.Helpers.get_pointing_cost()
        else:
            index_start_pointing = self.getChangeIndices(eclipse_schedule, target_num, 'after', 'start')[0]
            index_end_pointing = index_start_pointing + self.Helpers.get_pointing_cost()
        return index_start_pointing, index_end_pointing

    def _update_eclipse_and_operations(self, eclipse, eclipse_schedule, operations_schedule, target_name, target_num, eclipse_start, eclipse_end, pointing_debug):
        """Update the eclipse and operations schedule."""

        # Update the eclipse's properties for the eclipse object
        eclipse.operations.status = eclipse_schedule
        index = 0 if target_num == self.MissionStatus.TARGET1.value else 1
        if len(eclipse.targets_names) > 0:
            eclipse.targets_names[index] = target_name
            eclipse.targets_exp_times[index] = np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec
        else:
            eclipse.targets_names.append(target_name)
            eclipse.targets_exp_times.append(np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec)

        # Update the target's properties for the target object
        target = self.science_mission.get_target_by_name(target_name)
        target.current_exp_time += np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec

        # Update the operations schedule with the eclipse's schedule
        operations_schedule[eclipse_start: eclipse_end + 1] = eclipse_schedule
        
        # Plot the eclipse's operations
        if pointing_debug:
            self.plot_eclipse_operations(eclipse.eclipse_number)

    # Done
    def _allocate_pointing_windows_for_charging(self, operations_schedule):
        """_summary_

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
        """

        # Get the indices before you start charging (get the last status before you start charging)
        indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.CHARGING.value, index='before', change_type='start')

        # See detailed visualization inside each function
        for _, index in enumerate(indices):
            if operations_schedule[index + self.Helpers.get_pointing_cost()] == self.MissionStatus.POINTING.value:
                pass
            elif operations_schedule[index] == self.MissionStatus.DOWNTIME.value:
                self._allocate_pointing_before_charging_during_downtime(operations_schedule, index)
            elif operations_schedule[index - self.Helpers.get_pointing_cost()] == self.MissionStatus.POINTING.value:
                self._allocate_charging_after_pointing_before_charging_during_unknown(operations_schedule, index)
            elif operations_schedule[index] == self.MissionStatus.POLAR.value:
                self._allocate_pointing_before_charging_during_polar(operations_schedule, index)
            elif operations_schedule[index] != self.MissionStatus.POINTING.value:
                self._allocate_pointing_if_possible(operations_schedule, index)

        # Get the indices after you end charging
        indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.CHARGING.value, index='after', change_type='end')

        # See detailed visualization inside each function
        for index in indices:
            if operations_schedule[index] == self.MissionStatus.SAA.value:
                self._allocate_pointing_after_saa(operations_schedule, index)
            elif operations_schedule[index] not in (self.MissionStatus.POINTING.value, self.MissionStatus.DOWNTIME.value):
                self._allocate_pointing_before_end(operations_schedule, index)

        # # Update the eclipses
        # self._update_eclipses(operations_schedule)

    # Done
    def _allocate_pointing_before_charging_during_downtime(self, operations_schedule, index):
        """Allocate pointing for charging before charging during downtime.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Example (Dn = downtime, P = pointing, T = target, C = charging):
        # Prev.: [T T T T Dn Dn C C]
        # After: [T T T T P  P  C C]

        # Get the index of the start of the closest downtime and mark it that as the beginning of the pointing 
        start_downtime_indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.DOWNTIME.value, index='after', change_type='start')
        closest_start_downtime_index = self.getClosestValue(value=index, array=start_downtime_indices)
        start_pointing_index = closest_start_downtime_index
        end_pointing_index = start_pointing_index + self.Helpers.get_pointing_cost() + 1
        operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.POINTING.value

    def _allocate_charging_after_pointing_before_charging_during_unknown(self, operations_schedule, index):
        """Allocate charging after pointing before charging during unknown.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Example (D = downlink, P = pointing, T = target, C = charging, Po = polar):
        # Prev.: [D D P P Po Po C C]
        # After: [D D P P C  C  C C]

        # Get the status of what comes before the charging window (but after the pointing window detected) and mark it as charging
        status_after_pointing = operations_schedule[index]
        if status_after_pointing not in (self.MissionStatus.TARGET1, self.MissionStatus.TARGET2):
            start_status_indices = self.getChangeIndices(schedule=operations_schedule, value=status_after_pointing, index='after', change_type='start')
            closest_start_status_index = self.getClosestValue(value=index - self.Helpers.get_pointing_cost(), array=start_status_indices)
            start_pointing_index = closest_start_status_index
            end_pointing_index = start_pointing_index + self.Helpers.get_pointing_cost() + 1
            operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.CHARGING.value

    # Done
    def _allocate_pointing_before_charging_during_polar(self, operations_schedule, index):
        """Allocate pointing for charging before charging during polar.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Example (P = pointing, T = target, C = charging, Po = polar):
        # Prev.: [T T T T Po Po C C]
        # After: [T T T T P  P  C C]
        
        # Get the start of the closest polar and mark its beginning as the beginning of the pointing
        start_polar_indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.POLAR.value, index='after', change_type='start')
        closest_start_polar_index = self.getClosestValue(value=index, array=start_polar_indices)
        start_pointing_index = closest_start_polar_index
        end_pointing_index = start_pointing_index + self.Helpers.get_pointing_cost() + 1
        operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.POINTING.value

    # Done
    def _allocate_pointing_if_possible(self, operations_schedule, index):
        """Allocate pointing for charging in the schedule if possible.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """
        
        # Example (nP = not pointing, P = pointing, C = charging):
        # Prev.: [nP nP C C C C C]
        # After: [nP nP P P P C C]

        # Start pointing during the beginning of the charging window
        start_pointing_index = index + 1
        end_pointing_index = start_pointing_index + self.Helpers.get_pointing_cost() + 1
        if np.all(operations_schedule[start_pointing_index: end_pointing_index] == self.MissionStatus.CHARGING.value):
            operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.POINTING.value

    # Done
    def _allocate_pointing_after_saa(self, operations_schedule, index):
        """Allocate pointing for charging after the start of the SAA.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Example (S = SAA, nP = not pointing, P = pointing, C = charging):
        # Prev.: [C C S S S nP nP]
        # After: [C C S P P nP nP]

        # Start pointing before the end of the SAA to take advantage of the SAA
        end_SAA_indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.SAA.value, index='after', change_type='end')
        closest_end_SAA_index = self.getClosestValue(value=index, array=end_SAA_indices)
        if operations_schedule[closest_end_SAA_index + 1] != self.MissionStatus.POINTING.value:
            end_pointing_index = closest_end_SAA_index + 1
            start_pointing_index = end_pointing_index - self.Helpers.get_pointing_cost()
            operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.POINTING.value

    # Done
    def _allocate_pointing_before_end(self, operations_schedule, index):
        """Allocate pointing for charging before the end of the schedule.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Edge case for last pointing for charging
        start_pointing_index = index - self.Helpers.get_pointing_cost() - 1
        end_pointing_index = index
        operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.POINTING.value

    # TODO: Comment, docstring
    def _handle_edge_cases_for_downtime(self, operations_schedule):
        


        indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.POLAR.value, index='after', change_type='end')

        for _, index in enumerate(indices):
            if operations_schedule[index] == self.MissionStatus.CHARGING.value:
                start_charging_indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.CHARGING.value, index='after', change_type='start')
                end_charging_indices = self.getChangeIndices(schedule=operations_schedule, value=self.MissionStatus.CHARGING.value, index='before', change_type='end')
                closes_start_charging_index = self.getClosestValue(value=index, array=start_charging_indices)
                closest_end_charging_index = self.getClosestValue(value=index, array=end_charging_indices)
                start_pointing_index = closes_start_charging_index
                end_pointing_index = closest_end_charging_index + 1
                operations_schedule[start_pointing_index: end_pointing_index] = self.MissionStatus.DOWNTIME.value

        if np.sum(operations_schedule == self.MissionStatus.OBSERVING.value) > 0:
            operations_schedule[operations_schedule == self.MissionStatus.OBSERVING.value] = self.MissionStatus.DOWNTIME.value



    # TODO: Comment, docstring
    def update_targets_priorities(self, eclipse, pointing_debug):
        """Update the priorities of the targets based on their exposure times."""
        if len(eclipse.targets_available) != 0:
            max_exposure_time = max(np.sum(list(eclipse.targets_available.values()), axis=1) * self.satellite.time_step_sec)
            target_to_pop = []

            for target_name, target_schedule in eclipse.targets_available.items():
                target_survey = self.science_mission.get_survey_of_target(target_name)
                target = self.science_mission.get_target_by_name(target_name)
                if target.current_exp_time < target_survey.target_exp_time:
                    target_exposure_time = np.sum(target_schedule) * self.satellite.time_step_sec
                    time_available_factor = max_exposure_time / target_exposure_time
                    target.eclipse_priority = target.base_priority + time_available_factor
                else:
                    target_to_pop.append(target_name)

            for target_name in target_to_pop:
                eclipse.targets_available.pop(target_name)

            sorted_targets = sorted(eclipse.targets_available.items(), key=lambda item: self.science_mission.get_target_by_name(item[0]).eclipse_priority)
            eclipse.targets_available = dict(sorted_targets)

            # Print the updated priorities
            if pointing_debug:
                print("After sorting:")
                for target_name in eclipse.targets_available.keys():
                    target = self.science_mission.get_target_by_name(target_name)
                    print(f"Target: {target_name}, Priority: {target.eclipse_priority}")

    def _update_eclipses(self, operations_schedule):
        for eclipse in self.science_mission.eclipses:
            eclipse_schedule_in_mission = self.Helpers.inclusive_slice(operations_schedule, eclipse.schedule_indices[0], eclipse.schedule_indices[1])
            eclipse.operations.status = eclipse_schedule_in_mission
            for i in range(len(eclipse.targets_exp_times)):
                eclipse.targets_exp_times[i] = np.sum(eclipse_schedule_in_mission == (i - 1)) * self.satellite.time_step_sec


    # Done
    def get_schedule_by_name(self, name: str) -> Schedule:
        """Get the schedule with the given name.

        Args:
            name (str): The name of the schedule to retrieve.

        Returns:
            Schedule: The schedule with the given name.
        """

        for schedule in self.schedules:
            if schedule.name == name:
                return schedule

    # Done
    def get_operation_by_name(self, name: str) -> Schedule:
        """Get the operation with the given name.

        Args:
            name (str): The name of the operation to retrieve.

        Returns:
            Schedule: The operation with the given name.
        """

        for operation in self.operations:
            if operation.name == name:
                return operation

    ## TODO: update docstring and look into refactor
    def getMovesOutside(self, array, pointing_cost):
        """
            Get the outside pointing slots for a given array.

            Args:
                array (numpy.ndarray): The operation schedule.
                pointing_cost (int): The number of move slots.

            Returns:
                numpy.ndarray: The move slots mask.

            Description:
                This function takes an operation schedule and a pointing cost as input. It creates a copy of the operation schedule to avoid modifying the original. It then performs binary dilation on the copied schedule to expand it by the number of move slots. The move slots mask is generated by identifying the expanded parts not in the original schedule. The function returns the pointing slots mask.
        """
        
        # Create a copy of the operation schedule to avoid modifying the original
        array_copy = array.copy()

        # Perform binary dilation to expand the operation schedule by the number of pointing slots
        expanded_schedule = binary_dilation(array_copy,
                                            iterations = pointing_cost,
                                            structure = np.array([True, True, True]))

        # Generate the pointing slots mask by identifying the expanded parts not in the original schedule
        pointing_moves_mask = (expanded_schedule == 1) & (array == 0)

        return pointing_moves_mask


    def findFirstTarget(self, arr, obs):
        if not obs:
            for value in arr:
                if self.MissionStatus.TARGET2.value == value or self.MissionStatus.TARGET1.value == value:
                    return value
        elif obs:
            for value in arr:
                if self.MissionStatus.TARGET2.value == value or self.MissionStatus.TARGET1.value == value or self.MissionStatus.OBSERVING.value == value:
                    return value
        return None  # Return None if no such value is found
    
    def getClosestValue(self, value, array):
        # Ensure the value is not None
        if value is None:
            raise ValueError('value must not be None')
        
        # Ensure the array is not empty
        if len(array) == 0:
            raise ValueError('The array must not be empty')
        
        # Calculate the absolute differences between the array elements and the target value
        diff = abs(np.array(array) - value)
        
        # Find the index of the smallest difference
        min_val_index = np.argmin(diff)
        
        # Return the array element at the index of the smallest difference
        return array[min_val_index]

        
    def getChangeIndices(self, schedule, value=None, index='', change_type=''):
        """ 
        Finds indices in the schedule where a change occurs, based on the given parameters.

        Args:
            schedule (numpy.ndarray): The input array representing the schedule.
            value: The value to check for changes (default is None, meaning any change).
            index: Specifies whether to find changes 'before' or 'after' occurrences of the value 
                (default is '', meaning no index restriction).
            change_type: Specifies whether to find the 'start', 'end', or 'both' points of a change 
                        (default is '', meaning any change).

        Returns:
            numpy.ndarray: An array of indices where the specified change occurs.

        Raises:
            ValueError: If invalid values are provided for 'index' or 'change_type'.
        """

        # Input validation
        if index not in ['before', 'after']:
            raise ValueError("index must be either 'before' or 'after'")
        elif change_type not in ['start', 'end', 'both']:
            raise ValueError("change_type must be either 'start', 'end', or 'both'")

        if value is None:
            # Detect any change in value
            changes = np.diff(schedule) != 0 

            # Handle 'before' and 'after' cases
            result = np.where(changes)[0]

            if index == 'after':
                result = result + 1  # Shift indices by 1 to get the index after the change
                # Ensure we include 0 if there's a change at the beginning
                if changes[0]:
                    result = np.concatenate(([0], result))
                result = result[result < len(schedule)]  # Exclude out-of-bounds indices
            elif index == 'before':
                if changes[0]:
                    result = np.concatenate(([0], result)) 

            return result
        else:
            # Detect changes to/from the specified value
            condition = np.array(schedule) == value
            condition = np.concatenate(([0], condition)) if index == 'after' else np.concatenate((condition, [0]))

        if change_type == 'both':
            return np.where(np.diff(condition))[0]  # Return both start and end indices
        elif change_type == 'start':
            return np.where(np.diff(condition) == 1)[0]
        elif change_type == 'end':
            return np.where(np.diff(condition) == -1)[0]


    def _plot_operations(self, num_plots = 2):

        # Get the operations schedule and the satellite times
        operations_schedule_bp = self.get_operation_by_name("Before Pointing Operations Schedule").status
        operations_schedule_ap = self.get_operation_by_name("Final Operations Schedule").status
        times = self.satellite.times.utc_datetime()
        times_plot_lims = []

        # Get the total number of times to plot (total number of eclipses divided by 5)
        indices_to_plot = int(len(times) / num_plots)

        for i in range(0, len(times) - 1, indices_to_plot):
            xlim_start = i
            xlim_end = i + indices_to_plot
            if xlim_end > len(times):
                xlim_end = len(times) - 1

            # Initialize the plot
            fig, ax = plt.subplots(2, 1, figsize=(24, 6))

            # Plot the operations schedule before pointing
            ax[0].plot(times, operations_schedule_bp, drawstyle = 'steps-mid')
            for eclipse in self.science_mission.eclipses:
                eclipse_start = eclipse.schedule_indices[0]
                eclipse_end = eclipse.schedule_indices[1]
                ax[0].axvspan(times[eclipse_start], times[eclipse_end], color='lightsteelblue', alpha=0.3)
                if np.mod(i, 5) == 0:
                    times_plot_lims.append([times[eclipse_start], times[eclipse_end]])

            ax[0].set_yticks([status.value for status in self.MissionStatus], labels=[status.name for status in self.MissionStatus])
            ax[0].set_xticks([0])

            for status in self.MissionStatus:
                ax[0].plot(times[operations_schedule_bp == status.value], operations_schedule_bp[operations_schedule_bp == status.value], marker = 's', linestyle='')

            ax[0].set_ylabel("Status", fontsize = 25)
            ax[0].tick_params(labelsize=16)
            ax[0].set_xlim(times[xlim_start], times[xlim_end])
            ax[0].set_title('Schedule Before Pointing Allocation', fontsize = 30)
            ax[0].grid(True)

            # Plot the operations schedule after pointing

            ax[1].plot(times, operations_schedule_ap, drawstyle = 'steps-mid')
            for eclipse in self.science_mission.eclipses:
                eclipse_start = eclipse.schedule_indices[0]
                eclipse_end = eclipse.schedule_indices[1]
                ax[1].axvspan(times[eclipse_start], times[eclipse_end], color='lightsteelblue', alpha=0.3)
                if np.mod(i, 5) == 0:
                    times_plot_lims.append([times[eclipse_start], times[eclipse_end]])

            ax[1].set_yticks([status.value for status in self.MissionStatus], labels=[status.name for status in self.MissionStatus])

            for status in self.MissionStatus:
                ax[1].plot(times[operations_schedule_ap == status.value], operations_schedule_ap[operations_schedule_ap == status.value], marker = 's', linestyle='')

            ax[1].set_ylabel("Status", fontsize = 25)
            ax[1].set_xlabel("Time in UTC", fontsize = 25)
            ax[1].tick_params(labelsize = 16)
            ax[1].set_xlim(times[xlim_start], times[xlim_end])
            ax[1].set_title('Schedule After Pointing Allocation', fontsize = 30)
            ax[1].grid(True)
            
            fig.tight_layout()
            date_format = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
            plt.gca().xaxis.set_major_formatter(date_format)
            # plt.xticks(rotation = 15)
            plt.show()

    def plot_eclipse_operations(self, eclipse_num: int):

        # Get the data for the eclipse
        eclipse = self.science_mission.eclipses[eclipse_num]
        times = eclipse.operations.time.utc_datetime()
        eclipse_schedule = eclipse.operations.status

        # Plot the operations schedule
        plt.plot(times, eclipse_schedule, drawstyle = 'steps-mid')
        for status in self.MissionStatus:
            plt.plot(times[eclipse_schedule == status.value], eclipse_schedule[eclipse_schedule == status.value], marker = 's', linestyle='')
        if len(eclipse.targets_names) > 0:
            plt.plot([], [], label = f'Target 1 = {eclipse.targets_names[0]}. Exp Time = {eclipse.targets_exp_times[0]}', color = 'green')
            if eclipse.targets_exp_times[0] != np.sum(eclipse_schedule == self.MissionStatus.TARGET1.value) * self.satellite.time_step_sec:
                print(eclipse.targets_names[0],eclipse.targets_exp_times[0], np.sum(eclipse_schedule == self.MissionStatus.TARGET1.value) * self.satellite.time_step_sec)
                raise ValueError('The target exposure time does not match the number of slots allocated to the target')
            if np.any(eclipse_schedule == self.MissionStatus.TARGET2.value):
                plt.plot([], [], label = f'Target 2 = {eclipse.targets_names[1]}. Exp Time = {eclipse.targets_exp_times[1]}', color = 'orange')
                if eclipse.targets_exp_times[1] != np.sum(eclipse_schedule == self.MissionStatus.TARGET2.value) * self.satellite.time_step_sec:
                    raise ValueError('The target exposure time does not match the number of slots allocated to the target')
            plt.legend(loc = 'best')
        else:
            plt.plot([], [], label = f'Observation Time = {np.sum(eclipse_schedule == self.MissionStatus.OBSERVING.value)}s', color = 'green')
            plt.legend(loc = 'best')
        plt.yticks([status.value for status in self.MissionStatus], labels=[status.name for status in self.MissionStatus])
        plt.xticks(rotation = 15)
        plt.grid()
        # plt.xlim(eclipse.operations.time.utc_datetime()[0], eclipse.operations.time.utc_datetime()[-1])
        plt.xlabel('Time [UTC]')
        plt.ylabel('Visibility Status')
        plt.title(f'Eclipse {eclipse_num} Operations Schedule')
        plt.show()

    def plot_eclipse_summary(self, eclipse_num: int):

        # # Get the data for the target
        # target_name = self.science_mission.eclipses[eclipse_num].targets_names[0]
        # target_altitude = self.science_mission.get_target_by_name(target_name).target_altitude

        # Get the data for the eclipse
        eclipse = self.science_mission.eclipses[eclipse_num]
        eclipse_schedule = eclipse.operations.status
        eclipse_start = eclipse.schedule_indices[0]
        eclipse_end = eclipse.schedule_indices[1]
        times = eclipse.operations.time.utc_datetime()

        # Get the final operations schedule
        operations_schedule = self.get_operation_by_name("Final Operations Schedule").status
        final_operations_in_eclipse = self.Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end)


        # Get the data target for the target
        # target = self.science_mission.get_target_by_name(target_name)
        # target_altitude = self.Helpers.inclusive_slice(target.target_altitude, eclipse_start, eclipse_end)

        # Plot the target(s)'s altitudes
        fig, ax = plt.subplots(2, 2, figsize=(10, 10))

        colors = ['lightcoral', 'gold']
        target_names = []
        i = 0
        for i, target_name in enumerate(eclipse.targets_names):

            target = self.science_mission.get_target_by_name(target_name)
            target_altitude = self.Helpers.inclusive_slice(target.target_altitude, eclipse_start, eclipse_end)
            target_names.append(target_name)

            ax[1][0].plot(times, target_altitude, '--', color = colors[i], label = f'Target: {target.name}')
        
        if i == 0:
            ax[1][0].set_title(f'Target Altitude Throughout Eclipse {eclipse_num}')
        else:
            ax[1][0].set_title(f"Targets' Altitude Throughout Eclipse {eclipse_num}")
        ax[1][0].axhline(y = self.satellite.earth_constraint, color = 'firebrick', label = f'Altitude (Earth) Constraint: {self.satellite.earth_constraint:.2f}')
        ax[1][0].legend(loc = 'best')
        ax[1][0].set_xlabel('Time in UTC')
        ax[1][0].set_ylabel('Target Altitude in Degrees')
        ax[1][0].tick_params(axis='x', rotation = 25)
        ax[1][0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))
        ax[1][0].grid(alpha = 0.3)

        # Plot the moon's altitudes
        moon_altitude = self.Helpers.inclusive_slice(self.satellite.moon_altitudes, eclipse_start, eclipse_end)
        ax[1][1].plot(times, moon_altitude, '--', color = 'yellowgreen')
        ax[1][1].axhline(y = self.satellite.moon_constraint, color = 'olivedrab', label = f'Altitude (Moon) Constraint: {self.satellite.moon_constraint:.2f}')
        ax[1][1].set_title(f'Moon Altitude Throughout Eclipse {eclipse_num}')
        ax[1][1].legend(loc = 'best')
        ax[1][1].set_xlabel('Time in UTC')
        ax[1][1].set_ylabel('Moon Altitude in Degrees')
        ax[1][1].grid(alpha = 0.3)
        ax[1][1].tick_params(axis='x', rotation = 25)
        ax[1][1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))

        # Plot the operations schedule
        colors_operations = ['darkgoldenrod', 'firebrick', 'red', 'mediumseagreen', 'black', 'steelblue', 'tab:orange', 'khaki', 'khaki']

        ax[0, 0].plot(times, eclipse_schedule, drawstyle='steps-mid')
        for i, status in enumerate(self.MissionStatus):
            ax[0, 0].plot(times[eclipse_schedule == status.value], eclipse_schedule[eclipse_schedule == status.value], marker='s', linestyle='', color = colors_operations[i])
        if len(eclipse.targets_names) > 0:
            ax[0, 0].plot([], [], label=f'Target 1 = {eclipse.targets_names[0]}. Exp Time = {eclipse.targets_exp_times[0]}s', color='firebrick')
            if eclipse.targets_exp_times[0] != np.sum(eclipse_schedule == self.MissionStatus.TARGET1.value) * self.satellite.time_step_sec:
                raise ValueError('The target exposure time does not match the number of slots allocated to the target')
            if np.any(eclipse_schedule == self.MissionStatus.TARGET2.value):
                ax[0, 0].plot([], [], label=f'Target 2 = {eclipse.targets_names[1]}. Exp Time = {eclipse.targets_exp_times[1]}s', color='darkgoldenrod')
                if eclipse.targets_exp_times[1] != np.sum(eclipse_schedule == self.MissionStatus.TARGET2.value) * self.satellite.time_step_sec:
                    raise ValueError('The target exposure time does not match the number of slots allocated to the target')
        ax[0, 0].legend(loc='best')
        ax[0, 0].set_yticks([status.value for status in self.MissionStatus])
        ax[0, 0].set_yticklabels([status.name for status in self.MissionStatus])
        ax[0, 0].tick_params(axis='x', rotation = 25)
        ax[0, 0].grid()
        ax[0, 0].set_xlabel('Time [UTC]')
        ax[0, 0].set_ylabel('Visibility Status')
        ax[0, 0].set_title(f'Eclipse {eclipse_num} Operations Schedule')
        ax[0, 0].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))

        # Plot the groundtrack
        ax[0][1] = plt.subplot(2, 2, 2, projection=ccrs.PlateCarree())
        ax[0][1].coastlines()

        # Plot the groundtrack
        plot_lat, plot_lon = self._insert_plot_nans(self.Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end), self.Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end))
        ax[0][1].plot(plot_lon, plot_lat, color = self.MissionStatus.plot_color(), linewidth = 1)

        # Plot the SAA groundtrack coordinates and area
        saa_lat_area, saa_lon_area = self._insert_plot_nans(self.satellite.saa_latitudes_area, self.satellite.saa_longitudes_area)
        ax[0][1].plot(saa_lon_area, saa_lat_area, color = self.MissionStatus.plot_color(self.MissionStatus.SAA.value), linewidth = 6)

        saa_path = Path(list(zip(self.satellite.saa_longitudes_area, self.satellite.saa_latitudes_area)))
        in_saa = saa_path.contains_points(list(zip(plot_lon, plot_lat)))

        saa_lat = plot_lat[in_saa]
        saa_lon = plot_lon[in_saa]
        ax[0][1].plot(saa_lon, saa_lat, color = self.MissionStatus.plot_color(self.MissionStatus.SAA.value), linewidth = 6)

        # Plot the polar keepout (pk) coordinates
        pk_upper_lim = 90 - self.satellite.polar_constraint
        pk_latitude_upper = plot_lat[plot_lat > pk_upper_lim]
        pk_longitude_upper = plot_lon[plot_lat > pk_upper_lim]
        ax[0][1].plot(pk_longitude_upper, pk_latitude_upper, color = self.MissionStatus.plot_color(self.MissionStatus.POLAR.value), linewidth = 6)

        pk_lower_lim = -90 + self.satellite.polar_constraint
        pk_latitude_lower = plot_lat[plot_lat < pk_lower_lim]
        pk_longitude_lower = plot_lon[plot_lat < pk_lower_lim]
        ax[0][1].plot(pk_longitude_lower, pk_latitude_lower, color = self.MissionStatus.plot_color(self.MissionStatus.POLAR.value), linewidth = 6)

        # Plot the ground station accesses
        donwlink_schedule = self.Helpers.inclusive_slice(self.get_schedule_by_name("Ground Stations Schedule").status, eclipse_start, eclipse_end)
        gs_lat, gs_lon = self._insert_plot_nans(plot_lat[donwlink_schedule], plot_lon[donwlink_schedule])
        ax[0][1].plot(gs_lon, gs_lat, color = self.MissionStatus.plot_color(self.MissionStatus.DOWNLINK.value), linewidth = 6)

        # Plot pointing
        pointing_schedule = final_operations_in_eclipse == self.MissionStatus.POINTING.value
        pointing_lat, pointing_lon = self._insert_plot_nans(plot_lat[pointing_schedule], plot_lon[pointing_schedule])
        ax[0][1].plot(pointing_lon, pointing_lat, color = self.MissionStatus.plot_color(self.MissionStatus.POINTING.value), linewidth = 6)

        # Plot target 1
        target1_schedule = final_operations_in_eclipse == self.MissionStatus.TARGET1.value
        target1_lat, target1_lon = self._insert_plot_nans(plot_lat[target1_schedule], plot_lon[target1_schedule])
        ax[0][1].plot(target1_lon, target1_lat, self.MissionStatus.plot_color(self.MissionStatus.TARGET1.value), linewidth = 6)

        # Plot target 2
        target2_schedule = final_operations_in_eclipse == self.MissionStatus.TARGET2.value
        target2_lat, target2_lon = self._insert_plot_nans(plot_lat[target2_schedule], plot_lon[target2_schedule])
        ax[0][1].plot(target2_lon, target2_lat, color = self.MissionStatus.plot_color(self.MissionStatus.TARGET2.value), linewidth = 6)

        # Plot charging
        charging_schedule = final_operations_in_eclipse == self.MissionStatus.CHARGING.value
        charging_lat, charging_lon = self._insert_plot_nans(plot_lat[charging_schedule], plot_lon[charging_schedule])
        ax[0][1].plot(charging_lon, charging_lat, color = self.MissionStatus.plot_color(self.MissionStatus.CHARGING.value), linewidth = 6)

        # Plot downtime
        downtime_schedule = final_operations_in_eclipse == self.MissionStatus.DOWNTIME.value
        downtime_lat, downtime_lon = self._insert_plot_nans(plot_lat[downtime_schedule], plot_lon[downtime_schedule])
        ax[0][1].plot(downtime_lon, downtime_lat, color = self.MissionStatus.plot_color(self.MissionStatus.DOWNTIME.value), linewidth = 6)

        ax[0][1].set_xlim([min(plot_lon) - 15, max(plot_lon) + 15])
        ax[0][1].set_ylim([min(plot_lat) - 15, max(plot_lat) + 15])
        ax[0][1].grid(alpha = 0.3)
        ax[0, 1].xaxis.set_major_formatter(LongitudeFormatter())
        ax[0, 1].yaxis.set_major_formatter(LatitudeFormatter())
        ax[0, 1].set_title(f'Eclipse {eclipse_num} Groundtrack')

        plt.suptitle(f"Eclipse {eclipse_num} Summary")
        plt.tight_layout()
        plt.show()

        # Create the printing dictionary
        print_dict = {}
        print_dict['Eclipse Number'] = eclipse_num
        print_dict['Eclipse Start'] = self.satellite.times[eclipse.schedule_indices[0]].utc_datetime().strftime('%m-%d-%y, %H:%M:%S')
        print_dict['Eclipse End'] = self.satellite.times[eclipse.schedule_indices[1]].utc_datetime().strftime('%m-%d-%y, %H:%M:%S')
        print_dict['Eclipse Duration (min)'] = (eclipse_end - eclipse_start) * self.satellite.time_step_sec / 60
        if len(eclipse.targets_names) == 1:
            print_dict['Target'] = eclipse.targets_names[0]
            print_dict['Target Exposure Time (s)'] = eclipse.targets_exp_times[0]
            print_dict['Lat of Start of Exposure'] = self.satellite.latitudes[eclipse.schedule_indices[0] + (eclipse.operations.status == self.MissionStatus.TARGET1)[0]]
            print_dict['Lon of Start of Exposure'] = self.satellite.longitudes[eclipse.schedule_indices[0] + (eclipse.operations.status == self.MissionStatus.TARGET1)[0]]
        elif len(eclipse.targets_names) == 2:
            for i in range(2):
                print_dict[f'Target {i}'] = eclipse.targets_names[i]
                print_dict[f'Target {i} Exposure Time'] = eclipse.targets_exp_times[i]
                print_dict[f'Lat/Lon of Start of Exposure {i}'] = self.satellite.times.utc_datetime()[eclipse.schedule_indices[0] + (eclipse.operations.status == (i - 1))[i]]
        else:
            print_dict['No Targets Available in Eclipse'] = 'N/A'

        
        # Calculate the maximum key length
        max_key_length = max(len(key) for key in print_dict.keys())

        # Print the dictionary with aligned columns
        for key, value in print_dict.items():
            print(f"{key:<{max_key_length}} : {value}")

    def plot_target_availability_in_mission(self, target_name: str):

        # Find the target
        target = self.science_mission.get_target_by_name(target_name)

        # Get the schedule for the target in the mission
        target_schedule = target.schedule.status

        # Get the availability in seconds for every eclipse
        eclipses_numbers = []
        availability_in_seconds = []
        for eclipse_num, eclipse in enumerate(self.science_mission.eclipses):
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[-1]
            target_schedule_in_eclipse = target_schedule[eclipse_start: eclipse_end + 1]
            eclipses_numbers.append(f'{eclipse_num}')
            availability_in_seconds.append(np.sum(target_schedule_in_eclipse == 1) * self.satellite.time_step_sec)

        # Plot the schedule
        plt.bar(eclipses_numbers, availability_in_seconds)
        plt.legend(loc = 'best')
        plt.xlabel('Eclipse Number')
        plt.ylabel('Visibility in Seconds')
        plt.title(f"{target_name}'s Visibility Throughout the Mission")
        plt.grid(alpha = 0.3)
        plt.show()

    def plot_satellite_altitude(self):

        # Get the times
        times = self.satellite.times.utc_datetime()

        # Get the times and altitudes
        altitudes_in_km = self.satellite.altitudes/1000

        # Plot the altitudes
        plt.plot(times, altitudes_in_km, '--', color = 'silver')

        # Plot the median and mean
        plt.axhline(y = np.median(altitudes_in_km), label = f'Median: {np.median(altitudes_in_km):.2f} km', color = 'firebrick')
        plt.axhline(y = np.mean(altitudes_in_km), label = f'Mean: {np.mean(altitudes_in_km):.2f} km', color = 'olivedrab')

        plt.title(f"{self.satellite.satellite_name}'s Altitude Throughout Plan")
        plt.ylabel('Altitude in km')
        plt.xlabel('Time in UTC')
        plt.xticks(rotation = 45)
        plt.legend(loc = 'upper left')
        date_format = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
        plt.gca().xaxis.set_major_formatter(date_format)
        plt.grid(alpha = 0.3)
        plt.show()






        



    def _plot_satellite_positions(self) -> None:
        """
        Plot the positions of the satellite over the specified time interval.
        """
        # Initialize the plot
        plt.figure(figsize=(12, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.stock_img()
        ax.coastlines()

        # Plot the groundtrack
        plot_lat, plot_lon = self._insert_plot_nans(self.satellite.latitudes, self.satellite.longitudes)
        ax.plot(plot_lon, plot_lat, color = 'slategrey', linewidth = 1)

        # Plot the SAA area
        saa_lat_area, saa_lon_area = self._insert_plot_nans(self.satellite.saa_latitudes_area, self.satellite.saa_longitudes_area)
        ax.plot(saa_lon_area, saa_lat_area, color = 'tab:red', linewidth = 3)

        # Plot the SAA groundtrack coordinates
        saa_lat, saa_lon = self._insert_plot_nans(self.satellite.saa_latitudes, self.satellite.saa_longitudes)
        ax.plot(saa_lon, saa_lat, color = 'tab:red', linewidth = 3)

        # Plot the polar keepout (pk) coordinates
        pk_upper_lim = 90 - self.satellite.polar_constraint
        pk_latitude_upper = self.satellite.latitudes[self.satellite.latitudes > pk_upper_lim]
        pk_longitude_upper = self.satellite.longitudes[self.satellite.latitudes > pk_upper_lim]
        pk_latitude_upper, pk_longitude_upper = self._insert_plot_nans(pk_latitude_upper, pk_longitude_upper)
        ax.plot(pk_longitude_upper, pk_latitude_upper, color = 'tab:red', linewidth = 3)

        pk_lower_lim = -90 + self.satellite.polar_constraint
        pk_latitude_lower = self.satellite.latitudes[self.satellite.latitudes < pk_lower_lim]
        pk_longitude_lower = self.satellite.longitudes[self.satellite.latitudes < pk_lower_lim]
        pk_latitude_lower, pk_longitude_lower = self._insert_plot_nans(pk_latitude_lower, pk_longitude_lower)
        ax.plot(pk_longitude_lower, pk_latitude_lower, color = 'tab:red', linewidth = 3)
        
        # Plot the ground station accesses
        donwlink_schedule = self.get_schedule_by_name("Ground Stations Schedule")
        gs_lat, gs_lon = self._insert_plot_nans(self.satellite.latitudes[donwlink_schedule.status], self.satellite.longitudes[donwlink_schedule.status])                
        ax.plot(gs_lon, gs_lat, color = 'orange', linewidth = 3)

        plt.title('Groundtrack for SPRITE on Sample Day', fontsize = 20)
        plt.show()
        plt.savefig(fname = './Plots/Groundtrack.png', dpi = 100)

    def _insert_plot_nans(self, lat, lon) -> tuple:
        """
        Insert NaNs for wrap-around
        """
        # Set the lat and lon lims for inserting nans
        lon_lim = 5
        lat_lim = 5

        # Calculate the differences between consecutive lat/lon points
        lat_diff = np.diff(lat)
        lon_diff = np.diff(lon)

        # Identify where the gaps should be introduced to allow for line plotting
        gap_indices = np.where((np.abs(lon_diff) > lon_lim) | (np.abs(lat_diff) > lat_lim))[0]

        # Insert NaNs at the appropriate positions to break the line in the plot
        lon_split = np.insert(lon, gap_indices + 1, np.nan)
        lat_split = np.insert(lat, gap_indices + 1, np.nan)
        
        return lat_split, lon_split

    def __repr__(self) -> str:
        """
        TODO: CHANGE THE OUTPUT TO SOMETHING USEFUL
        """
        return (f"CubeSatMission(science_mission={self.science_mission}, "
                f"mission_config={self.mission_config}, "
                f"satellite={self.satellite}, "
                f"ground_stations={self.ground_stations}, "
                f"visibilities={self.schedules}, "
                f"operations={self.operations})")