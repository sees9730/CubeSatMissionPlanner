from typing import List, Type, Dict
from PlanningObjects.Satellite import Satellite
from PlanningObjects.MissionConfig import MissionConfig

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

    def __init__(self, excel_file_path: str):
                #  science_mission: 'ScienceMission',
                #  mission_config: 'MissionConfig',
                #  satellite: 'Satellite',
                #  ground_stations: List['GroundStation'],
                #  visibilities: 'Schedule',
                #  operations: 'Schedule'):

        # Initialize a new CubeSatMission object
        self.mission_config = self._createMissionConfig(excel_file_path)
        self.satellite = self._createSatellite()
        self.science_mission = None
        self.ground_stations = []
        self.visibilities = None
        self.operations = None

    def _createMissionConfig(self, excel_file_path: str):
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
        return MissionConfig(excel_file_path)
    
    def _createSatellite(self) -> Satellite:
        """
        Create a new Satellite object based on the data in the plan_info DataFrame.
        
        Returns
        -------
        Satellite
            A new Satellite object with the data from the plan_info DataFrame.
        """
        return Satellite(self.mission_config.plan_info['TLE URL'].values[0],
                         self.mission_config.plan_info['TLE File'].values[0],
                         self.mission_config.plan_info['Satellite Name'].values[0],
                         self.mission_config.plan_info['Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.mission_config.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.mission_config.plan_info['Timestep [sec]'].values[0])

        
    def __repr__(self) -> str:
        """
        TODO: CHANGE THE OUTPUT TO SOMETHING USEFUL
        """
        return (f"CubeSatMission(science_mission={self.science_mission}, "
                f"mission_config={self.mission_config}, "
                f"satellite={self.satellite}, "
                f"ground_stations={self.ground_stations}, "
                f"visibilities={self.visibilities}, "
                f"operations={self.operations})")