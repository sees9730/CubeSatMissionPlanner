# Custom imports
# import Utilities.Objects
# import PlanningObjects.UsefulFunctions
from PlanningObjects.MissionConfig import MissionConfig
# import PlanningObjects.Satellite

# def main():

# Load the Excel file
excel_file_path = 'Data Files/Mission_Config_Example.xlsx'

# Create the MissionConfig object
mission_config = MissionConfig(excel_file_path)
satellite = mission_config.createSatelliteObject()


# Get the satellite info
# satellite_name = mission_config.plan_info['Satellite Name'].values[0]


# # Get the plan times
# start_time = mission_config.plan_info['Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0]
# end_time = mission_config.plan_info['Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]'].values[0]
# time_step = mission_config.plan_info['Timestep [sec]'].values[0]



# Utilities.Objects.Schedule(mission_config.plan_info)








# # Load the data and add some summary columns
# saa_coordinates_file = 'Data Files/SAA_Boundary_ROSAT.xlsx'
# input_file_path = "Data Files/SPRITE_Targets_MANTIS.xlsx"

# new_plan = True

# if new_plan == True:
#     # Load the TLE and get the satellite object
#     user_input = Utilities.PlanningObjects.UserInput(input_file_path)
#     satellite = Utilities.OrbitCalculations.fetchTLE(user_input, max_days = 2)[0]
#     plan = None
#     # plan = Utilities.PlanInitializing.initializePlanTargets(input_file_path, saa_coordinates_file, satellite)
#     plan = Utilities.PlanInitializing.initializePlanTargets(user_input, satellite)
#     plan = Utilities.BroadScheduleBuilder.prepopulatePlanSchedule(plan)
#     old_schedule = plan.getSchedule()
#     plan = Utilities.BroadScheduleBuilder.createEclipses(plan)
#     plan = Utilities.BroadScheduleBuilder.populateEclipses(plan)
#     plan = Utilities.BroadScheduleBuilder.cleanUpSchedule(plan)
#     new_schedule = plan.getSchedule()
#     data = {'plan': plan, 'old_schedule': old_schedule, 'new_schedule': new_schedule}
#     with open('data.pkl', 'wb') as file:
#         pickle.dump(data, file)
# else:
#     with open('data.pkl', 'rb') as file:
#         loaded_data = pickle.load(file)
#     plan = loaded_data['plan']
#     old_schedule = loaded_data['old_schedule']
#     new_schedule = loaded_data['new_schedule']

# for i in range(0, len(plan.getSchedule()) - 1, 2880):
#     start = i
#     end = i + 2880
#     if end > len(plan.getSchedule()):
#         end = len(plan.getSchedule()) - 1
#     Utilities.PlottingHelper.plotSchedule(plan, old_schedule, new_schedule, xlims = [start, end])

# # if not is_interactive():
# #     plt.show()

# power_budget_sheet = 'PowerBudgetInfo'
# data_budget_sheet = 'DataBudgetInfo'
# actions_list = Utilities.PlottingFunctions.initializeActionList(plan, input_file_path, power_budget_sheet)

# Utilities.PlottingFunctions.getBatteryChargePlot(input_file_path, power_budget_sheet, actions_list, plan)
# Utilities.PlottingFunctions.getDataStoragePlot(input_file_path, data_budget_sheet, actions_list, plan)
# Utilities.PlottingFunctions.plotTargetCompletion(plan, actions_list)

# if __name__ == '__main__':
#     main()