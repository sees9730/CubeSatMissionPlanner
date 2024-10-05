# Import libraries
import pandas as pd

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
