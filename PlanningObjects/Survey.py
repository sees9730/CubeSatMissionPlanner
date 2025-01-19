from typing import List
from PlanningObjects.Target import Target

class Survey:
    def __init__(self, name: str, n_targets: int, targets: List[Target], pointing_per_target: int, pointing_exp_time: int,
                 target_min_exp_time: int, target_exp_time: int, total_exp_time: int, repeat_targets: bool, obs_mode: str):
        self.name = name
        self.n_targets = n_targets
        self.targets = targets
        self.pointing_per_target = pointing_per_target
        self.pointing_exp_time = pointing_exp_time
        self.target_min_exp_time = target_min_exp_time
        self.target_exp_time = target_exp_time
        self.total_exp_time = total_exp_time
        self.repeat_targets = repeat_targets
        self.obs_mode = obs_mode
