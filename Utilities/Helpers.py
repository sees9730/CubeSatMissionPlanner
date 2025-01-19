import numpy as np
from typing import Dict

class Helpers:

        def inclusive_slice(array: np.ndarray, start: int, end: int) -> np.ndarray:
            """Return a slice of the array from start to end, inclusive."""
            return array[start:end + 1]
        
        def get_pointing_cost() -> int:
            return 80
        
        def is_inside_eclipse(satellite, eclipses, time):
            
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
            
    