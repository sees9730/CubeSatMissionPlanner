# Import libraries
import pandas as pd
from PlanningObjects.Satellite import Satellite

class MissionConfig:
    """
    A class to represent the mission configuration details.
    
    Attributes
    ----------
    excel_input : pd.ExcelFile
        The Excel file containing all mission configuration data.
    plan_info : pd.DataFrame
        A DataFrame with the plan information.
    ground_stations_info : pd.DataFrame
        A DataFrame with the ground stations information.
    constraints_info : pd.DataFrame
        A DataFrame with the constraints information.
    saa_info : pd.DataFrame
        A DataFrame with the South Atlantic Anomaly (SAA) information.
    targets_info : pd.DataFrame
        A DataFrame with the targets information.
    survey_info : pd.DataFrame
        A DataFrame with the survey details.
    power_info : pd.DataFrame
        A DataFrame with power requirements and constraints.
    data_info : pd.DataFrame
        A DataFrame with data constraints and requirements.
    """

    def __init__(self, excel_file_path: str):
        """
        Initialize a new MissionConfig object by loading data from the provided Excel file path.
        
        Parameters
        ----------
        excel_file_path : str
            The file path to the Excel file containing all mission configuration data.
        """
        self.excel_input = pd.ExcelFile(excel_file_path)
        self.plan_info = self.loadSheet("PlanPropagation_Info")
        self.ground_stations_info = self.loadSheet("GroundStations_Info")
        self.constraints_info = self.loadSheet("Constraints_Info")
        self.saa_info = self.loadSheet("SAA_Info")
        self.targets_info = self.loadSheet("Targets_Info")
        self.survey_info = self.loadSheet("Survey_Info")
        self.power_info = self.loadSheet("PowerBudget_Info")
        self.data_info = self.loadSheet("DataBudget_Info")
        
    def loadSheet(self, sheet_name: str) -> pd.DataFrame:
        try:
            return self.excel_input.parse(sheet_name)
        except ValueError:
            raise ValueError(f"Sheet '{sheet_name}' not found in the provided Excel file.")

    def createSatelliteObject(self) -> Satellite:
        """
        Create a new Satellite object based on the data in the plan_info DataFrame.
        
        Returns
        -------
        Satellite
            A new Satellite object with the data from the plan_info DataFrame.
        """
        return Satellite(self.plan_info['TLE URL'].values[0],
                         self.plan_info['TLE File'].values[0],
                         self.plan_info['Satellite Name'].values[0],
                         self.plan_info['Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0],
                         self.plan_info['Timestep [sec]'].values[0])

    def __repr__(self) -> str:
        """
        Provide a string representation of the MissionConfig.
        
        Returns
        -------
        str
            A string representation of the MissionConfig object.
        """
        return (f"MissionConfig(plan_info=DataFrame({len(self.plan_info)} rows), "
                f"ground_stations_info=DataFrame({len(self.ground_stations_info)} rows), "
                f"constraints_info=DataFrame({len(self.constraints_info)} rows), "
                f"saa_info=DataFrame({len(self.saa_info)} rows), "
                f"targets_info=DataFrame({len(self.targets_info)} rows), "
                f"survey_info=DataFrame({len(self.survey_info)} rows), "
                f"power_info=DataFrame({len(self.power_info)} rows), "
                f"data_info=DataFrame({len(self.data_info)} rows))")
