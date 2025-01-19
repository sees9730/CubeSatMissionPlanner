from typing import List
from PlanningObjects.Target import Target
from PlanningObjects.Eclipse import Eclipse
from PlanningObjects.Survey import Survey

import matplotlib.pyplot as plt
import numpy as np

class ScienceMission:
    """
    A class to represent a science mission, including its targets, eclipses, and surveys.
    
    Attributes
    ----------
    master_target_list : list of Target
        A list containing all the targets involved in the science mission.
    eclipses : list of Eclipse
        A list containing all the eclipses that affect the mission.
    surveys : list of Survey
        A list containing all the surveys performed during the mission.
    """

    def __init__(self,
                 master_target_list: List[Target],
                 eclipses: List[Eclipse],
                 surveys: List[Survey]):
        """
        Initialize a new ScienceMission object.
        
        Parameters
        ----------
        master_target_list : list of Target
            A list of targets involved in the science mission.
        eclipses : list of Eclipse
            A list of eclipses that affect the mission.
        surveys : list of Survey
            A list of surveys performed during the mission.
        """
        self.master_target_list = master_target_list
        self.eclipses = eclipses
        self.surveys = surveys

    def get_survey_by_name(self, name: str) -> Survey:
        """
        Retrieve a survey by its name.
        
        Parameters
        ----------
        name : str
            The name of the survey to retrieve.
        
        Returns
        -------
        Survey
            The survey with the given name.
        
        Raises
        ------
        KeyError
            If no survey with the given name is found.
        """

        for survey in self.surveys:
            if survey.name == name:
                return survey
        raise KeyError(f"Survey with name {name} not found in mission.")
    
    def get_survey_of_target(self, target_name: str) -> Survey:
        """
        Retrieve the survey associated with a target.
        
        Parameters
        ----------
        target_name : str
            The name of the target.
        
        Returns
        -------
        Survey
            The survey associated with the target.
        """

        for survey in self.surveys:
            for target in survey.targets:
                if target.name == target_name:
                    return survey
    
    def get_target_by_name(self, name: str) -> Target:
        """
        Retrieve a target by its name.
        
        Parameters
        ----------
        name : str
            The name of the target to retrieve.
        
        Returns
        -------
        Target
            The target with the given name.
        
        Raises
        ------
        KeyError
            If no target with the given name is found.
        """

        for survey in self.surveys:
            targets = survey.targets
            for target in targets:
                if target.name == name:
                    return target
        raise KeyError(f"Target with name {name} not found in mission.")

    def plot_target_in_eclipse(self, target_name: str, eclipse_num: int):

        # Find the eclipse
        eclipse = self.eclipses[eclipse_num]

        # Get the schedule for the target in the eclipse
        target_names = eclipse.targets_available.keys()
        
        if target_name not in target_names:
            raise KeyError(f"Target {target_name} not visible in eclipse {eclipse_num}.")
        else:
            target_eclipse_schedule = eclipse.targets_available[target_name]

        # Get the start and end indices of visibility in the eclipse
        starts = eclipse.schedule_indices[0]
        ends = eclipse.schedule_indices[-1]

        # Plot the schedule
        plt.step(eclipse.operations.time.utc_datetime(), target_eclipse_schedule, color = 'darkcyan')
        plt.plot([], [], label = f'Start Index = {starts}, End Index = {ends}', color = 'darkcyan')
        plt.legend(loc = 'best')
        plt.xticks(rotation = 15)
        plt.xlabel('Time [UTC]')
        plt.ylabel('Visibility Status')
        plt.title(f'Visibility Schedule for {target_name} in Eclipse {eclipse_num}')
        plt.show()

    def plot_targets_in_eclipse(self, survey_name: str, eclipse_num: int):

        # Get the eclipse and the targets
        eclipse = self.eclipses[eclipse_num]
        targets_available_in_eclipse = eclipse.targets_available.keys()

        survey = self.get_survey_by_name(survey_name)
        targets_in_survey = survey.targets

        # Get the schedule for the targets in the eclipse
        plotted = False
        for target in targets_in_survey:
            if target.name in targets_available_in_eclipse and np.sum(eclipse.targets_available[target.name]) != 0:
                print(survey_name, target.name)
                plt.step(eclipse.operations.time.utc_datetime(), eclipse.targets_available[target.name], label = target.name)
                plotted = True
        if plotted:
            plt.legend(loc = 'best')
            plt.xticks(rotation = 15)
            plt.xlabel('Time [UTC]')
            plt.ylabel('Visibility Status')
            plt.title(f'Available Targets in Eclipse {eclipse_num}')
            plt.show()
        else:
            raise KeyError(f"No targets in {survey_name} are visible in Eclipse {eclipse_num}.")

    def plot_targets_in_mission(self):

        # Plot the available targets in the entire mission
        plotted = False
        for survey in self.surveys:
            for target in survey.targets:
                if np.sum(target.schedule.status) != 0:
                    plt.step(target.schedule.time.utc_datetime(), target.schedule.status, label = target.name)
                    plotted = True
        if plotted:
            plt.legend(loc = 'best')
            plt.xlim(self.eclipses[0].operations.time.utc_datetime()[0], self.eclipses[0].operations.time.utc_datetime()[-1])
            plt.xticks(rotation = 15)
            plt.xlabel('Time [UTC]')
            plt.ylabel('Visibility Status')
            plt.title('Available Targets in the Mission')
            plt.show()
        else:
            raise KeyError('No targets are visible in the mission.')
        
    # def update_target_priority_by_name(self, name: str, free_slots: Eclipse) -> None:

    #     # Find the target
    #     target = self.get_target_by_name(name)

    #     # Update the target

        


