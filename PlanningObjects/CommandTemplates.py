"""
Command Templates
=================

Per-action-key command dicts emitted to the mission JSON. Edit this file to
change mnemonics, args, pre/post timing offsets, or add/remove commands for a
given action. `_create_command_json` in CubeSatMission.py dispatches here based
on the action key.

Each function returns either a single command dict or a list of command dicts.
Return None to emit nothing for that action.

All timestamps are formatted as DOY: "%Y/%j-%H:%M:%S".
"""

import datetime


DOY_FMT = "%Y/%j-%H:%M:%S"


def downlink_command(utc_time, action_time, action_duration_min, gs_name):
    return {
        "utc_time": utc_time,
        "command_type": "placeholder",
        "mnemonic": f"{gs_name} Passover",
        "args": {
            "los_time": (action_time + action_duration_min).strftime(DOY_FMT),
        },
    }


def saa_command(utc_time):
    return {
        "utc_time": utc_time,
        "command_type": "placeholder",
        "mnemonic": "SAA",
        "args": {},
    }


def polar_command(utc_time):
    return {
        "utc_time": utc_time,
        "command_type": "placeholder",
        "mnemonic": "Polar Keepout",
        "args": {},
    }


def charging_command(utc_time):
    return {
        "utc_time": utc_time,
        "command_type": "placeholder",
        "mnemonic": "Charging",
        "args": {},
    }


def slewing_commands(utc_time, action_time, q_1, q_2, q_3, q_4):
    """Commands emitted when slewing to a science target."""
    return [
        {
            "utc_time": (action_time - datetime.timedelta(minutes=1)).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_DAC",
            "args": {"STATE": "STANDBY"},
        },
        {
            "utc_time": (action_time - datetime.timedelta(seconds=30)).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_FIXED",
            "args": {"STATE": "STANDBY"},
        },
        {
            "utc_time": utc_time,
            "command_type": "xb1",
            "mnemonic": "GOTO_ECI_ATTITUDE",
            "args": {
                "PRI_CMD_DIR": 3.0,
                "SEC_CMD_DIR": 1.0,
                "Q_CMD_WRT_REF_1": q_1,
                "Q_CMD_WRT_REF_2": q_2,
                "Q_CMD_WRT_REF_3": q_3,
                "Q_CMD_WRT_REF_4": q_4,
            },
        },
        {
            "utc_time": (action_time + datetime.timedelta(minutes=2)).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_DAC",
            "args": {"STATE": "OBSERV"},
        },
        {
            "utc_time": (action_time + datetime.timedelta(minutes=2, seconds=30)).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_FIXED",
            "args": {"STATE": "OBSERV"},
        },
    ]


def science_commands(utc_time, action_time, action_duration_min, action_id, exposure_type):
    """Commands emitted during a science exposure (TARGET1/TARGET2 windows)."""
    return [
        {
            "utc_time": utc_time,
            "command_type": "fsw",
            "mnemonic": "SCI_START",
            "args": {
                "TYPE": exposure_type,
                "TIME": action_duration_min.seconds,
                "OBS_ID": action_id,
                "end_utc_time": (action_time + action_duration_min).strftime(DOY_FMT),
            },
        },
        {
            "utc_time": (action_time + action_duration_min).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_FIXED",
            "args": {"STATE": "STANDBY"},
        },
        {
            "utc_time": (action_time + action_duration_min + datetime.timedelta(seconds=30)).strftime(DOY_FMT),
            "command_type": "fsw",
            "mnemonic": "HV_DAC",
            "args": {"STATE": "STANDBY"},
        },
    ]
