
"""
CubeSat Mission Planner
=======================

A comprehensive mission planning and scheduling system for CubeSat operations,
optimizing target observations during eclipse periods while accounting for
various operational constraints.

Author: Sebastian Escobar
License: BSD 3-Clause
"""

from typing import List, Type, Dict
from Utilities.Helpers import Helpers
from Utilities.MissionStatus import MissionStatus
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
import json
import os
from collections import defaultdict
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
from itertools import groupby
from collections import Counter, OrderedDict
import seaborn as sns
import pandas as pd
from datetime import datetime, timedelta
from matplotlib import gridspec

from skyfield.api import Star
# import time
import datetime
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

    def __init__(self, excel_file_path: str = None,
                 program_options: Dict[str, bool] = None):

        # Initialize a new CubeSatMission object
        self.target_av_check = program_options['Target Availability Check']
        self.survey_av_check = program_options['Survey Availability Check']
        self.pointing_debug = program_options['Pointing Debug']
        self.observe_targets = program_options['Observe Targets']
        self.write_json = program_options['Write JSON File']
        self.json_file_directory = program_options['JSON File Directory']

        self.schedules = []
        self._create_mission_config(excel_file_path)
        self._print_startup_message()
        self._create_satellite()
        self._create_ground_stations()
        self._create_science_mission()
        self._create_operations()
        if self.target_av_check:
            self._display_target_availability()
        if self.survey_av_check:
            self._display_survey_availability()
        self._create_commands_list(write_json=self.write_json) #UNCOMMENT ME 
        # self.plot_battery_charge_plot()
        self.plot_target_completion()
        self.get_data_storage_plot()
        # self.plot_mission_overview()

        self._print_mission_summary()

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
    
    def _print_startup_message(self):
        print("CubeSat Mission has started...")
        print(f"Satellite Name: {self.mission_config.plan_info['Satellite Name'].values[0]}")
        start_time = self.mission_config.plan_info['Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0]
        end_time = self.mission_config.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0]
        if start_time >= end_time:
            start_str = pd.Timestamp(start_time).strftime('%Y-%m-%d %H:%M:%S UTC')
            end_str = pd.Timestamp(end_time).strftime('%Y-%m-%d %H:%M:%S UTC')
            raise ValueError(f"Simulation start time ({start_str}) must be before end time ({end_str}).")
        duration = (end_time - start_time).astype('timedelta64[D]').astype(float)
        print(f"Simulation Start UTC Time: {start_time}")
        print(f"Simulation End UTC Time: {self.mission_config.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0]}")
        print(f"Simulation Time Step: {self.mission_config.plan_info['Timestep [sec]'].values[0]} seconds")
        print(f"Simulation Duration: {duration} days")
        print(f"Number of Targets: {len(self.mission_config.targets_info['Target'].values)}")

    def _print_mission_summary(self):

        mission_schedule = self.get_operation_by_name("Final Operations Schedule").status
        print("CubeSat Mission has completed...")
        num_exposure_cmds = sum(1 for key, _ in groupby(mission_schedule) if key == MissionStatus.TARGET1.value)
        print(f"Number of Continuous Exposure Commands: {num_exposure_cmds}")
        num_pointing_cmds = sum(1 for key, _ in groupby(mission_schedule) if key == MissionStatus.SLEWING.value)
        print(f"Number of Pointing Commands: {num_pointing_cmds}")
        num_downlink_cmds = sum(1 for key, _ in groupby(mission_schedule) if key == MissionStatus.DOWNLINK.value)
        print(f"Number of Downlink Commands: {num_downlink_cmds}")

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

    def _create_science_mission(self) -> ScienceMission:
        """
        Create a new ScienceMission object based on the data in the plan_info DataFrame.
        
        Returns
        -------
        ScienceMission
            A new ScienceMission object with the data from the plan_info DataFrame.
        """
        self.science_mission = None

        # Create surveys
        surveys = self._create_surveys()

        # Create visibility schedules and targets and assign them to surveys
        master_targets_list = self._create_targets(surveys)

        # Create eclipses
        eclipse_objects = self._create_eclipses(surveys)
        print(f"Number of eclipses: {len(eclipse_objects)}")

        self.science_mission = ScienceMission(master_targets_list, eclipse_objects, surveys)
        return self.science_mission

    def _create_surveys(self) -> List[Survey]:
        """
        Create a list of Survey objects based on the data in the survey_info DataFrame.
        
        Returns
        -------
        List[Survey]
            A list of Survey objects with the data from the survey_info DataFrame.
        """
        # Get the survey information
        survey_info = self.mission_config.survey_info
        surveys_data = zip(survey_info['Survey'].values, survey_info['N Targets'].values,
                           survey_info['Pointings Per Target'].values, survey_info['ExpTime Per Pointing [s]'].values,
                           survey_info['ExpTime Per Target [s]'].values, survey_info['Total ExpTime'].values,
                           survey_info['Obs Mode'].values, survey_info['Repeat Targets'].values,
                           survey_info['SurveyPriority'].values, survey_info['Minimum ExpTime [s]'].values)
        
        # Sort surveys_data based on SurveyPriority
        sorted_surveys_data = sorted(surveys_data, key=lambda x: x[8])  # x[8] is the SurveyPriority

        # Create the survey objects
        surveys = []
        for survey_data in sorted_surveys_data:
            survey_name, n_targets, pntngs_per_target, exp_time_per_pntng, exp_time_per_target, total_exp_time, obs_mode, repeat_targets, priority, min_exp_time = survey_data
            surveys.append(Survey(survey_name, n_targets, [], pntngs_per_target, 
                                  exp_time_per_pntng, min_exp_time, exp_time_per_target, 
                                  total_exp_time, repeat_targets, obs_mode))
            
        return surveys

    def _create_targets(self, surveys: List[Survey]) -> List[Target]:
        """
        Create a list of Target objects based on the data in the target_info DataFrame.
        
        Returns
        -------
        List[Target]
            A list of Target objects with the data from the target_info DataFrame.
        """
        # observer = self.satellite.earth_ephemeris + self.satellite.wgs84.latlon(self.satellite.latitudes, self.satellite.longitudes, self.satellite.altitudes)
        # # Calculate the times at which the sun is invisible
        # sun_apparent = observer.at(self.satellite.times).observe(self.satellite.sun_ephemeris)
        # alt_sun, _, _ = sun_apparent.apparent().altaz()
        # # sun_invisible = alt_sun.degrees < self.satellite.sun_constraint
        # sun_invisible = alt_sun.degrees < 30
        # self.satellite.sun_altitudes = alt_sun.degrees

        # Calculate the visibilities that play a role in calculating target visibility
        saa_keepout_schedule = np.isin(self.satellite.latitudes, self.satellite.saa_latitudes)
        polar_keepout_schedule = (
            (self.satellite.latitudes > (90 - self.satellite.polar_constraint)) |
            (self.satellite.latitudes < (-90 + self.satellite.polar_constraint))
        )
        charging_schedule = self.satellite.earth_satellite.at(self.satellite.times).is_sunlit(self.satellite.ephemeris)

        self.schedules.append(Schedule("SAA Keepout Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, saa_keepout_schedule,
                                          {True: "In SAA", False: "Not in SAA"}))
        self.schedules.append(Schedule("Polar Keepout Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, polar_keepout_schedule,
                                          {True: "In Polar Keepout", False: "Not in Polar Keepout"}))
        self.schedules.append(Schedule("Charging Schedule", self.satellite.start_time,
                                          self.satellite.end_time, self.satellite.time_step_sec,
                                          self.satellite.times, charging_schedule,
                                          {True: "Charging", False: "Not Charging"}))
                                          
        # Calculate the targets' visibilities and create the target objects
        targets_info = self.mission_config.targets_info
        targets_data = zip(targets_info['Target'].values, targets_info['Pointing'], targets_info['HH'].values, targets_info['MM'].values,
                           targets_info['SS'].values, targets_info['dd'].values, targets_info['mm'].values,
                           targets_info['ss'].values, targets_info['Rotation Angle'].values, targets_info['Base Priority'].values,
                           targets_info['Survey'].values)

        # Sort targets_data based on Base Priority
        sorted_targets_data = sorted(targets_data, key=lambda x: x[9])  # x[9] is the Base Priority
        master_targets_list = []
        survey_names = [survey.name for survey in surveys]

        # Calculate the times at which the moon is invisible
        observer = self.satellite.earth_ephemeris + self.satellite.wgs84.latlon(self.satellite.latitudes, self.satellite.longitudes, self.satellite.altitudes)
        moon_apparent = observer.at(self.satellite.times).observe(self.satellite.moon_ephemeris)
        alt_moon, _, _ = moon_apparent.apparent().altaz()
        moon_invisible = alt_moon.degrees < self.satellite.moon_constraint
        self.satellite.moon_altitudes = alt_moon.degrees
        
        for target_data in sorted_targets_data:
            target_name, ptng, ra_hr, ra_min, ra_sec, dec_deg, dec_min, dec_sec, rotation_angle, priority, target_survey = target_data

            # Create the skyfield target object
            target_skyfield_object = Star(ra_hours=(ra_hr, ra_min, ra_sec), dec_degrees=(dec_deg, dec_min, dec_sec))
            
            # Get the target visibility constraints
            apparent = observer.at(self.satellite.times).observe(target_skyfield_object)
            alt, _, _ = apparent.apparent().altaz()
            visible_times = (90 - alt.degrees) < self.satellite.earth_constraint
            
            # Create the target schedule
            target_schedule = visible_times & ~saa_keepout_schedule & ~polar_keepout_schedule & ~charging_schedule & moon_invisible
            # target_schedule = visible_times & ~saa_keepout_schedule & ~polar_keepout_schedule & sun_invisible & moon_invisible
            target_schedule_object = Schedule(str(target_name) + '_' + str(ptng), self.satellite.start_time, self.satellite.end_time,
                                            self.satellite.time_step_sec, self.satellite.times, target_schedule,
                                            {True: "Visible", False: "Not Visible"})
            
            # Create the target object and store it in the survey
            target_object = Target(str(target_name) + '_' + str(ptng), target_skyfield_object, rotation_angle, priority, 0, target_schedule_object, alt.degrees)
            master_targets_list.append(target_object)
            target_survey_index = survey_names.index(target_survey)
            survey = surveys[target_survey_index]
            survey.targets.append(target_object)
        
        return master_targets_list

    def _create_eclipses(self, surveys: List[Survey]) -> List[Eclipse]:
        """
        Create a list of Eclipse objects based on the data in the eclipse_info DataFrame.
        
        Returns
        -------
        List[Eclipse]
            A list of Eclipse objects with the data from the eclipse_info DataFrame.
        """
        # Create the eclipse schedules based on the charging schedule
        overall_eclipse_schedule = ~self.get_schedule_by_name("Charging Schedule").status
        
        # Get the start and end indices of contiguous ones (start and ends are inclusive)
        is_one = overall_eclipse_schedule == 1
        eclipse_starts = np.where(np.diff(np.concatenate(([0], is_one.astype(int)))) == 1)[0]
        eclipse_ends = np.where(np.diff(np.concatenate((is_one.astype(int), [0]))) == -1)[0] - 1

        # Create the Eclipse objects
        eclipse_objects = []

        for i, (start, end) in enumerate(zip(eclipse_starts, eclipse_ends)):
            targets_available = {}

            # Get the indices in this chunk and the start and end. Have to add 1 to the end index to include it
            eclipse_schedule = Helpers.inclusive_slice(overall_eclipse_schedule, start, end)
            eclipse_schedule = ~eclipse_schedule # Flip the schedule to have it be all zeros (standard status)

            # Get the times of the eclipse
            start_time = self.satellite.times[start]
            end_time = self.satellite.times[end]
            eclipse_times = Helpers.inclusive_slice(self.satellite.times, start, end)

            operations = Schedule("Operations", start_time, end_time,
                                  self.satellite.time_step_sec, eclipse_times, eclipse_schedule,
                                  MissionStatus)
            
            for survey in surveys:
                for target in survey.targets:
                    target_eclipse_schedule = Helpers.inclusive_slice(target.schedule.status, start, end)

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

        return eclipse_objects

    def _display_target_availability(self):

        # Create a dictionary where the key is the target name and the value is the exposure time in seconds
        target_dict = {target.name: 0 for target in self.science_mission.master_target_list}

        # Get the exposure times for each target
        # for eclipse in self.science_mission.eclipses:
        #     for target_name, exposure_time in eclipse.targets_available.items():
        #         target_dict[target_name] += float(np.sum(exposure_time)) * self.satellite.time_step_sec / 60
        for target in self.science_mission.master_target_list:
            target_dict[target.name] += float(np.sum(target.schedule.status)) * target.schedule.time_step_sec / 60


        # Sort the dictionary by exposure time
        sorted_targets = dict(sorted(target_dict.items(), key=lambda item: item[1], reverse=True))

        # Print the target names and exposure times
        max_key_length = max(len(key) for key in sorted_targets.keys())
        print()
        print('------- Target Availability in Minutes -------')
        for key, value in sorted_targets.items():
            print(f"{key:<{max_key_length}} : {value:.2f}")

    def _display_survey_availability(self):

        # Create a dictionary where the key is the survey name and the value is the exposure time in seconds
        survey_dict = {survey.name: 0 for survey in self.science_mission.surveys}

        # Get the exposure times for each survey
        for eclipse in self.science_mission.eclipses:
            for target_name, exposure_time in eclipse.targets_available.items():
                survey_dict[self.science_mission.get_survey_of_target(target_name).name] += float(np.sum(exposure_time)) * self.satellite.time_step_sec / 60

        # Sort the dictionary by exposure time
        sorted_surveys = dict(sorted(survey_dict.items(), key=lambda item: item[1], reverse=True))

        # Print the survey names and exposure times
        max_key_length = max(len(key) for key in sorted_surveys.keys())
        print()
        print('------- Survey Availability in Minutes -------')
        for key, value in sorted_surveys.items():
            print(f"{key:<{max_key_length}} : {value:.2f}")

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
                                        self.satellite.time_step_sec, self.satellite.times, operations_schedule_bp, MissionStatus))

        if self.observe_targets:
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
                                self.satellite.time_step_sec, self.satellite.times, operations_schedule_ap, MissionStatus))

    def _create_commands_list(self, write_json):
        # Initialize the commands list
        commands_list = CommandList()
        
        # Get the indices of the changes in the operations schedule
        operations_schedule = self.get_operation_by_name("Final Operations Schedule").status
        
        # Use vectorized operations for faster processing
        status_array = np.array(operations_schedule)
        diffs = np.diff(status_array)
        change_indices = np.where(diffs != 0)[0] + 1  # 'after' index adjustment
        change_indices = np.concatenate(([0], change_indices))  # Include the starting index
        
        # Get the net energy dictionary
        energy_dict = defaultdict(float)
        for key, value in Helpers.get_energy_dict(self.mission_config).items():
            if isinstance(value, (int, float)):
                energy_dict[key] = value
        
        # Get the times
        times = self.satellite.times.utc_datetime()
        
        # Pre-compute durations between adjacent indices for speed
        durations = []
        for j in range(len(change_indices) - 1):
            start_idx = change_indices[j]
            end_idx = change_indices[j + 1]
            durations.append(times[end_idx] - times[start_idx])
        
        # Handle the last duration (use a default if needed)
        if len(change_indices) > 0:
            last_idx = change_indices[-1]
            if last_idx < len(times) - 1:
                durations.append(times[-1] - times[last_idx])
            else:
                durations.append(datetime.timedelta(minutes=30))  # Default duration
        
        # Count passovers for comments
        boulder_passovers = 0
        ncu_passovers = 0
        wallops_passovers = 0
        
        # Collection for frame IDs
        frame_ids = []
        
        # Loop through the changes in the operations schedule
        for j, index in enumerate(change_indices):
            # Get the time of the action
            action_time = times[index]
            
            # Get the duration of the action
            action_duration = durations[j] if j < len(durations) else datetime.timedelta(minutes=30)
            action_duration_min = datetime.timedelta(minutes=action_duration.total_seconds() / 60)
            
            # Get the key of the action
            status_value = operations_schedule[index]
            action_key = MissionStatus.get_key(operations_schedule[index])
            
            # Calculate energy value
            energy_value = energy_dict[action_key] * action_duration.total_seconds()

            # Determine if the action is inside an eclipse
            action_inside_eclipse, action_eclipse_num = Helpers.is_inside_eclipse(self.satellite, self.science_mission.eclipses, action_time)
            
            exposure_type = None
            if action_inside_eclipse:
                eclipse = self.science_mission.eclipses[action_eclipse_num]
                if action_key == 'TARGET1':
                    # action_key = eclipse.targets_names[0]
                    target_name = eclipse.targets_names[0]
                    action_key = f"TARGET1: {target_name}"
                    survey = self.science_mission.get_survey_of_target(target_name)
                    exposure_type = survey.obs_mode
                elif action_key == 'TARGET2':
                    # action_key = eclipse.targets_names[1]
                    target_name = eclipse.targets_names[1]
                    action_key = f"TARGET2: {target_name}"
                    survey = self.science_mission.get_survey_of_target(target_name)
                    exposure_type = survey.obs_mode
            
            # Create the action text
            action_text = f'{action_key} for {action_duration_min} min'
            
            # Get the next action key
            if action_key == 'SLEWING' and j + 1 < len(change_indices):
                next_action_key = MissionStatus.get_key(operations_schedule[change_indices[j + 1]])
                # print(f"Action: {action_key}, Next Action: {next_action_key}")
                # if next_action_key in ['TARGET1', 'TARGET2']:
                # if "TARGET1" in next_action_key or "TARGET2" in next_action_key:
                if any(target in next_action_key for target in ["TARGET1", "TARGET2"]):
                    next_action_time = times[change_indices[j + 1]]
                    next_action_inside_eclipse, next_action_eclipse_num = Helpers.is_inside_eclipse(self.satellite, self.science_mission.eclipses, next_action_time)
                    next_eclipse = self.science_mission.eclipses[next_action_eclipse_num]
                    next_action_key = next_eclipse.targets_names[0]

                # # Determine if the next action is inside an eclipse
                # next_action_time = times[change_indices[j + 1]]
                # next_action_inside_eclipse, next_action_eclipse_num = Helpers.is_inside_eclipse(self.satellite, self.science_mission.eclipses, next_action_time)
                # print(f"Action: {action_key}, Next Action: {next_action_inside_eclipse}")
                # # Get the next action key
                # if next_action_inside_eclipse:
                #     next_eclipse = self.science_mission.eclipses[next_action_eclipse_num]
                #     if action_key == 'TARGET1':
                #         next_action_key = next_eclipse.targets_names[0]
                #     elif action_key == 'TARGET2':
                #         next_action_key = next_eclipse.targets_names[1]
                    # print(f"Next action key: {next_action_key}")
            else:
                next_action_key = None


            # Generate command JSON based on action type
            action_time_index = index
            command_json = self._create_command_json(action_key, action_time, action_duration_min, j, exposure_type, action_time_index = action_time_index, next_action_key = next_action_key)

            # Track passovers
            # if "BOULDER PASSOVER" in action_key.upper():
            #     boulder_passovers += 1
            # elif "NCU PASSOVER" in action_key.upper():
            #     ncu_passovers += 1
            # elif "WALLOPS PASSOVER" in action_key.upper():
            #     wallops_passovers += 1
                
            # # Track frame IDs if this is a CHANGE ID command
            # if command_json.get("command_type") == "CHANGE ID" and "ID" in command_json.get("args", {}):
            #     frame_ids.append(int(command_json["args"]["ID"]))
            
            # Create the action object
            action = ActionChunk(
                action_id=j,
                time=action_time,
                duration_min=action_duration_min,
                energy=energy_value,
                key=action_key,
                text=action_text,
                json=json.dumps(command_json) if command_json else None,  #json.dumps(command_json),  # Store JSON string representation
                in_eclipse=action_inside_eclipse,
                eclipse_num=action_eclipse_num, 
                exposure_type=exposure_type
            )
            
            # Add to the command list
            commands_list.addToTail(action)
        
        # # Generate sequence comments
        # if frame_ids:
        #     min_id = min(frame_ids)
        #     max_id = max(frame_ids)
        #     frame_id_range = f"{min_id}-{max_id}"
        # else:
        #     frame_id_range = "N/A"
            
        # comments = f"Sequence: 1x Bias (13) -> 1x Dark (7) -> 2x Science (15) -> 1x Dark (7) -> 1x Bias (13). "
        # comments += f"Frame IDs = {frame_id_range}. Boulder Passovers = {boulder_passovers}. "
        # comments += f"NCU Passover = {ncu_passovers}. Wallops Passovers = {wallops_passovers}."
        comments = ''
        # Create and save the JSON file
        json_data = self._generate_commands_json(commands_list, comments)
        
        if self.write_json:
            os.makedirs(self.json_file_directory, exist_ok=True)
            with open(os.path.join(self.json_file_directory, f"mission_commands_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.json"), 'w') as f:
                json.dump(json_data, f, indent=4)
        
        self.commands_list = commands_list
        return commands_list
    
    def _generate_commands_json(self, commands_list, comments=""):
        """
        Generate complete JSON structure from a commands list.
        
        Args:
            commands_list (CommandList): List of commands
            comments (str): Comments for the sequence
            
        Returns:
            dict: Complete JSON structure
        """
        # Get sequence start and end times
        sequence_start = commands_list.head_node.data.time if commands_list.head_node else datetime.datetime.now()
        sequence_end = commands_list.tail_node.data.time if commands_list.tail_node else (sequence_start + datetime.timedelta(hours=48))
        
        # Format times in DOY format
        start_str = sequence_start.strftime("%Y/%j-%H:%M:%S")
        end_str = sequence_end.strftime("%Y/%j-%H:%M:%S")
        
        # Create command sequence
        sequence = {
            "start_date": start_str,
            "end_date": end_str,
            "description": "",
            "comments": comments,
            "commands": []
        }
        
        # Add each command to the sequence
        current = commands_list.head_node
        while current:
            # Parse the JSON string back to a dictionary
            if isinstance(current.data.json, str):
                try:
                    command_json = json.loads(current.data.json)
                except (json.JSONDecodeError, TypeError):
                    # Create a new command if JSON parsing fails
                    command_json = self._create_command_json(current.data.key, current.data.time, current.data.duration_min, current.data.action_id, current.data.exposure_type)
            else:
                # Create a new command if JSON is not available
                command_json = self._create_command_json(current.data.key, current.data.time, current.data.duration_min, current.data.action_id, current.data.exposure_type)
            
            # Add command to sequence
            if command_json is not None:
                if isinstance(command_json, list):
                    for command in command_json:
                        sequence["commands"].append(command)
                else:
                    sequence["commands"].append(command_json)
            current = current.next_node
        
        # Create full JSON structure
        json_data = {
            "author": getattr(self, "author", "sebastian.escobar@lasp.colorado.edu"),
            "timestamp": datetime.datetime.now().strftime("%Y%m%dT%H%M%S"),
            "comments": f"Questions? Email {getattr(self, 'author', 'sebastian.escobar@lasp.colorado.edu')}",
            "storedCommands": [sequence]
        }
        
        return json_data

    def quaternion_from_axis_angle(self, axis, angle_rad):
        """Return quaternion from axis and angle (in radians). Format: [w, x, y, z]"""
        axis = axis / np.linalg.norm(axis)
        sin_half = np.sin(angle_rad / 2)
        return np.array([
            np.cos(angle_rad / 2),
            axis[0] * sin_half,
            axis[1] * sin_half,
            axis[2] * sin_half
        ])

    def quaternion_multiply(self, q1, q2):
        """Quaternion multiplication: q = q1 * q2. Inputs as [w, x, y, z]"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
    
    def get_pointing_quaternion(self, ra_deg, dec_deg, roll_deg):
        """
        Return the quaternion that rotates spacecraft +Z to point at (RA, Dec)
        and then applies a roll about that line of sight.
        
        Returns: quaternion as [w, x, y, z]
        """
        # Convert angles to radians
        ra = np.radians(ra_deg)
        dec = np.radians(dec_deg)
        roll = np.radians(roll_deg)

        # Step 1: Direction vector from RA/Dec
        pointing_vector = np.array([
            np.cos(dec) * np.cos(ra),
            np.cos(dec) * np.sin(ra),
            np.sin(dec)
        ])

        # Step 2: Rotate Z-axis to pointing_vector
        z_axis = np.array([0, 0, 1])
        cross_prod = np.cross(z_axis, pointing_vector)
        dot_prod = np.dot(z_axis, pointing_vector)

        if np.linalg.norm(cross_prod) < 1e-8:
            if dot_prod > 0:
                q_point = np.array([1.0, 0.0, 0.0, 0.0])  # Identity
            else:
                q_point = np.array([0.0, 1.0, 0.0, 0.0])  # 180° about X
        else:
            axis = cross_prod / np.linalg.norm(cross_prod)
            angle = np.arccos(np.clip(dot_prod, -1.0, 1.0))
            q_point = self.quaternion_from_axis_angle(axis, angle)

        # Step 3: Roll about pointing vector
        q_roll = self.quaternion_from_axis_angle(pointing_vector, roll)

        # Step 4: Compose roll * point
        q_final = self.quaternion_multiply(q_roll, q_point)
        return q_final

    def _create_command_json(self, action_key, action_time, action_duration_min, action_id, action_exposure_type=None, action_time_index=None, next_action_key=None):
        """
        Creates a command JSON object based on the action type.
        
        Args:
            action_key (str): The key identifying the action type
            action_time (datetime): The time of the action
            action_id (int): The action ID
            
        Returns:
            dict: Command JSON representation
        """
        # Format the UTC time
        # print(action_time, action_key)
        utc_time = action_time.strftime("%Y/%j-%H:%M:%S")  # DOY format

        if action_key == 'DOWNLINK':
            # Figure out which ground station to use
            for gs in self.ground_stations:
                gs_visibility = gs.visibility.status
                # Check if the ground station is visible at the action time
                # index_time = np.where(self.satellite.times == action_time)
                # print(gs.name, action_time_index, gs_visibility[action_time_index])
                if gs_visibility[action_time_index]:
                    gs_name = gs.name
                
            # print(f"NAME: {gs_name}")

            command = {
                "utc_time": utc_time
            }
            command["command_type"] = "placeholder"
            command["mnemonic"] = f"{gs_name} Passover"
            los_time = action_time + action_duration_min
            command["args"] = {
                "los_time": los_time.strftime("%Y/%j-%H:%M:%S")
            }
            return command
        
        elif action_key == 'SAA':
            command = {
                "utc_time": utc_time,
                "command_type": "placeholder",
                "mnemonic": "SAA",
                "args": {}
            }
            return command
        
        elif action_key == 'POLAR':
            command = {
                "utc_time": utc_time,
                "command_type": "placeholder",
                "mnemonic": "Polar Keepout",
                "args": {}
            }
            return command
    
        elif action_key == 'CHARGING':
            command = {
                "utc_time": utc_time,
                "command_type": "placeholder",
                "mnemonic": "Charging",
                "args": {}
            }
            return command
        
        elif action_key == 'SLEWING':
            if next_action_key not in [None, 'DOWNTIME', 'CHARGING', 'OBSERVING', 'SLEWING', 'DOWNLINK', 'SAA', 'POLAR']:  # Must be a science target
                # Get the target name
                target = self.science_mission.get_target_by_name(next_action_key)
                roll = target.rotation_angle
                dec = target.skyfield_object.dec.degrees
                ra = target.skyfield_object.ra._degrees

                # Get the pointing quaternion
                q = self.get_pointing_quaternion(ra, dec, roll)
                q_1 = q[1]
                q_2 = q[2]
                q_3 = q[3]
                q_4 = q[0]
                
            else:
                return None
            # phi = 
            # phi = roll * 0.5
            # theta = -1 * declination * 0.5  # Note: negative sign as in MATLAB code
            # psi = right_ascension * 0.5
            
            # # Compute quaternion components using cosd and sind functions
            # q_4 = cosd(psi) * cosd(theta) * cosd(phi) + sind(psi) * sind(theta) * sind(phi)
            # q_1 = cosd(psi) * cosd(theta) * sind(phi) - sind(psi) * sind(theta) * cosd(phi)
            # q_2 = cosd(psi) * sind(theta) * cosd(phi) + sind(psi) * cosd(theta) * sind(phi)
            # q_3 = sind(psi) * cosd(theta) * cosd(phi) - cosd(psi) * sind(theta) * sind(phi)

            # Create a list of commands
            commands = []

            # First command: HVPS standby 1 minute before slew
            commands.append({
                "utc_time": (action_time - datetime.timedelta(minutes=1)).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_DAC",
                "args": {
                    "STATE": "STANDBY"
                }
            })

            # Second command: HVPS standby 30 seconds before slew
            commands.append({
                "utc_time": (action_time - datetime.timedelta(seconds=30)).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_FIXED",
                "args": {
                    "STATE": "STANDBY"
                }
            })

            # Third command: Slew to the target attitude
            commands.append({
                "utc_time": utc_time,
                "command_type": "xb1",
                "mnemonic": "GOTO_ECI_ATTITUDE",
                "args": {
                    "PRI_CMD_DIR": 3.0,
                    "SEC_CMD_DIR": 1.0,
                    "Q_CMD_WRT_REF_1": q_1,
                    "Q_CMD_WRT_REF_2": q_2,
                    "Q_CMD_WRT_REF_3": q_3,
                    "Q_CMD_WRT_REF_4": q_4
                }
            })

            # Fourth command: HVPS observe 2 minutes after slew
            commands.append({
                "utc_time": (action_time + datetime.timedelta(minutes=2)).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_DAC",
                "args": {
                    "STATE": "OBSERV"
                }
            })

            # Fifth command: HVPS observe 2 minutes, 30 seconds after slew
            commands.append({
                "utc_time": (action_time + datetime.timedelta(minutes=2, seconds=30)).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_FIXED",
                "args": {
                    "STATE": "OBSERV"
                }
            })

            # Return the list of commands
            return commands

        elif action_key not in ['DOWNTIME', 'CHARGING', 'OBSERVING', 'SLEWING', 'DOWNLINK', 'SAA', 'POLAR']:  # Must be a science target
            # Create a list of commands
            commands = []

            # Create the science exposure command
            commands.append({
                "utc_time": utc_time,
                "command_type": "fsw",
                "mnemonic": "SCI_START",
                "args": {
                    "TYPE": action_exposure_type,
                    "TIME": action_duration_min.seconds,  # in seconds
                    "OBS_ID": action_id,
                    "end_utc_time": (action_time + action_duration_min).strftime("%Y/%j-%H:%M:%S"),
                }
            })

            # Have the HVPS go on standby again
            commands.append({
                "utc_time": (action_time + action_duration_min).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_FIXED",
                "args": {
                    "STATE": "STANDBY"
                }
            })

            commands.append({
                "utc_time": (action_time + action_duration_min + datetime.timedelta(seconds=30)).strftime("%Y/%j-%H:%M:%S"),
                "command_type": "fsw",
                "mnemonic": "HV_DAC",
                "args": {
                    "STATE": "STANDBY"
                }
            })

            # Return the list of commands
            return commands
        return None

        
        # # Set command type, mnemonic, and arguments based on action key
        # if action_key in ["TARGET1", "TARGET2"]:
            

        #     command["command_type"] = "fsw"
        #     command["mnemonic"] = "SCI_START"
        #     command["args"] = {
        #         "TYPE": ""
        #         # "TIME": 100000.0,  # Default for science targets
        #         # "NUM": 15.0 if "SCIENCE" in action_key else 10.0,
        #         # "TARGETID": 340.0,
        #         # "OPT1": 7.0,
        #         # "OPT2": 0.0,
        #         # "OPT3": 0.0,
        #         # "OPT4": 0.0,
        #         # "DARKSRC": 1.0,
        #         # "BIASSRC": 0.0,
        #         # "DST": 16.0
        #     }
        # # elif action_key == "BIAS":
        # #     command["command_type"] = "fsw"
        # #     command["mnemonic"] = "CCD"
        # #     command["args"] = {
        # #         "TIME": 0.0,
        # #         "NUM": 13.0,
        # #         "TARGETID": 0.0,
        # #         "OPT1": 7.0,
        # #         "OPT2": 0.0,
        # #         "OPT3": 0.0,
        # #         "OPT4": 0.0,
        # #         "DARKSRC": 1.0,
        # #         "BIASSRC": 0.0,
        # #         "DST": 16.0
        # #     }
        # # elif action_key == "DARK":
        # #     command["command_type"] = "fsw"
        # #     command["mnemonic"] = "CCD"
        # #     command["args"] = {
        # #         "TIME": 100000.0,
        # #         "NUM": 7.0,
        # #         "TARGETID": 255.0,
        # #         "OPT1": 7.0,
        # #         "OPT2": 0.0,
        # #         "OPT3": 0.0,
        # #         "OPT4": 0.0,
        # #         "DARKSRC": 1.0,
        # #         "BIASSRC": 0.0,
        # #         "DST": 16.0
        # #     }
        # # elif action_key == "ROTATE" or action_key == "DOWNLINK":
        # #     command["command_type"] = "xb1"
        # #     command["mnemonic"] = "ROTATE"
        # #     command["args"] = {
        # #         "PRI_CMD_DIR": 3.0,
        # #         "SEC_CMD_DIR": 1.0,
        # #         "Q_CMD_WRT_REF_1": 0.5810693332,
        # #         "Q_CMD_WRT_REF_2": 0.778188243,
        # #         "Q_CMD_WRT_REF_3": 0.1983378156,
        # #         "Q_CMD_WRT_REF_4": -0.1320742192
        # #     }
        # # elif action_key == "SET_ID":
        # #     command["command_type"] = "CHANGE ID"
        # #     command["mnemonic"] = "SET IF"
        # #     command["args"] = {
        # #         "ID": 5179.0 + action_id  # Incrementing from base ID
        # #     }
        # # elif "PASSOVER" in action_key.upper():
        # #     command["command_type"] = "placeholder"
        # #     command["mnemonic"] = action_key
            
        # #     # Add LOS time (10 minutes after AOS)
        # #     los_time = action_time + datetime.timedelta(minutes=10)
        # #     command["args"] = {
        # #         "los_time": los_time.strftime("%Y/%j-%H:%M:%S")
        # #     }
        # # else:
        # #     # Default for other actions
        # #     command["command_type"] = "placeholder"
        # #     command["mnemonic"] = action_key
        # #     command["args"] = {}
        
        # return command

    def _allocate_constraints(self, operations_schedule):
        """Allocate the constraints (SAA, Polar Keepout, Charging) in the operations schedule."""
        saa_schedule = self.get_schedule_by_name("SAA Keepout Schedule").status
        polar_schedule = self.get_schedule_by_name("Polar Keepout Schedule").status
        charging_schedule = self.get_schedule_by_name("Charging Schedule").status

        operations_schedule[saa_schedule] = MissionStatus.SAA.value
        operations_schedule[polar_schedule] = MissionStatus.POLAR.value
        operations_schedule[charging_schedule] = MissionStatus.CHARGING.value

    def _allocate_targets_and_update_eclipses(self, operations_schedule):
        """Allocate the availability of the targets and update the eclipses."""

        # Get the SAA and polar keepout schedule
        saa_schedule = self.get_schedule_by_name("SAA Keepout Schedule").status
        polar_keepout_schedule = self.get_schedule_by_name("Polar Keepout Schedule").status

        for eclipse in self.science_mission.eclipses:

            # Get the eclipse schedule
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            eclipse_schedule = Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end)

            # Get the eclipse SAA and polar keepout schedules
            saa_schedule_eclipse = Helpers.inclusive_slice(saa_schedule, eclipse_start, eclipse_end)
            polar_keepout_schedule_eclipse = Helpers.inclusive_slice(polar_keepout_schedule, eclipse_start, eclipse_end)

            # Update the eclipse schedule
            # for target_schedule in eclipse.targets_available.values():
            for _, target_schedule in eclipse.targets_available.items():
                if np.any(target_schedule):

                    # Mark the eclipse as observing a target
                    eclipse_schedule[target_schedule & ~saa_schedule_eclipse & ~polar_keepout_schedule_eclipse] = MissionStatus.OBSERVING.value

                    if np.all(eclipse_schedule != MissionStatus.DOWNTIME.value):
                        break  # Stop if there is no downtime in the eclipse

            # Save the eclipse schedule
            eclipse.operations.status = eclipse_schedule

    def _allocate_downlink_windows(self, operations_schedule):
        """Allocate the downlink windows in the operations schedule."""
        # Get the downlink schedule
        downlink_schedule = self.get_schedule_by_name("Ground Stations Schedule").status
        operations_schedule[downlink_schedule] = MissionStatus.DOWNLINK.value

        # Allocate the pointing windows for downlink
        dilated_downlink = Helpers.get_moves_outside(operations_schedule == MissionStatus.DOWNLINK.value, pointing_cost=Helpers.get_pointing_cost())
        operations_schedule[dilated_downlink == 1] = MissionStatus.SLEWING.value

        # Update the eclipses
        for eclipse in self.science_mission.eclipses:
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            eclipse_schedule = np.copy(Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end))
            eclipse.operations.status = eclipse_schedule

    def _allocate_pointing_operations(self, operations_schedule, pointing_debug):
        """Allocate the pointing operations and choose targets to observe."""
        min_exp_time = min([survey.target_min_exp_time for survey in self.science_mission.surveys])

        for eclipse_num, eclipse in enumerate(self.science_mission.eclipses):
            eclipse_schedule = eclipse.operations.status
            eclipse_start = eclipse.schedule_indices[0]
            eclipse_end = eclipse.schedule_indices[1]
            if pointing_debug:
                print(f'----------- Eclipse {eclipse_num} -----------')
                self.plot_eclipse_summary(eclipse_num)

            self.update_targets_priorities(eclipse, pointing_debug)

            # Allocate the pointing operations if there is at least one target available
            if np.any(eclipse_schedule == MissionStatus.OBSERVING.value):
                target_num = MissionStatus.TARGET1.value
                for target_name, target_schedule in eclipse.targets_available.items():
                    if np.any(target_schedule):
                        if target_num == MissionStatus.TARGET1.value:
                            target_num = self._allocate_target_pointing_operations(eclipse, eclipse_schedule, operations_schedule, target_name, target_schedule, target_num, eclipse_start, eclipse_end, min_exp_time, pointing_debug)
                        elif target_num == MissionStatus.TARGET2.value:
                            target_num = self._allocate_target2_pointing_operations(eclipse, eclipse_schedule, operations_schedule, target_name, target_schedule, target_num, eclipse_start, eclipse_end, min_exp_time, pointing_debug)
                        # Break if all targets pointing windows have been allocated
                        if target_num == -3:
                            print(f"Exiting eclipse {eclipse_num} because all pointing windows have been allocated")
                            break
            else:
                # print(eclipse.targets_available)
                print('------- WARNING -------')
                print(f'ISSUE: Eclipse {eclipse_num} has no targets available')
                if np.any(eclipse_schedule == MissionStatus.DOWNLINK.value):
                    print('REASON: Downlinking during eclipse')
                elif np.any(self.satellite.moon_altitudes[eclipse_start: eclipse_end + 1] > self.satellite.moon_altitudes[eclipse_start: eclipse_end + 1]):
                    print('REASON: Moon is visible during eclipse')
                elif len(eclipse_schedule) * self.satellite.time_step_sec / 60 < 20:
                    print('REASON: Eclipse is too short')
                print('-----------------------')

    def _allocate_target_pointing_operations(
        self,
        eclipse,
        eclipse_schedule,
        operations_schedule,
        target_name,
        target_schedule,
        target_num,
        eclipse_start,
        eclipse_end,
        min_exp_time,
        pointing_debug
        ):
        """
        Schedule Target and its pointing sequence within an eclipse.
        Prioritizes observation windows after POLAR regions and before SAA.
        Pointing operations finish exactly at the beginning of the observation window.
        Continues observation after SAA without re-pointing.
        """
        if pointing_debug:
            print(f"\n----- Starting allocation for {target_name} -----")
        pointing_sequence_length = Helpers.get_pointing_cost()
        
        # Check for exact time requirement
        exact_time_only = False
        survey = self.science_mission.get_survey_of_target(target_name)
        if survey.target_exp_time == survey.target_min_exp_time:
            exact_time_only = True
            original_target_length = survey.target_min_exp_time / self.satellite.time_step_sec
        else:
            original_target_length = np.sum(target_schedule)
            
        # Calculate minimum length required
        min_target_length = min_exp_time / self.satellite.time_step_sec
        
        # Initialize target sequence length
        target_sequence_length = original_target_length
        length = len(eclipse_schedule)
        
        if pointing_debug:
            print(f"Pointing length: {pointing_sequence_length}")
            print(f"Target sequence length: {target_sequence_length}")
            print(f"Minimum target length: {min_target_length}")
            print(f"Total schedule length: {length}")
            print(f"Exact time only: {exact_time_only}")

        # Get valid pointing positions
        valid_pointing_statuses = [
            MissionStatus.OBSERVING.value,
            MissionStatus.DOWNTIME.value,
            MissionStatus.SAA.value,
            MissionStatus.POLAR.value
        ]
        
        # PHASE 1: Look for first valid observation window
        for obs_start in range(length):
            # Skip if not a valid observation position
            if target_schedule[obs_start] != 1 or eclipse_schedule[obs_start] != MissionStatus.OBSERVING.value:
                continue
                
            if pointing_debug:
                print(f"\n--- Found potential observation start at position {obs_start} ---")
                
            # Check if we can place pointing sequence before this position
            pointing_start = obs_start - pointing_sequence_length
            
            if pointing_debug:
                print(f"Observation would start at: {obs_start}")
                print(f"Pointing would start at: {pointing_start}")
                
            if pointing_start < 0:
                if pointing_debug:
                    print("Not enough space for pointing before observation - skipping")
                continue
                
            # Check if pointing positions are valid
            can_place_pointing = True
            for p in range(pointing_start, obs_start):
                if eclipse_schedule[p] not in valid_pointing_statuses:
                    can_place_pointing = False
                    if pointing_debug:
                        print(f"Cannot place pointing at position {p} - invalid status: {MissionStatus(eclipse_schedule[p]).name}")
                    break
                    
            if not can_place_pointing:
                if pointing_debug:
                    print("Cannot place pointing sequence - skipping")
                continue
                
            # Find how long we can observe continuously
            continuous_obs_end = obs_start
            while continuous_obs_end < length:
                if target_schedule[continuous_obs_end] != 1 or eclipse_schedule[continuous_obs_end] != MissionStatus.OBSERVING.value:
                    break
                continuous_obs_end += 1
                
            continuous_obs_length = continuous_obs_end - obs_start
            
            if pointing_debug:
                print(f"Continuous observation window: {obs_start} to {continuous_obs_end-1}")
                print(f"Length: {continuous_obs_length}")
                
            # Check if we hit SAA
            encountered_saa = False
            saa_start = continuous_obs_end
            
            if saa_start < length and eclipse_schedule[saa_start] == MissionStatus.SAA.value:
                encountered_saa = True
                
                # Find SAA end
                saa_end = saa_start
                while saa_end < length and eclipse_schedule[saa_end] == MissionStatus.SAA.value:
                    saa_end += 1
                    
                if pointing_debug:
                    print(f"Found SAA from {saa_start} to {saa_end-1}")
                    
                # Find post-SAA observation window
                post_saa_start = saa_end
                post_saa_end = post_saa_start
                
                while post_saa_end < length:
                    if target_schedule[post_saa_end] != 1 or eclipse_schedule[post_saa_end] != MissionStatus.OBSERVING.value:
                        break
                    post_saa_end += 1
                    
                post_saa_length = post_saa_end - post_saa_start
                
                if pointing_debug:
                    print(f"Post-SAA observation window: {post_saa_start} to {post_saa_end-1}")
                    print(f"Length: {post_saa_length}")
                    
                # Calculate total observation length
                total_obs_length = continuous_obs_length + post_saa_length
            else:
                total_obs_length = continuous_obs_length
                
            if pointing_debug:
                print(f"Total observation length: {total_obs_length}")
                
            # Check if we have enough observation time
            if total_obs_length < min_target_length and exact_time_only:
                if pointing_debug:
                    print(f"Not enough observation time ({total_obs_length}) for minimum requirement ({min_target_length})")
                continue
                
            # At this point, we've found a valid observation window with pointing before it
            # and potentially a post-SAA continuation
            if pointing_debug:
                print("\n!!! Found valid observation window with pre-positioned pointing !!!")
                
            # Calculate how many observation positions to use
            pre_saa_to_use = min(continuous_obs_length, int(target_sequence_length))
            remaining_needed = max(0, int(target_sequence_length) - pre_saa_to_use)
            
            post_saa_to_use = 0
            if encountered_saa and remaining_needed > 0:
                post_saa_to_use = min(post_saa_length, remaining_needed)
                
            # Allocate pointing sequence
            if pointing_debug:
                print("\nAllocating pointing sequence...")
            for p in range(pointing_start, obs_start):
                eclipse_schedule[p] = MissionStatus.SLEWING.value
                if pointing_debug:
                    print(f"Set position {p} to SLEWING")
                    
            # Allocate pre-SAA target positions
            if pointing_debug:
                print("\nAllocating pre-SAA target positions...")
            for p in range(obs_start, obs_start + pre_saa_to_use):
                eclipse_schedule[p] = target_num
                if pointing_debug:
                    print(f"Set position {p} to TARGET")
                    
            # Allocate post-SAA target positions
            if encountered_saa and post_saa_to_use > 0:
                if pointing_debug:
                    print("\nAllocating post-SAA target positions...")
                post_saa_start = saa_end
                for i in range(post_saa_to_use):
                    pos = post_saa_start + i
                    eclipse_schedule[pos] = target_num
                    if pointing_debug:
                        print(f"Set position {pos} to TARGET")
                        
            # Convert remaining OBSERVING to DOWNTIME
            if pointing_debug:
                print("\nConverting remaining OBSERVING to DOWNTIME...")
            downtime_conversions = 0
            for i in range(length):
                if eclipse_schedule[i] == MissionStatus.OBSERVING.value:
                    eclipse_schedule[i] = MissionStatus.DOWNTIME.value
                    downtime_conversions += 1
            if pointing_debug:
                print(f"Converted {downtime_conversions} positions to DOWNTIME")
                            
            # Update eclipse and operations
            if pointing_debug:
                print("\nUpdating eclipse and operations...")
            self._update_eclipse_and_operations(
                eclipse,
                eclipse_schedule,
                operations_schedule,
                target_name,
                target_num,
                eclipse_start,
                eclipse_end,
                pointing_debug
            )
            
            if pointing_debug:
                print(f"\nSuccessfully allocated target with {pre_saa_to_use} positions before SAA and {post_saa_to_use} after!")
            return target_num - 1  # Successfully allocated target and pointing
        
        # If we get here, we couldn't find a suitable observation window
        # Fall back to standard allocation (original algorithm)
        if pointing_debug:
            print("\n=== No suitable observation window found, trying standard allocation ===")
        
        # Start with full exposure time, then reduce if needed
        while target_sequence_length >= min_target_length:
            if pointing_debug:
                print(f"\n=== Trying with target sequence length: {target_sequence_length} ===")
            
            # Try consecutive chunks of the current target length
            current_chunk_start = 0
            
            while current_chunk_start + target_sequence_length <= length:
                if pointing_debug:
                    print(f"\n--- Trying chunk starting at position {current_chunk_start} ---")
                
                # Check if we have enough consecutive valid positions
                has_enough_consecutive = True
                potential_chunk = []
                
                # Verify consecutive positions
                for i in range(current_chunk_start, current_chunk_start + int(target_sequence_length)):
                    if target_schedule[i] != 1 or eclipse_schedule[i] != MissionStatus.OBSERVING.value:
                        has_enough_consecutive = False
                        if pointing_debug:
                            print(f"Position {i} invalid: target_schedule={target_schedule[i]}, "
                                f"status={MissionStatus(eclipse_schedule[i]).name}")
                        break
                    potential_chunk.append(i)
                
                if not has_enough_consecutive:
                    if pointing_debug:
                        print(f"Not enough consecutive valid positions starting at {current_chunk_start}")
                    current_chunk_start += 1
                    continue
                    
                if pointing_debug:
                    print(f"Found potential chunk: {potential_chunk}")
                
                # Try to allocate pointing for this chunk
                pointing_start = current_chunk_start - pointing_sequence_length
                
                if pointing_debug:
                    print(f"Target would start at: {current_chunk_start}")
                    print(f"Pointing would start at: {pointing_start}")
                
                if pointing_start < 0:
                    if pointing_debug:
                        print("Not enough space before target - skipping chunk")
                    current_chunk_start += 1
                    continue

                # Check if we can place pointing sequence
                can_place_pointing = True
                invalid_positions = []
                for i in range(pointing_start, current_chunk_start):
                    if eclipse_schedule[i] not in valid_pointing_statuses:
                        can_place_pointing = False
                        invalid_positions.append((i, MissionStatus(eclipse_schedule[i]).name))
                
                if not can_place_pointing:
                    if pointing_debug:
                        print(f"Cannot place pointing - invalid positions: {invalid_positions}")
                    current_chunk_start += 1
                    continue

                # Found valid chunk and pointing position - allocate both
                if pointing_debug:
                    print("Found valid chunk and pointing position!")
                    print("\nAllocating target sequence...")
                
                # Allocate target
                for i in potential_chunk:
                    eclipse_schedule[i] = target_num
                    if pointing_debug:
                        print(f"Set position {i} to TARGET")
                
                # Allocate pointing
                if pointing_debug:
                    print("\nAllocating pointing sequence...")
                for i in range(pointing_start, current_chunk_start):
                    eclipse_schedule[i] = MissionStatus.SLEWING.value
                    if pointing_debug:
                        print(f"Set position {i} to SLEWING")
                            
                # Convert remaining OBSERVING to DOWNTIME
                if pointing_debug:
                    print("\nConverting remaining OBSERVING to DOWNTIME...")
                downtime_conversions = 0
                for i in range(length):
                    if eclipse_schedule[i] == MissionStatus.OBSERVING.value:
                        eclipse_schedule[i] = MissionStatus.DOWNTIME.value
                        downtime_conversions += 1
                if pointing_debug:
                    print(f"Converted {downtime_conversions} positions to DOWNTIME")
                                
                # Update eclipse and operations
                if pointing_debug:
                    print("\nUpdating eclipse and operations...")
                self._update_eclipse_and_operations(
                    eclipse,
                    eclipse_schedule,
                    operations_schedule,
                    target_name,
                    target_num,
                    eclipse_start,
                    eclipse_end,
                    pointing_debug
                )
                
                if pointing_debug:
                    print(f"\nSuccessfully allocated target with length {target_sequence_length} and pointing!")
                return target_num - 1  # Successfully allocated target and pointing

            # Couldn't allocate with current length, reduce if not exact time only
            if exact_time_only:
                if pointing_debug:
                    print("\nExact time required, no reduction possible")
                break
            else:
                # Reduce target sequence length by 10%
                new_length = max(min_target_length, target_sequence_length * 0.9)
                if pointing_debug:
                    print(f"\nReducing target sequence length from {target_sequence_length} to {new_length}")
                    print(f"This corresponds to {new_length * self.satellite.time_step_sec} seconds of exposure time")
                    print(f"Minimum required: {min_target_length * self.satellite.time_step_sec} seconds")
                target_sequence_length = new_length

        # If we get here, we couldn't allocate pointing for any chunk
        if pointing_debug:
            print("\nCould not allocate pointing for any chunk")
            print(f"Tried target lengths from {original_target_length} down to {target_sequence_length}")
            print(f"Minimum required exposure time: {min_exp_time} seconds")
        return target_num

    def _allocate_target2_pointing_operations(
        self,
        eclipse,
        eclipse_schedule,
        operations_schedule,
        target_name,
        target_schedule,
        target_num,
        eclipse_start,
        eclipse_end,
        min_exp_time,
        pointing_debug
    ):
        """
        Schedule Target2 and its pointing sequence within an eclipse.
        Tries consecutive chunks of the required size until finding a valid one.
        """
        if pointing_debug:
            print(f"\n----- Starting allocation for {target_name} (Target2) -----")
        pointing_sequence_length = int(Helpers.get_pointing_cost()/2)
        
        # Check for exact time requirement
        exact_time_only = False
        survey = self.science_mission.get_survey_of_target(target_name)
        if survey.target_exp_time == survey.target_min_exp_time:
            exact_time_only = True
            original_target_length = survey.target_min_exp_time / self.satellite.time_step_sec
        else:
            original_target_length = np.sum(target_schedule)
        
        target_sequence_length = original_target_length
        length = len(eclipse_schedule)
        
        if pointing_debug:
            print(f"Pointing length: {pointing_sequence_length}")
            print(f"Initial target sequence length: {target_sequence_length}")
            print(f"Total schedule length: {length}")
            print(f"Exact time only: {exact_time_only}")

        # Find Target1 positions to determine valid Target2 regions
        target1_positions = [i for i in range(length) if eclipse_schedule[i] == MissionStatus.TARGET1.value]
        target1_pointing = [i for i in range(length) if eclipse_schedule[i] == MissionStatus.SLEWING.value]
        
        # Determine valid regions for Target2 (before Target1 pointing or after Target1 sequence)
        valid_regions = []
        
        if target1_positions and target1_pointing:
            first_pointing = min(target1_pointing)
            last_target1 = max(target1_positions)
            
            # Region before first Target1 pointing
            if first_pointing > pointing_sequence_length:
                valid_regions.append((0, first_pointing))
                
            # Region after last Target1
            if last_target1 < length - 1:
                valid_regions.append((last_target1 + 1, length))
        else:
            valid_regions.append((0, length))

        if pointing_debug:
            print(f"Valid regions for Target2: {valid_regions}")

        # Get valid pointing positions - including SAA
        valid_pointing_statuses = [
            MissionStatus.OBSERVING.value,
            MissionStatus.DOWNTIME.value,
            MissionStatus.SAA.value,
            MissionStatus.POLAR.value
        ]

        # Try consecutive chunks of the required size
        current_chunk_start = 0
        
        while current_chunk_start + target_sequence_length <= length:
            if pointing_debug:
                print(f"\n--- Trying chunk starting at position {current_chunk_start} ---")
            
            # Check if we have enough consecutive valid positions
            has_enough_consecutive = True
            potential_chunk = []
            
            for i in range(current_chunk_start, current_chunk_start + int(target_sequence_length)):
                if target_schedule[i] != 1 or eclipse_schedule[i] != MissionStatus.DOWNTIME.value:
                    has_enough_consecutive = False
                    break
                potential_chunk.append(i)
            
            if not has_enough_consecutive:
                if pointing_debug:
                    print(f"Not enough consecutive valid positions starting at {current_chunk_start}")
                current_chunk_start += 1
                continue
                
            if pointing_debug:
                print(f"Found potential chunk: {potential_chunk}")
            
            # Create temporary schedule for trying this chunk
            temp_schedule = eclipse_schedule.copy()
            
            # Allocate target in this chunk
            for i in potential_chunk:
                temp_schedule[i] = target_num
            
            # Check if this chunk is entirely within a valid region
            chunk_valid = False
            for region_start, region_end in valid_regions:
                if current_chunk_start >= region_start and current_chunk_start + target_sequence_length <= region_end:
                    chunk_valid = True
                    break
            
            if not chunk_valid:
                if pointing_debug:
                    print(f"Chunk not within valid regions - trying next position")
                current_chunk_start += 1
                continue

            # Try to allocate pointing for this chunk
            pointing_start = current_chunk_start - pointing_sequence_length
            
            if pointing_debug:
                print(f"Target starts at: {current_chunk_start}")
                print(f"Pointing would start at: {pointing_start}")
            
            if pointing_start < 0:
                if pointing_debug:
                    print("Not enough space before target - skipping chunk")
                current_chunk_start += 1
                continue

            # Check if pointing sequence would overlap with Target1 or its pointing
            would_overlap = False
            for i in range(pointing_start, current_chunk_start):
                if temp_schedule[i] in [MissionStatus.TARGET1.value, MissionStatus.SLEWING.value]:
                    would_overlap = True
                    break
            
            if would_overlap:
                if pointing_debug:
                    print("Would overlap with Target1 or its pointing - skipping chunk")
                current_chunk_start += 1
                continue

            # Check if we can place pointing sequence
            can_place_pointing = True
            invalid_positions = []
            for i in range(pointing_start, current_chunk_start):
                if temp_schedule[i] not in valid_pointing_statuses:
                    can_place_pointing = False
                    invalid_positions.append((i, MissionStatus(temp_schedule[i]).name))
            
            if not can_place_pointing:
                if pointing_debug:
                    print(f"Cannot place pointing - invalid positions: {invalid_positions}")
                current_chunk_start += 1
                continue

            if pointing_debug:
                print("Found valid pointing position!")
            # Allocate pointing
            if pointing_debug:
                print("\nAllocating pointing sequence...")
            for i in range(pointing_start, current_chunk_start):
                temp_schedule[i] = MissionStatus.SLEWING.value
                if pointing_debug:
                    print(f"Set position {i} to SLEWING")
                        
            # Update the real schedule with this valid solution
            eclipse_schedule[:] = temp_schedule[:]
                        
            # Update eclipse and operations
            if pointing_debug:
                print("\nUpdating eclipse and operations...")
            self._update_eclipse_and_operations(
                eclipse,
                eclipse_schedule,
                operations_schedule,
                target_name,
                target_num,
                eclipse_start,
                eclipse_end,
                pointing_debug
            )
            
            if pointing_debug:
                print("\nSuccessfully allocated Target2 and pointing!")
            return -3  # Successfully allocated target and pointing

        # If we get here, we couldn't allocate pointing for any chunk
        if pointing_debug:
            print("\nCould not allocate pointing for any chunk")
        return target_num

    def _get_pointing_indices(self, eclipse_schedule, target_num, other_target_num, first_target_num):
        """Get the start and end indices for pointing."""
        if first_target_num == target_num:
            index_end_pointing = Helpers.get_change_indices(eclipse_schedule, other_target_num, 'after', 'start')[0]
            index_start_pointing = index_end_pointing - Helpers.get_pointing_cost()
        else:
            index_start_pointing = Helpers.get_change_indices(eclipse_schedule, target_num, 'after', 'start')[0]
            index_end_pointing = index_start_pointing + Helpers.get_pointing_cost()
        return index_start_pointing, index_end_pointing

    def _update_eclipse_and_operations(self, eclipse, eclipse_schedule, operations_schedule, target_name, target_num, eclipse_start, eclipse_end, pointing_debug):
        """Update the eclipse and operations schedule."""

        # Update the eclipse's properties for the eclipse object
        eclipse.operations.status = eclipse_schedule
        # index = 0 if target_num == MissionStatus.TARGET1.value else 1
        # print(f"{target_name} has target number {target_num}")
        # print(f"{target_name} at index {index}")
        # if len(eclipse.targets_names) > index:
            # eclipse.targets_names[index] = target_name
            # eclipse.targets_exp_times[index] = np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec
        # else:
        eclipse.targets_names.append(target_name)
        eclipse.targets_exp_times.append(np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec)
        # print(f"Target name: {target_name}, Target exp time: {np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec}", eclipse.targets_names, eclipse.targets_exp_times)

        # Update the target's properties for the target object
        target = self.science_mission.get_target_by_name(target_name)
        target.current_exp_time += np.sum(eclipse_schedule == target_num) * self.satellite.time_step_sec

        # Update the operations schedule with the eclipse's schedule
        operations_schedule[eclipse_start: eclipse_end + 1] = eclipse_schedule
        
        # Plot the eclipse's operations
        if pointing_debug:
            print(f"Allocated pointing for {target_name}")
            self.plot_eclipse_summary(eclipse.eclipse_number, operations_schedule=operations_schedule)

    # TODO: Description
    def _allocate_pointing_windows_for_charging(self, operations_schedule):
        """_summary_

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
        """

        # Get the indices before you start charging (get the last status before you start charging)
        indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.CHARGING.value, index='before', change_type='start')

        # See detailed visualization inside each function
        for _, index in enumerate(indices):
            if index + Helpers.get_pointing_cost() >= len(operations_schedule):
                operations_schedule[index:] = MissionStatus.SLEWING.value
                pass
            elif operations_schedule[index] == MissionStatus.DOWNTIME.value:
                # print(self.satellite.times.utc_datetime()[index], 1)
                self._allocate_pointing_before_charging_during_downtime(operations_schedule, index)
            elif operations_schedule[index - Helpers.get_pointing_cost()] == MissionStatus.SLEWING.value and operations_schedule[index] not in [MissionStatus.POLAR.value]:
                # print(self.satellite.times.utc_datetime()[index], 2)
                # print(operations_schedule[index])
                self._allocate_charging_after_pointing_before_charging_during_unknown(operations_schedule, index)
            elif operations_schedule[index] == MissionStatus.POLAR.value:
                # print(self.satellite.times.utc_datetime()[index], 3)
                self._allocate_pointing_before_charging_during_polar(operations_schedule, index)
            elif operations_schedule[index] != MissionStatus.SLEWING.value:
                # print(self.satellite.times.utc_datetime()[index], 4)
                self._allocate_pointing_if_possible(operations_schedule, index)
            


        # # Get the indices after you end charging
        # indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.CHARGING.value, index='after', change_type='end')

        # # See detailed visualization inside each function
        # for index in indices:
        #     if operations_schedule[index] == MissionStatus.SAA.value:
        #         self._allocate_pointing_after_saa(operations_schedule, index)
        #     elif operations_schedule[index] not in (MissionStatus.SLEWING.value, MissionStatus.DOWNTIME.value):
        #         self._allocate_pointing_before_end(operations_schedule, index)

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
        start_downtime_indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.DOWNTIME.value, index='after', change_type='start')
        closest_start_downtime_index = Helpers.get_closest_value(value=index, array=start_downtime_indices)
        start_pointing_index = closest_start_downtime_index
        end_pointing_index = start_pointing_index + Helpers.get_pointing_cost() + 1
        operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.SLEWING.value

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
        if status_after_pointing not in (MissionStatus.TARGET1, MissionStatus.TARGET2):
            start_status_indices = Helpers.get_change_indices(schedule=operations_schedule, value=status_after_pointing, index='after', change_type='start')
            closest_start_status_index = Helpers.get_closest_value(value=index - Helpers.get_pointing_cost(), array=start_status_indices)
            start_pointing_index = closest_start_status_index
            end_pointing_index = start_pointing_index + Helpers.get_pointing_cost() + 1
            operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.CHARGING.value

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
        start_polar_indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.POLAR.value, index='after', change_type='start')
        closest_start_polar_index = Helpers.get_closest_value(value=index, array=start_polar_indices)
        start_pointing_index = closest_start_polar_index
        end_pointing_index = start_pointing_index + Helpers.get_pointing_cost() + 1
        operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.SLEWING.value

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
        end_pointing_index = start_pointing_index + Helpers.get_pointing_cost() + 1
        if np.all(operations_schedule[start_pointing_index: end_pointing_index] == MissionStatus.CHARGING.value):
            operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.SLEWING.value

    # Done
    def _allocate_pointing_after_saa(self, operations_schedule, index):
        """Allocate pointing for charging after the start of the SAA.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Example (S = SAA, n = not pointing or observing, P = pointing, C = charging):
        # Prev.: [C C S S S n n]
        # After: [C C S P P n n]

        # Start pointing before the end of the SAA to take advantage of the SAA
        end_SAA_indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.SAA.value, index='after', change_type='end')
        closest_end_SAA_index = Helpers.get_closest_value(value=index, array=end_SAA_indices)
        if operations_schedule[closest_end_SAA_index + 1] not in (MissionStatus.SLEWING.value, MissionStatus.OBSERVING.value):
            end_pointing_index = closest_end_SAA_index + 1
            start_pointing_index = end_pointing_index - Helpers.get_pointing_cost()
            operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.SLEWING.value

    # Done
    def _allocate_pointing_before_end(self, operations_schedule, index):
        """Allocate pointing for charging before the end of the schedule.

        Args:
            operations_schedule (numpy.ndarray): The operation schedule.
            index (int): The index of the current operation.
        """

        # Edge case for last pointing for charging
        start_pointing_index = index - Helpers.get_pointing_cost() - 1
        end_pointing_index = index
        operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.SLEWING.value

    # TODO: Comment, docstring
    def _handle_edge_cases_for_downtime(self, operations_schedule):
        
        indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.POLAR.value, index='after', change_type='end')

        for _, index in enumerate(indices):
            if operations_schedule[index] == MissionStatus.CHARGING.value:
                start_charging_indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.CHARGING.value, index='after', change_type='start')
                end_charging_indices = Helpers.get_change_indices(schedule=operations_schedule, value=MissionStatus.CHARGING.value, index='before', change_type='end')
                closes_start_charging_index = Helpers.get_closest_value(value=index, array=start_charging_indices)
                closest_end_charging_index = Helpers.get_closest_value(value=index, array=end_charging_indices)
                start_pointing_index = closes_start_charging_index
                end_pointing_index = closest_end_charging_index + 1
                operations_schedule[start_pointing_index: end_pointing_index] = MissionStatus.DOWNTIME.value

        if np.sum(operations_schedule == MissionStatus.OBSERVING.value) > 0:
            operations_schedule[operations_schedule == MissionStatus.OBSERVING.value] = MissionStatus.DOWNTIME.value

    # TODO: Comment, docstring
    def update_targets_priorities(self, eclipse, pointing_debug):
        """Update the priorities of the targets based on their exposure times."""
        if len(eclipse.targets_available) != 0:
            max_exposure_time = max(np.sum(list(eclipse.targets_available.values()), axis=1) * self.satellite.time_step_sec)
            target_to_pop = []

            for target_name, target_schedule in eclipse.targets_available.items():
                target_survey = self.science_mission.get_survey_of_target(target_name)
                target = self.science_mission.get_target_by_name(target_name)
                if target.current_exp_time < target_survey.total_exp_time:
                    if target.base_priority < 0:
                        # Negative base priority: use as fixed rank (lower = higher priority)
                        target.eclipse_priority = target.base_priority
                    else:
                        target_exposure_time = np.sum(target_schedule) * self.satellite.time_step_sec
                        time_available_factor = max_exposure_time / target_exposure_time
                        target.eclipse_priority = target.base_priority + time_available_factor
                else:
                    target_to_pop.append(target_name)

            for target_name in target_to_pop:
                eclipse.targets_available.pop(target_name)

            # Pinned targets (negative base_priority) come first: -1 = 1st, -2 = 2nd (sorted descending, closer to 0 = higher rank)
            pinned = sorted(
                [(n, s) for n, s in eclipse.targets_available.items() if self.science_mission.get_target_by_name(n).base_priority < 0],
                key=lambda item: self.science_mission.get_target_by_name(item[0]).base_priority, reverse=True
            )
            normal = sorted(
                [(n, s) for n, s in eclipse.targets_available.items() if self.science_mission.get_target_by_name(n).base_priority >= 0],
                key=lambda item: self.science_mission.get_target_by_name(item[0]).eclipse_priority
            )
            eclipse.targets_available = dict(pinned + normal)

            # Print the updated priorities
            if pointing_debug:
                print("After sorting:")
                for target_name in eclipse.targets_available.keys():
                    target = self.science_mission.get_target_by_name(target_name)
                    print(f"Target: {target_name}, Priority: {target.eclipse_priority}")

    def _update_eclipses(self, operations_schedule):
        for i, eclipse in enumerate(self.science_mission.eclipses):
            eclipse_schedule_in_mission = Helpers.inclusive_slice(operations_schedule, eclipse.schedule_indices[0], eclipse.schedule_indices[1])
            eclipse.operations.status = eclipse_schedule_in_mission
            for i in range(len(eclipse.targets_exp_times)):
                if i == 0:
                    target_num = MissionStatus.TARGET1.value
                else:
                    target_num = MissionStatus.TARGET2.value
                eclipse.targets_exp_times[i] = np.sum(eclipse_schedule_in_mission == target_num) * self.satellite.time_step_sec


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

    def plot_battery_charge_plot(self):
        """
        Generates a realistic battery charge plot based on power budget and action list.

        Args:
            None

        Returns:
            None (plots the battery charge profile)
        """

        # Get the power budget information
        net_energy_dict = Helpers.get_energy_dict(self.mission_config)
        initial_charge = net_energy_dict['INITIAL_CHARGE']
        max_charge = net_energy_dict['MAXIMUM_CHARGE']

        # Loop through the actions
        current_node = self.commands_list.head_node

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
            battery_charge_joules.append(min(battery_charge_joules[-1] + action_energy, max_charge))
            battery_charge_time.append(action_time + action_duration)

            # Move to the next node
            current_node = current_node.getNextNode()

        # Prepare eclipse times
        eclipse_times = []
        for eclipse in self.science_mission.eclipses:
            for i in range(2):
                eclipse_times.append(self.satellite.times.utc_datetime()[eclipse.schedule_indices[i]])

        # Create time points for a more detailed plot with proper constraint enforcement
        x_seconds = [(time - battery_charge_time[0]).total_seconds() for time in battery_charge_time]
        
        # Create a piecewise linear interpolation - more realistic for battery charging
        from scipy.interpolate import interp1d
        
        # Create a denser set of points for smoother appearance while respecting constraints
        X_seconds = np.linspace(min(x_seconds), max(x_seconds), 1000)
        
        # Use piecewise linear interpolation which respects the limits better
        interp_func = interp1d(x_seconds, battery_charge_joules, kind='linear')
        Y_interp = interp_func(X_seconds)
        
        # Apply battery physical constraints (no exceeding max charge)
        Y_constrained = np.minimum(Y_interp, max_charge)
        
        # Convert back to datetime for plotting
        X_datetime = [battery_charge_time[0] + datetime.timedelta(seconds=time) for time in X_seconds]
        
        # Convert to kJ for display
        Y_kJ = Y_constrained / 1000
        
        # Create the plot
        plt.figure(figsize=(10, 6))
        plt.title('Battery Charge Profile', fontsize=20)
        
        # Plot the constrained interpolation as the main curve
        plt.plot(X_datetime, Y_kJ, color='#FF5003', linewidth=4, label='Battery Charge')
        
        # Optional: Add the actual data points for reference
        # plt.scatter([battery_charge_time[0] + datetime.timedelta(seconds=sec) for sec in x_seconds], 
        #             [charge/1000 for charge in battery_charge_joules], 
        #             color='blue', s=30, alpha=0.6, label='Action Points')
        
        # Add a horizontal line for max capacity
        plt.axhline(y=max_charge/1000, color='k', linestyle='--', 
                    linewidth=1.5, label=f'Max Capacity ({max_charge/1000:.1f} kJ)')
        
        # Highlight eclipse periods
        for start, end in zip(eclipse_times[::2], eclipse_times[1::2]):
            plt.axvspan(start, end, color='lightsteelblue', alpha=0.3)
            
        # Add legend to explain the elements
        plt.legend(loc='best')
        
        # Format the plot
        plt.ylabel('Battery Charge [kJ]', fontsize=15)
        plt.xlabel('Time in UTC', fontsize=15)
        plt.grid(which='both', linestyle='--', linewidth=0.2)
        plt.xticks(rotation=45)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d-%y, %H:%M:%S'))
        
        # # Add some annotations for clearer understanding
        # # Find a charging and discharging segment to annotate
        # for i in range(1, len(battery_charge_joules)):
        #     if battery_charge_joules[i] > battery_charge_joules[i-1]:
        #         # Charging segment
        #         midpoint_idx = (x_seconds[i] + x_seconds[i-1]) / 2
        #         midpoint_time = battery_charge_time[0] + datetime.timedelta(seconds=midpoint_idx)
        #         midpoint_charge = (battery_charge_joules[i] + battery_charge_joules[i-1]) / 2 / 1000
        #         plt.annotate("Charging", xy=(midpoint_time, midpoint_charge),
        #                     xytext=(midpoint_time, midpoint_charge+max_charge/10000),
        #                     arrowprops=dict(facecolor='green', shrink=0.05, width=1.5),
        #                     fontsize=10, color='green', ha='center')
        #         break
        
        # for i in range(1, len(battery_charge_joules)):
        #     if battery_charge_joules[i] < battery_charge_joules[i-1]:
        #         # Discharging segment
        #         midpoint_idx = (x_seconds[i] + x_seconds[i-1]) / 2
        #         midpoint_time = battery_charge_time[0] + datetime.timedelta(seconds=midpoint_idx)
        #         midpoint_charge = (battery_charge_joules[i] + battery_charge_joules[i-1]) / 2 / 1000
        #         plt.annotate("Discharging", xy=(midpoint_time, midpoint_charge),
        #                     xytext=(midpoint_time, midpoint_charge-max_charge/10000),
        #                     arrowprops=dict(facecolor='red', shrink=0.05, width=1.5),
        #                     fontsize=10, color='red', ha='center')
        #         break
        
        plt.tight_layout()
        plt.show()

    def plot_target_completion(self):
        """
        Generates an enhanced plot showing target observation completion over time.
        
        This function tracks cumulative exposure time for each target and displays
        it as a step plot, with various visual enhancements for clarity.
        
        Args:
            None
            
        Returns:
            None (displays the plot)
        """
        # Initialize data structures
        current_node = self.commands_list.head_node
        target_completion_names = []
        target_completion_exp_times = []  # Exposure times in seconds
        target_completion_exc_times = []  # Time of execution
        
        # Process the command list to extract target observations
        while current_node:
            # Get the data for the current node
            command = current_node.data
            command_key = command.key
            command_time = command.time

            # If the command is a target exposure (not a system operation)
            if MissionStatus.get_value(command_key) is None:
                eclipse_num = command.eclipse_num
                eclipse = self.science_mission.eclipses[eclipse_num]
                
                # Extract target name from command key
                if "TARGET1" in command_key or "TARGET2" in command_key:
                    target_name = command_key.split(": ")[1]
                    index = eclipse.targets_names.index(target_name)
                    target_exposure_sec = eclipse.targets_exp_times[index]
                    
                    target_completion_names.append(target_name)
                    target_completion_exp_times.append(target_exposure_sec)
                    target_completion_exc_times.append(command_time)

            # Move to the next node
            current_node = current_node.getNextNode()

        # Calculate cumulative sums for each unique target
        unique_targets = list(set(target_completion_names))
        running_totals = {name: 0 for name in unique_targets}
        
        # Create arrays to store cumulative exposure times
        cumulative_times_by_target = {}
        for target in unique_targets:
            cumulative_times_by_target[target] = []
        
        # Process observations chronologically
        sorted_indices = np.argsort([t.timestamp() for t in target_completion_exc_times])
        sorted_names = [target_completion_names[i] for i in sorted_indices]
        sorted_times = [target_completion_exp_times[i] for i in sorted_indices]
        sorted_exec_times = [target_completion_exc_times[i] for i in sorted_indices]
        
        # Build cumulative exposure time for each target
        for target in unique_targets:
            current_total = 0
            target_cumulative = []
            
            for name, time, exec_time in zip(sorted_names, sorted_times, sorted_exec_times):
                if name == target:
                    current_total += time
                target_cumulative.append((exec_time, current_total))
            
            # Store chronological (time, cumulative_exposure) pairs
            cumulative_times_by_target[target] = target_cumulative
        
        # Get target requirements/goals from the mission configuration
        target_goals = {}
        for target in unique_targets:
            try:
                # Get the target's survey
                target_survey = self.science_mission.get_survey_of_target(target)

                # Get the index of the survey in the mission configuration
                survey_index = self.mission_config.survey_info["Survey"].to_list().index(target_survey.name)

                # Get the exposure time per pointing for the target
                exp_time_per_pointing = self.mission_config.survey_info["ExpTime Per Pointing [s]"][survey_index]

                # Add the target's goal to the dictionary
                target_goals[target] = exp_time_per_pointing
            except (AttributeError, KeyError, ValueError, IndexError) as e:
                # If there's an error getting the goal, output info for debugging
                print(f"Could not get goal for target {target}: {e}")
                # Set a default goal based on achieved value if available
                if cumulative_times_by_target[target] and len(cumulative_times_by_target[target]) > 0:
                    # Fall back to using the achieved value as the goal
                    target_goals[target] = cumulative_times_by_target[target][-1][1]
                else:
                    # Default to a reasonable value if no achievement data
                    target_goals[target] = 600  # 10 minutes in seconds
        
        # Calculate completion percentages
        target_completion_percentages = {}
        total_exposure_time = 0
        
        for target in unique_targets:
            if cumulative_times_by_target[target]:
                final_value = cumulative_times_by_target[target][-1][1]  # Final exposure in seconds
                total_exposure_time += final_value
                
                if target in target_goals and target_goals[target] > 0:
                    # Calculate percentage based on goal
                    target_completion_percentages[target] = (final_value / target_goals[target]) * 100
                else:
                    # No goal defined, set to 100% (fully completed)
                    target_completion_percentages[target] = 100.0
        
        # Store the targets completion data
        self.target_completion = cumulative_times_by_target
        
        # Create figure with main title at the very top and more space at the bottom
        fig = plt.figure(figsize=(12, 9))  # Increased height further to accommodate all elements
        
        # Add the main title outside of any subplot area
        fig.suptitle('Target Observation Completion', fontsize=20, y=0.98)
        
        # Create main plotting axis with proper spacing for title and percentage bars
        ax1 = fig.add_subplot(111)
        plt.subplots_adjust(top=0.82)  # Leave space for percentage bars AND title
        
        # Get the eclipse times
        eclipse_times = []
        for eclipse in self.science_mission.eclipses:
            for i in range(2):
                eclipse_times.append(self.satellite.times.utc_datetime()[eclipse.schedule_indices[i]])
        
        # Highlight eclipse periods without labeling
        for i in range(0, len(eclipse_times), 2):
            if i + 1 < len(eclipse_times):
                start_time = eclipse_times[i]
                end_time = eclipse_times[i + 1]
                
                # Highlight eclipse period without adding text labels
                plt.axvspan(start_time, end_time, color='lightsteelblue', alpha=0.3)
        
        # Create a separate axis for completion percentage bars below the title but above the main plot
        ax2 = fig.add_axes([0.1, 0.85, 0.8, 0.05])  # [left, bottom, width, height]
        
        # Plot each target's cumulative exposure with enhanced styling
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_targets)))
        markers = ['o', 's', '^', 'D', 'v', '<', '>', 'p', '*', 'h']
        
        # Draw the completion percentage bars
        bar_positions = np.arange(len(unique_targets))
        bar_heights = [target_completion_percentages.get(target, 0) for target in unique_targets]
        bar_colors = [colors[i % len(colors)] for i in range(len(unique_targets))]
        
        # Plot percentage bars (capped at 100%)
        capped_bar_heights = [min(h, 100) for h in bar_heights]
        bars = ax2.barh(bar_positions, capped_bar_heights, height=0.6, color=bar_colors, alpha=0.7)
        
        # Add target labels and percentage annotations
        for i, (target, bar) in enumerate(zip(unique_targets, bars)):
            # Add target name at left
            ax2.text(-5, i, target, ha='right', va='center', fontsize=9)
            
            # Add percentage at right of each bar
            completion_pct = target_completion_percentages.get(target, 0)
            bar_width = min(completion_pct, 100)  # Cap display at 100%
            
            if completion_pct > 100:
                # Show overachievement
                label = f"{completion_pct:.0f}% ({(completion_pct-100):.0f}% over)"
                color = 'darkgreen'
            else:
                label = f"{completion_pct:.0f}%"
                color = 'black'
                
            ax2.text(bar_width + 2, i, label, va='center', fontsize=9, color=color)
        
        # Format the percentage axis
        ax2.set_xlim(0, 105)  # Leave space for labels
        ax2.set_ylim(-0.5, len(unique_targets) - 0.5)
        ax2.set_title('Target Completion Percentage', fontsize=12)
        ax2.xaxis.set_ticks([0, 25, 50, 75, 100])
        ax2.yaxis.set_visible(False)  # Hide y-axis labels since we added our own
        ax2.spines['right'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax2.spines['left'].set_visible(False)
        
        # Return to the main axis for the time series
        plt.sca(ax1)
        
        # Plot each target's cumulative exposure over time
        for idx, target in enumerate(unique_targets):
            # Extract time and cumulative values
            times = [pair[0] for pair in cumulative_times_by_target[target]]
            values = [pair[1]/60 for pair in cumulative_times_by_target[target]]  # Convert to minutes
            
            # Plot the step function
            plt.step(times, values, where='post', 
                    label=f"{target}", 
                    linewidth=2.5, 
                    color=colors[idx % len(colors)],
                    marker=markers[idx % len(markers)],
                    markersize=6,
                    markevery=max(1, len(times)//8))  # Show markers periodically
        
        # Enhance the plot formatting
        plt.ylabel('Cumulative Exposure Time (minutes)', fontsize=15)
        plt.xlabel('UTC Time', fontsize=15)
        # Improve x-axis labels for better readability
        plt.xticks(ha='right')
        # ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d-%y, %H:%M:%S'))
        
        # Add some padding to ensure x-axis labels are visible
        ax1.tick_params(axis='x', pad=8)
        ax1.set_xlabel('UTC Time', fontsize=15, labelpad=15)  # Increased labelpad
        plt.grid(linestyle='--', alpha=0.4)
        
        # Create a better legend
        legend = plt.legend(title="Observation Targets", 
                        loc='upper left', 
                        fontsize=10,
                        framealpha=0.9)
        legend.get_title().set_fontsize(12)
        
        # Add final exposure time annotations at the end of each line
        last_times = {}
        last_values = {}
        
        for target in unique_targets:
            if cumulative_times_by_target[target]:
                last_times[target] = cumulative_times_by_target[target][-1][0]
                last_values[target] = cumulative_times_by_target[target][-1][1]/60  # Minutes
        
        # Stagger annotations to avoid overlap
        targets_by_final_time = sorted(unique_targets, key=lambda t: last_times[t])
        stagger_offset = 0
        
        for idx, target in enumerate(targets_by_final_time):
            plt.annotate(f"{last_values[target]:.1f} min", 
                        xy=(last_times[target], last_values[target]),
                        xytext=(10, 5 + stagger_offset),
                        textcoords="offset points",
                        fontsize=9,
                        color=colors[unique_targets.index(target) % len(colors)],
                        weight='bold')
            stagger_offset = (stagger_offset + 15) % 60  # Cycle through offsets
        
        # Calculate summary statistics for targets
        summary_data = {}
        total_minutes = 0
        completion_percentages = []
        
        for target in unique_targets:
            if cumulative_times_by_target[target]:
                final_value = cumulative_times_by_target[target][-1][1]/60  # Minutes
                completion_pct = target_completion_percentages.get(target, 0)
                summary_data[target] = (final_value, completion_pct)
                total_minutes += final_value
                completion_percentages.append(completion_pct)
        
        # Calculate overall statistics
        avg_completion = sum(completion_percentages) / len(completion_percentages) if completion_percentages else 0
        
        # Create a summary table at the bottom of the plot instead of in a text box
        # Adjust the main plot to make room at the bottom
        plt.subplots_adjust(bottom=0.25)
        
        # Position the summary table with more space between it and the main plot
        summary_ax = fig.add_axes([0.1, 0.02, 0.8, 0.15])  # Lower position for summary table
        summary_ax.axis('off')  # Hide axis
        
        # Create table data
        table_data = []
        for target, (time, pct) in summary_data.items():
            table_data.append([target, f"{time:.1f} min", f"{pct:.0f}%"])
        
        # Add totals row
        table_data.append(["Total", f"{total_minutes:.1f} min", f"{avg_completion:.0f}% avg"])
        
        # Create the table
        table = summary_ax.table(
            cellText=table_data,
            colLabels=["Target", "Observation Time", "Completion"],
            loc='center',
            cellLoc='center',
            colWidths=[0.4, 0.3, 0.3]
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)  # Adjust table size
        
        # Highlight the total row
        for j in range(3):
            cell = table[(len(table_data), j)]
            cell.set_facecolor('lightgray')
            cell.set_text_props(weight='bold')
        
        # Set up the layout with precise control over spacing
        plt.tight_layout()
        
        # Apply specific adjustments to ensure all elements are visible
        plt.subplots_adjust(
            top=0.82,      # Space for title and percentage bars at top
            bottom=0.25,   # Significant space for x-axis labels and summary table
            left=0.10,     # Left margin
            right=0.95     # Right margin
        )
        plt.show()
        
        # Print summary information
        print("-----Targets Observed in Order-----")
        for target in unique_targets:
            if cumulative_times_by_target[target]:
                final_value = cumulative_times_by_target[target][-1][1]/60  # Minutes
                completion_pct = target_completion_percentages.get(target, 0)
                print(f"{target} = {final_value:.2f} min ({completion_pct:.1f}%)")

    def plot_mission_overview(self):
        """
        Creates a bar chart overview of the mission schedule, showing time allocation for
        different mission activities including target observations.
        
        This function maintains the original style and functionality while handling
        the new target completion data structure.
        """
        # Retrieve mission schedule data
        mission_schedule = self.get_operation_by_name('Final Operations Schedule').status

        # Extract subcategories and process mission schedule data
        schedule_counter = Counter(mission_schedule)
        time_conversion = self.satellite.time_step_sec / 60
        subcategories = [status.name for status in MissionStatus if status.name != "TARGET1"]
        data = np.array([[schedule_counter.get(status.value, 0) * time_conversion for status in MissionStatus if status.name != "TARGET1"]], dtype=int)

        # Include target completion data with fixed handling for the new data structure
        for target_name, observation_data in self.target_completion.items():
            if observation_data:  # Make sure there's data for this target
                # Extract the final cumulative exposure time (in minutes)
                # In the new structure, each entry is a (time, cumulative_exposure) tuple
                final_exposure_min = observation_data[-1][1] / 60
                
                # Add to our data arrays
                subcategories.append(f'TARGET: {target_name}')
                data = np.append(data, [[final_exposure_min]], axis=1)

        # Compute statistics and filter data
        total_counts = np.sum(data)  # Total of all values in data
        percentages = (data / total_counts * 100).flatten()
        valid_indices = percentages > 0
        subcategories = np.array(subcategories)[valid_indices].tolist()
        data = data[:, valid_indices]
        percentages = percentages[valid_indices]

        # Sort data by percentage
        sorted_indices = np.argsort(percentages)[::-1]
        subcategories = [subcategories[i] for i in sorted_indices]
        data = data[:, sorted_indices]
        percentages = percentages[sorted_indices]

        # Assign colors
        bar_colors = [MissionStatus.plot_color(MissionStatus.TARGET1.value) if sub.startswith("TARGET:") else MissionStatus.plot_color(MissionStatus.get_value(sub)) for sub in subcategories]

        # Create figure with improved size for better readability
        fig, ax = plt.subplots(figsize=(12, 7))
        bars = ax.bar(subcategories, data[0], color=bar_colors)
        ax.set_ylabel('Time in minutes', fontsize=12)
        ax.set_title('Mission Schedule Overview', fontsize=16)
        ax.set_xticklabels(subcategories, rotation=30, ha='right')
        ax.set_ylim(0, max(data[0]) + 100)
        plt.grid(alpha=0.2)

        # Add labels
        for bar, value, pct in zip(bars, data[0], percentages):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2, 
                    f'{value:.0f}\n({pct:.1f}%)', 
                    ha='center', va='bottom', fontsize=10, color='black')

        # Add a title with total mission time
        total_minutes = total_counts  # total_counts is already a scalar
        total_hours = total_minutes / 60
        plt.figtext(0.5, 0.01, f'Total Mission Time: {total_minutes:.1f} minutes ({total_hours:.2f} hours)', 
                ha='center', fontsize=12)

        plt.tight_layout()
        plt.show()

    def get_data_storage_plot(self):
        """
            Generates a plot of data storage over time based on target observations and downlinks.


            Args:
                file_path: The path to the Excel file containing data budget information.
                sheet_name: The name of the sheet within the Excel file.
                actions_list: A linked list of actions.
                plan: The overall plan object.


            Returns:
                None (The function generates a plot but doesn't return a value).
        """
    
        # Get the data budget information
        data_budget_dict = Helpers.get_data_dict(self.mission_config)

        # Loop through the actions
        current_node = self.commands_list.head_node
    
        # Get the variables ready
        initial_data_size = data_budget_dict['INITIAL_DATA_SIZE']
        data_size = [initial_data_size]
        data_size_time = [current_node.getData().getTime()]

        # Get the eclipse objects
        eclipses = self.science_mission.eclipses

        while current_node:

            # Get the key for the current node
            action = current_node.getData()
            action_key = action.getKey()

            # if action_key not in [None, 'DOWNTIME', 'CHARGING', 'OBSERVING', 'SLEWING', 'DOWNLINK', 'SAA', 'POLAR']:
            if any(target in action_key for target in ["TARGET1", "TARGET2"]):

                # Get the new data size
                new_data_size = self.getNewDataSize(action, data_budget_dict, eclipses) * action.getDuration().total_seconds()
                new_data_size = data_size[-1] + new_data_size

                # Update the data size
                data_size.append(new_data_size)
                data_size_time.append(action.getTime())

            elif action_key == 'DOWNLINK':

                # Get the downlink information
                action_time = action.getTime()
                action_duration = action.getDuration()

                # Get the downlinked data size
                downlinked_data_size = action_duration.total_seconds() * data_budget_dict['DOWNLINK_RATE']
                final_data_size = data_size[-1] - downlinked_data_size


                # Update the data size
                data_size.append(max(final_data_size, 0))  # Ensure non-negative data size
                data_size_time.append(action_time)

            # Move to the next node
            current_node = current_node.getNextNode()

        # Plot the data
        eclipse_times = []
        for eclipse in self.science_mission.eclipses:
            for i in range(2):
                eclipse_times.append(self.satellite.times.utc_datetime()[eclipse.schedule_indices[i]])
        self.plot_data_storage(data_size_time, data_size, eclipse_times)

    def getNewDataSize(self, action, data_budget_dict, eclipses):
        """
            Calculates the new data size based on the target, target exposure mode, and data budget.


            Args:
                plan: The overall plan object.
                action: The current action being executed.
                data_budget_dict: A dictionary mapping exposure modes to data sizes.
                eclipses: A collection of eclipse objects.


            Returns:
                The new data size corresponding to the target exposure mode.
        """

        # Get the targets observed names and eclipse
        eclipse = eclipses[action.getEclipseNum()]
        # target_names = list(eclipse.getTargetsObserved().keys())
        target_names = eclipse.targets_names
        action_key = action.getKey()
        if "TARGET1" in action_key:
            target_index = 0
        elif "TARGET2" in action_key:
            target_index = 1
        else:
            target_index = None

        # Get the target index
        # target_index = {'TARGET1': 0, 'TARGET2': 1}.get(action_key)
        if target_index is None:
            raise ValueError(f"Invalid action key: {action.getKey()}")

        # Get the exposure mode of the target
        target_name = target_names[target_index]
        # target = self.science_mission.get_target_by_name(target_name)
        survey = self.science_mission.get_survey_of_target(target_name)
        exposure_mode = survey.obs_mode

        # Get the new data size
        new_data_size = data_budget_dict.get(exposure_mode)
        if new_data_size is None:
            raise ValueError(f"Exposure mode '{exposure_mode}' not found in data budget")

        return new_data_size

    def plot_data_storage(self, x, y, eclipse_times):
        """
        Creates an enhanced visualization of onboard data storage over time.
        
        This function plots the satellite's onboard file size throughout the mission,
        with visual indicators for eclipse periods, downlink events, and storage thresholds.
        
        Args:
            x (list): List of datetime objects representing time points
            y (list): List of file sizes in MB at each time point
            eclipse_times (list): List of datetime objects marking eclipse start/end times
            
        Returns:
            None (displays the plot)
        """
        # Create figure with improved size for better readability
        fig = plt.figure(figsize=(12, 8))  # Increased height to accommodate table at bottom
        
        # Create primary axis for data storage
        ax = plt.gca()
        
        # Plot title with more descriptive information
        plt.title('Onboard Data Storage Utilization', fontsize=20, pad=15)
        
        # Calculate some statistics for annotations
        max_storage = max(y)
        final_storage = y[-1]
        peak_idx = y.index(max_storage)
        peak_time = x[peak_idx]
        
        # Identify potential downlink events (where data size decreases)
        downlink_indices = []
        downlink_amounts = []
        for i in range(1, len(y)):
            if y[i] < y[i-1]:
                downlink_indices.append(i)
                downlink_amounts.append(y[i-1] - y[i])
        
        # Plot the main data storage line with improved styling
        plt.plot(x, y, 
                drawstyle='steps-post', 
                color='#FF5003',
                linewidth=3,
                label='Onboard Data')
        
        # Plot the eclipses
        for i in range(0, len(eclipse_times), 2):
            if i + 1 < len(eclipse_times):
                start_time = eclipse_times[i]
                end_time = eclipse_times[i + 1]
                
                # Highlight eclipse period
                plt.axvspan(start_time, end_time, color='lightsteelblue', alpha=0.3)
        
        # Add reference lines for storage thresholds
        plt.axhline(y=max_storage, color='k', linestyle='--', alpha=0.7, 
                    label=f'Peak Storage ({max_storage:.1f} MB)')
        
        # Create a summary table at the bottom of the plot instead of figtext
        plt.subplots_adjust(bottom=0.25)  # Make room for the table
        
        # Create summary table data
        summary_data = []
        if downlink_indices:
            # Calculate average collection rate
            slopes = []
            for i in range(1, len(y)):
                if y[i] > y[i-1]:  # Only measure positive slopes (data collection)
                    time_diff = (x[i] - x[i-1]).total_seconds()
                    if time_diff > 0:
                        data_rate = (y[i] - y[i-1]) / time_diff * 60  # MB per minute
                        slopes.append(data_rate)
            
            avg_collection_rate = sum(slopes) / len(slopes) if slopes else 0
            total_downlinked = sum(downlink_amounts)
            
            # Add rows to the summary table
            summary_data.append(["Final Size", f"{final_storage:.2f} MB"])
            summary_data.append(["Peak Size", f"{max_storage:.2f} MB"])
            summary_data.append(["Avg. Collection Rate", f"{avg_collection_rate:.2f} MB/min"])
            summary_data.append(["Total Downlinked", f"{total_downlinked:.2f} MB"])
            summary_data.append(["Downlink Events", f"{len(downlink_indices)}"])
        else:
            summary_data.append(["Final Size", f"{final_storage:.2f} MB"])
            summary_data.append(["Peak Size", f"{max_storage:.2f} MB"])
        
        # Create a new axis for the summary table
        summary_ax = fig.add_axes([0.15, 0.02, 0.7, 0.15])  # [left, bottom, width, height]
        summary_ax.axis('off')  # Hide axis
        
        # Create the table
        table = summary_ax.table(
            cellText=summary_data,
            colLabels=["Metric", "Value"],
            loc='center',
            cellLoc='center',
            colWidths=[0.4, 0.4]
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.5)  # Adjust table size
        
        # Add a header row with different styling
        for j in range(2):
            cell = table[(0, j)]
            cell.set_facecolor('lightgray')
            cell.set_text_props(weight='bold')
        
        # Improve axis labels and formatting
        plt.ylabel('Lasting Data Size [MB]', fontsize=15, labelpad=10)
        plt.xlabel('Time in UTC', fontsize=15, labelpad=10)
        
        # Enhanced grid
        plt.grid(which='both', linestyle='--', linewidth=0.2)
        
        # Format x-axis with improved date formatting
        # x_fmt = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
        # ax.xaxis.set_major_formatter(x_fmt)
        # plt.xticks(rotation=45)
        
        # Add legend with custom positioning
        plt.legend(loc='upper left', fontsize=9)
        
        # Plot margins and layout
        plt.tight_layout()
        plt.subplots_adjust(bottom=0.25)  # Ensure there's room for the table
        
        # Show the plot
        plt.show()

    def _plot_operations(self, num_plots = 1):

        # Get the operations schedule and the satellite times
        operations_schedule_bp = self.get_operation_by_name("Before Pointing Operations Schedule").status
        operations_schedule_ap = self.get_operation_by_name("Final Operations Schedule").status
        times = self.satellite.times.utc_datetime()

        # Split the full timeline into exactly num_plots equal chunks
        chunks = np.array_split(np.arange(len(times)), num_plots)

        for chunk in chunks:
            xlim_start = chunk[0]
            xlim_end = chunk[-1]

            # Initialize the plot
            fig, ax = plt.subplots(2, 1, figsize=(24, 6))

            # Plot the operations schedule before pointing
            ax[0].plot(times, operations_schedule_bp, drawstyle = 'steps-mid')
            for eclipse in self.science_mission.eclipses:
                eclipse_start = eclipse.schedule_indices[0]
                eclipse_end = eclipse.schedule_indices[1]
                ax[0].axvspan(times[eclipse_start], times[eclipse_end], color='lightsteelblue', alpha=0.3)

            ax[0].set_yticks([status.value for status in MissionStatus], labels=[status.name for status in MissionStatus])
            ax[0].set_xticks([0])

            for status in MissionStatus:
                ax[0].plot(times[operations_schedule_bp == status.value], operations_schedule_bp[operations_schedule_bp == status.value], color = MissionStatus.plot_color(status.value), marker = 's', linestyle='')

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

            ax[1].set_yticks([status.value for status in MissionStatus], labels=[status.name for status in MissionStatus])

            for status in MissionStatus:
                ax[1].plot(times[operations_schedule_ap == status.value], operations_schedule_ap[operations_schedule_ap == status.value], color = MissionStatus.plot_color(status.value), marker = 's', linestyle='')

            ax[1].set_ylabel("Status", fontsize = 25)
            ax[1].set_xlabel("Time in UTC", fontsize = 25)
            ax[1].tick_params(labelsize = 16)
            ax[1].set_xlim(times[xlim_start], times[xlim_end])
            ax[1].set_title('Schedule After Pointing Allocation', fontsize = 30)
            ax[1].grid(True)
            
            fig.tight_layout()
            date_format = mdates.DateFormatter('%m-%d-%y, %H:%M:%S')
            ax[0].xaxis.set_major_formatter(date_format)
            ax[1].xaxis.set_major_formatter(date_format)
            for tick in ax[0].get_xticklabels():
                tick.set_rotation(15)
            for tick in ax[1].get_xticklabels():
                tick.set_rotation(15)
            fig.tight_layout()
            plt.show()

    def plot_eclipse_summary(self, eclipse_num: int, operations_schedule=None):

        # Get the data for the eclipse
        eclipse = self.science_mission.eclipses[eclipse_num]
        eclipse_schedule = eclipse.operations.status
        eclipse_start = eclipse.schedule_indices[0]
        eclipse_end = eclipse.schedule_indices[1]
        times = eclipse.operations.time.utc_datetime()

        # Use provided schedule, or fall back to Final, then Before Pointing
        if operations_schedule is None:
            final_schedule_obj = self.get_operation_by_name("Final Operations Schedule")
            if final_schedule_obj is None:
                final_schedule_obj = self.get_operation_by_name("Before Pointing Operations Schedule")
            operations_schedule = final_schedule_obj.status
        final_operations_in_eclipse = Helpers.inclusive_slice(operations_schedule, eclipse_start, eclipse_end)

        # Create a 2x2 subplot grid
        fig = plt.figure(figsize=(15, 12))
        
        # Define the grid layout
        gs = gridspec.GridSpec(2, 2, figure=fig)
        
        # Create subplots with specific positions in the grid
        ax_ops = fig.add_subplot(gs[0, 0])        # Operations Schedule
        ax_track = fig.add_subplot(gs[0, 1], projection=ccrs.PlateCarree())  # Groundtrack
        ax_target = fig.add_subplot(gs[1, 0])     # Target Altitude
        ax_moon = fig.add_subplot(gs[1, 1])       # Moon Altitude

        # Plot the target(s)'s altitudes
        colors = ['lightcoral', 'gold']
        target_names = []
        i = 0
        for i, target_name in enumerate(eclipse.targets_names):
            target = self.science_mission.get_target_by_name(target_name)
            target_altitude = Helpers.inclusive_slice(target.target_altitude, eclipse_start, eclipse_end)
            target_names.append(target_name)

            ax_target.plot(times, target_altitude, '--', color=colors[i], label=f'Target: {target.name}')
        
        if i == 0:
            ax_target.set_title(f'Target Altitude Throughout Eclipse {eclipse_num}')
        else:
            ax_target.set_title(f"Targets' Altitude Throughout Eclipse {eclipse_num}")
        ax_target.axhline(y=90 - self.satellite.earth_constraint, color='firebrick', label=f'Earth Angle Constraint: {self.satellite.earth_constraint:.2f}°')
        ax_target.legend(loc='best')
        ax_target.set_xlabel('Time in UTC')
        ax_target.set_ylabel('Target Altitude in Degrees')
        ax_target.tick_params(axis='x', rotation=25)
        ax_target.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))
        ax_target.grid(alpha=0.3)

        # Plot the moon's altitudes
        moon_altitude = Helpers.inclusive_slice(self.satellite.moon_altitudes, eclipse_start, eclipse_end)
        ax_moon.plot(times, moon_altitude, '--', color='yellowgreen')
        ax_moon.axhline(y=self.satellite.moon_constraint, color='olivedrab', label=f'Altitude (Moon) Constraint: {self.satellite.moon_constraint:.2f}')
        ax_moon.set_title(f'Moon Altitude Throughout Eclipse {eclipse_num}')
        ax_moon.legend(loc='best')
        ax_moon.set_xlabel('Time in UTC')
        ax_moon.set_ylabel('Moon Altitude in Degrees')
        ax_moon.grid(alpha=0.3)
        ax_moon.tick_params(axis='x', rotation=25)
        ax_moon.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))

        # Plot the operations schedule
        ax_ops.plot(times, eclipse_schedule, drawstyle='steps-mid')
        for i, status in enumerate(MissionStatus):
            ax_ops.plot(times[eclipse_schedule == status.value], eclipse_schedule[eclipse_schedule == status.value], 
                        marker='s', linestyle='', color=MissionStatus.plot_color(status.value))
        if len(eclipse.targets_names) > 0:
            ax_ops.plot([], [], label=f'Target 1 = {eclipse.targets_names[0]}. Exp Time = {eclipse.targets_exp_times[0]}s', 
                    color='firebrick')
            if eclipse.targets_exp_times[0] != np.sum(eclipse_schedule == MissionStatus.TARGET1.value) * self.satellite.time_step_sec:
                raise ValueError(f'The target 1 exposure time {eclipse.targets_exp_times[0]} does not match the number of slots allocated to the target {np.sum(eclipse_schedule == MissionStatus.TARGET1.value) * self.satellite.time_step_sec}')
            if np.any(eclipse_schedule == MissionStatus.TARGET2.value):
                ax_ops.plot([], [], label=f'Target 2 = {eclipse.targets_names[1]}. Exp Time = {eclipse.targets_exp_times[1]}s', 
                        color='darkgoldenrod')
                if eclipse.targets_exp_times[1] != np.sum(eclipse_schedule == MissionStatus.TARGET2.value) * self.satellite.time_step_sec:
                    raise ValueError(f'The target 2 exposure time {eclipse.targets_exp_times[1]} does not match the number of slots allocated to the target {np.sum(eclipse_schedule == MissionStatus.TARGET2.value) * self.satellite.time_step_sec}')
        ax_ops.legend(loc='best')
        ax_ops.set_yticks([status.value for status in MissionStatus])
        ax_ops.set_yticklabels([status.name for status in MissionStatus])
        ax_ops.tick_params(axis='x', rotation=25)
        ax_ops.grid(alpha=0.3)
        ax_ops.set_xlabel('Time [UTC]')
        ax_ops.set_ylabel('Visibility Status')
        ax_ops.set_title(f'Eclipse {eclipse_num} Operations Schedule')
        ax_ops.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d, %H:%M'))

        # Plot the groundtrack
        ax_track.coastlines()

        # Plot the groundtrack
        plot_lat, plot_lon = self._insert_plot_nans(Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end), 
                                                Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end))
        ax_track.plot(plot_lon, plot_lat, color=MissionStatus.plot_color(), linewidth=1)

        # Plot the SAA groundtrack coordinates and area
        saa_lat_area, saa_lon_area = self._insert_plot_nans(self.satellite.saa_latitudes_area, self.satellite.saa_longitudes_area)
        ax_track.plot(saa_lon_area, saa_lat_area, color=MissionStatus.plot_color(MissionStatus.SAA.value), linewidth=6)

        saa_path = Path(list(zip(self.satellite.saa_longitudes_area, self.satellite.saa_latitudes_area)))
        in_saa = saa_path.contains_points(list(zip(plot_lon, plot_lat)))

        saa_lat = plot_lat[in_saa]
        saa_lon = plot_lon[in_saa]
        ax_track.plot(saa_lon, saa_lat, color=MissionStatus.plot_color(MissionStatus.SAA.value), linewidth=6)

        # Plot the polar keepout (pk) coordinates
        pk_upper_lim = 90 - self.satellite.polar_constraint
        pk_latitude_upper = plot_lat[plot_lat > pk_upper_lim]
        pk_longitude_upper = plot_lon[plot_lat > pk_upper_lim]
        ax_track.plot(pk_longitude_upper, pk_latitude_upper, color=MissionStatus.plot_color(MissionStatus.POLAR.value), linewidth=6)

        pk_lower_lim = -90 + self.satellite.polar_constraint
        pk_latitude_lower = plot_lat[plot_lat < pk_lower_lim]
        pk_longitude_lower = plot_lon[plot_lat < pk_lower_lim]
        ax_track.plot(pk_longitude_lower, pk_latitude_lower, color=MissionStatus.plot_color(MissionStatus.POLAR.value), linewidth=6)

        # Plot the ground station accesses
        downlink_schedule = Helpers.inclusive_slice(self.get_schedule_by_name("Ground Stations Schedule").status, eclipse_start, eclipse_end)
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[downlink_schedule] 
        filtered_lon = raw_lon[downlink_schedule]
        gs_lat, gs_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(gs_lon, gs_lat, color=MissionStatus.plot_color(MissionStatus.DOWNLINK.value), linewidth=6)

        # Plot pointing
        pointing_schedule = final_operations_in_eclipse == MissionStatus.SLEWING.value
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[pointing_schedule] 
        filtered_lon = raw_lon[pointing_schedule]
        pointing_lat, pointing_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(pointing_lon, pointing_lat, color=MissionStatus.plot_color(MissionStatus.SLEWING.value), linewidth=6)

        # Plot target 1
        target1_schedule = final_operations_in_eclipse == MissionStatus.TARGET1.value
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[target1_schedule] 
        filtered_lon = raw_lon[target1_schedule]
        target1_lat, target1_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(target1_lon, target1_lat, MissionStatus.plot_color(MissionStatus.TARGET1.value), linewidth=6)

        # Plot target 2
        target2_schedule = final_operations_in_eclipse == MissionStatus.TARGET2.value
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[target2_schedule] 
        filtered_lon = raw_lon[target2_schedule]
        target2_lat, target2_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(target2_lon, target2_lat, color=MissionStatus.plot_color(MissionStatus.TARGET2.value), linewidth=6)

        # Plot charging
        charging_schedule = final_operations_in_eclipse == MissionStatus.CHARGING.value
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[charging_schedule] 
        filtered_lon = raw_lon[charging_schedule]
        charging_lat, charging_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(charging_lon, charging_lat, color=MissionStatus.plot_color(MissionStatus.CHARGING.value), linewidth=6)

        # Plot downtime
        downtime_schedule = final_operations_in_eclipse == MissionStatus.DOWNTIME.value
        raw_lat = Helpers.inclusive_slice(self.satellite.latitudes, eclipse_start, eclipse_end)
        raw_lon = Helpers.inclusive_slice(self.satellite.longitudes, eclipse_start, eclipse_end)
        filtered_lat = raw_lat[downtime_schedule] 
        filtered_lon = raw_lon[downtime_schedule]
        downtime_lat, downtime_lon = self._insert_plot_nans(filtered_lat, filtered_lon)
        ax_track.plot(downtime_lon, downtime_lat, color=MissionStatus.plot_color(MissionStatus.DOWNTIME.value), linewidth=6)

        ax_track.set_xlim([min(plot_lon) - 15, max(plot_lon) + 15])
        ax_track.set_ylim([min(plot_lat) - 15, max(plot_lat) + 15])
        ax_track.grid(alpha=0.3)
        ax_track.xaxis.set_major_formatter(LongitudeFormatter())
        ax_track.yaxis.set_major_formatter(LatitudeFormatter())
        ax_track.set_title(f'Eclipse {eclipse_num} Groundtrack')

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
            print_dict['Lat of Start of Exposure'] = self.satellite.latitudes[eclipse.schedule_indices[0] + (eclipse.operations.status == MissionStatus.TARGET1)[0]]
            print_dict['Lon of Start of Exposure'] = self.satellite.longitudes[eclipse.schedule_indices[0] + (eclipse.operations.status == MissionStatus.TARGET1)[0]]
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

    def plot_satellite_positions(self) -> None:
        """
        Plot the positions of the satellite over the specified time interval.
        """
        # Get the operations schedule
        operations_schedule = self.get_operation_by_name("Final Operations Schedule").status

        # Initialize the plot
        plt.figure(figsize=(12, 6))
        ax = plt.axes(projection=ccrs.PlateCarree())
        ax.stock_img()
        ax.coastlines()

        # Plot the groundtrack
        plot_lat, plot_lon = self._insert_plot_nans(self.satellite.latitudes, self.satellite.longitudes)
        ax.plot(plot_lon, plot_lat, color = 'lightslategrey', linewidth = 1)

        # Plot the SAA area
        saa_lat_area, saa_lon_area = self._insert_plot_nans(self.satellite.saa_latitudes_area, self.satellite.saa_longitudes_area)
        ax.plot(saa_lon_area, saa_lat_area, color = MissionStatus.plot_color(MissionStatus.SAA.value), linewidth = 1)

        # Plot the SAA groundtrack coordinates
        saa_lat, saa_lon = self._insert_plot_nans(self.satellite.saa_latitudes, self.satellite.saa_longitudes)
        ax.plot(saa_lon, saa_lat, color = MissionStatus.plot_color(MissionStatus.SAA.value), linewidth = 1)

        # Plot the polar keepout (pk) coordinates
        pk_upper_lim = 90 - self.satellite.polar_constraint
        pk_latitude_upper = self.satellite.latitudes[self.satellite.latitudes > pk_upper_lim]
        pk_longitude_upper = self.satellite.longitudes[self.satellite.latitudes > pk_upper_lim]
        pk_latitude_upper, pk_longitude_upper = self._insert_plot_nans(pk_latitude_upper, pk_longitude_upper)
        ax.plot(pk_longitude_upper, pk_latitude_upper, color = MissionStatus.plot_color(MissionStatus.POLAR.value), linewidth = 1)

        pk_lower_lim = -90 + self.satellite.polar_constraint
        pk_latitude_lower = self.satellite.latitudes[self.satellite.latitudes < pk_lower_lim]
        pk_longitude_lower = self.satellite.longitudes[self.satellite.latitudes < pk_lower_lim]
        pk_latitude_lower, pk_longitude_lower = self._insert_plot_nans(pk_latitude_lower, pk_longitude_lower)
        ax.plot(pk_longitude_lower, pk_latitude_lower, color = MissionStatus.plot_color(MissionStatus.POLAR.value), linewidth = 1)
        
        # Plot the pointing 
        pointing_schedule = operations_schedule == MissionStatus.SLEWING.value
        pointing_lat, pointing_lon = self._insert_plot_nans(self.satellite.latitudes[pointing_schedule], self.satellite.longitudes[pointing_schedule])
        ax.plot(pointing_lon, pointing_lat, color = MissionStatus.plot_color(MissionStatus.SLEWING.value), linewidth = 4)

        # Plot the ground station accesses
        downlink_schedule = self.get_schedule_by_name("Ground Stations Schedule")
        gs_lat, gs_lon = self._insert_plot_nans(self.satellite.latitudes[downlink_schedule.status], self.satellite.longitudes[downlink_schedule.status])                
        ax.plot(gs_lon, gs_lat, color = MissionStatus.plot_color(MissionStatus.DOWNLINK.value), linewidth = 4)

        # Plot target exposures
        target1_schedule = operations_schedule == MissionStatus.TARGET1.value
        target2_schedule = operations_schedule == MissionStatus.TARGET2.value
        target1_lat, target1_lon = self._insert_plot_nans(self.satellite.latitudes[target1_schedule], self.satellite.longitudes[target1_schedule])
        target2_lat, target2_lon = self._insert_plot_nans(self.satellite.latitudes[target2_schedule], self.satellite.longitudes[target2_schedule])
        ax.plot(target1_lon, target1_lat, color = MissionStatus.plot_color(MissionStatus.TARGET1.value), linewidth = 4)
        ax.plot(target2_lon, target2_lat, color = MissionStatus.plot_color(MissionStatus.TARGET2.value), linewidth = 4)

        plt.title('Groundtrack for MANTIS on Sample Day', fontsize = 20)
        if os.path.exists('./Plots'):
            plt.savefig(fname = './Plots/Groundtrack.png', dpi = 100)
            plt.show()
        else:
            os.mkdir('./Plots')
            plt.savefig(fname = './Plots/Groundtrack.png', dpi = 100)
            plt.show()

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
    
    def plot_target_visibility_heatmap(self, target_name: str):
        """
        Check the visibility of an input target for the simulation period and generate a
        heatmap of visibility in minutes per day with day of week and date axes.
        
        Args:
            target_name (str): The name of the target to check visibility for.
        Returns:
            None (displays the heatmap)
        """
        # Find the target
        target = self.science_mission.get_target_by_name(target_name)
        # Get the schedule for the target in the mission
        target_schedule = target.schedule.status
        # Initialize a DataFrame to store visibility data
        visibility_data = pd.DataFrame(columns=['Date', 'Visibility'])
        
        # Calculate visibility for each day of the simulation period
        start_date = pd.to_datetime(self.satellite.start_time).tz_localize(None)
        end_date = pd.to_datetime(self.satellite.end_time).tz_localize(None)
        current_date = start_date
        
        while current_date <= end_date:
            # Get the indices for the current day
            day_start_index = np.searchsorted(pd.to_datetime(self.satellite.times.utc_datetime()).tz_localize(None), current_date)
            day_end_index = np.searchsorted(pd.to_datetime(self.satellite.times.utc_datetime()).tz_localize(None), current_date + timedelta(days=1)) - 1
            
            # Calculate visibility for the current day
            day_visibility = np.sum(target_schedule[day_start_index:day_end_index + 1]) * self.satellite.time_step_sec / 60  # in minutes
            
            # Append the data to the DataFrame
            visibility_data = pd.concat([visibility_data, pd.DataFrame({'Date': [current_date], 'Visibility': [day_visibility]})], ignore_index=True)
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        # Convert the 'Date' column to datetime
        visibility_data['Date'] = pd.to_datetime(visibility_data['Date'])
        
        # Extract components from dates
        visibility_data['DateStr'] = visibility_data['Date'].dt.strftime('%b %d')  # e.g., "Jun 15"
        visibility_data['DayOfWeek'] = visibility_data['Date'].dt.dayofweek  # Monday=0, Sunday=6
        
        # Define weeks properly to handle month transitions
        # Start with the first Monday before or on the start date
        first_monday = start_date - timedelta(days=start_date.weekday())
        if first_monday > start_date:  # If start_date is before Monday, go back one more week
            first_monday = first_monday - timedelta(days=7)
        
        # Assign week numbers based on this reference Monday
        visibility_data['Week'] = ((visibility_data['Date'] - first_monday).dt.days // 7)
        
        # Create pivot table with day of week as rows and weeks as columns
        heatmap_data = visibility_data.pivot_table(
            index='DayOfWeek',
            columns='Week',
            values='Visibility',
            aggfunc='first'
        )
        
        # Get date ranges for each week for column labels
        week_labels = []
        for week in sorted(visibility_data['Week'].unique()):
            # Get dates that fall within this week in our data
            week_data = visibility_data[visibility_data['Week'] == week]
            if not week_data.empty:
                # Convert numpy.int64 to standard Python int
                week_num = int(week)
                # Find the Monday of this week (might not be in our data)
                week_monday = first_monday + timedelta(days=week_num*7)
                week_sunday = week_monday + timedelta(days=6)
                
                # Format the date strings - include month names for clarity across month transitions
                monday_str = week_monday.strftime('%b %d')
                sunday_str = week_sunday.strftime('%b %d')
                
                week_labels.append(f"{monday_str} - {sunday_str}")
            else:
                week_labels.append(f"Week {int(week)}")
        
        # Create the heatmap
        plt.figure(figsize=(14, 8))
        ax = sns.heatmap(heatmap_data.astype(float), cmap='YlGnBu', annot=True, fmt=".1f", linewidths=.5)
        
        # Set labels
        plt.title(f'Visibility of {target_name} in Minutes per Day')

        # Set y-axis (day of week) labels
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        plt.yticks(np.arange(len(day_names)) + 0.5, day_names)
        
        # Set x-axis (week) labels
        plt.xticks(np.arange(len(week_labels)) + 0.5, week_labels, rotation=45, ha='right')
        
        plt.xlabel('Week')
        plt.ylabel('Day of Week')
        plt.tight_layout()
        plt.show()
        
        return visibility_data  # Return the data for further analysis if needed

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