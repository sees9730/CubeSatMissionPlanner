================================
CubeSat Mission Planner
================================

A comprehensive mission planning and scheduling system for CubeSat operations,
optimizing target observations during eclipse periods while accounting for
various operational constraints.

.. contents:: Table of Contents
   :depth: 3
   :local:

Overview
========

The CubeSat Mission Planner is a sophisticated scheduling system designed to optimize
satellite operations, particularly focusing on scientific observations during eclipse periods.
It manages complex constraints including South Atlantic Anomaly (SAA) avoidance, polar region
keepouts, ground station communications, and power management.

Key Features
-----------

* Automatic scheduling of observations during eclipse periods
* Target prioritization based on visibility and science requirements
* Management of pointing operations with slew time costs
* Power budget tracking and optimization
* Downlink scheduling with ground stations
* Visualization tools for mission analysis

Installation
===========

Requirements
-----------

* Python 3.8+
* Required packages:
  * numpy
  * matplotlib
  * pandas
  * skyfield
  * cartopy
  * seaborn
  * scipy

Setup
-----

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/username/cubesat-mission-planner.git
   cd cubesat-mission-planner
   
   # Install dependencies
   pip install -r requirements.txt

Usage
=====

Basic Operation
--------------

.. code-block:: python

   from CubeSatMission import CubeSatMission
   
   # Define program options
   program_options = {
       'Target Availability Check': True,
       'Survey Availability Check': True,
       'Pointing Debug': False
   }
   
   # Create a mission planner instance with your configuration file
   mission = CubeSatMission('mission_config.xlsx', program_options)
   
   # The mission planner automatically generates schedules and outputs
   # Access results through the mission object

Configuration File Format
------------------------

The mission planner expects an Excel file with the following worksheets:

1. **Plan Info**: Basic mission parameters (start/end times, satellite name, TLE data)
2. **Constraints**: Operational constraints (polar, Earth angle, Moon angle)
3. **Ground Stations**: Ground station information (location, elevation constraints)
4. **SAA**: South Atlantic Anomaly boundary coordinates
5. **Targets**: Scientific targets for observation
6. **Survey**: Survey configurations and priorities
7. **Power Budget**: Energy consumption rates for different operations
8. **Data Budget**: Data generation rates for observation modes

Core Components
==============

CubeSatMission
-------------

The main class coordinating all mission planning activities.

.. code-block:: python

   CubeSatMission(excel_file_path, program_options)

Key methods:

* ``_create_mission_config()``: Processes the configuration file
* ``_create_satellite()``: Sets up the satellite model
* ``_create_ground_stations()``: Configures ground station contacts
* ``_create_science_mission()``: Establishes science objectives and targets
* ``_create_operations()``: Generates the operational schedule
* ``_create_commands_list()``: Produces the command sequence

Satellite
--------

Represents the spacecraft, including its orbital parameters and constraints.

ScienceMission
-------------

Manages scientific objectives, including targets, surveys, and eclipse operations.

Target
------

Represents celestial objects to be observed, with visibility calculations.

Eclipse
-------

Manages operations during eclipse periods when scientific observations typically occur.

Schedule
-------

Tracks satellite status and operations throughout the mission timeline.

Visualization
============

The system provides several visualization tools:

* ``plot_battery_charge_plot()``: Battery energy over time
* ``plot_target_completion()``: Observation progress for each target
* ``get_data_storage_plot()``: Onboard data storage utilization
* ``plot_eclipse_operations()``: Detailed view of operations during eclipses
* ``plot_satellite_positions()``: Groundtrack with operational overlays

Command Generation
================

The system generates a JSON command file with the operations schedule:

.. code-block:: python

   # Command file is automatically generated
   mission._create_commands_list()
   
   # File is saved as: mission_commands_YYYYMMDDTHHMMSS.json

Advanced Usage
=============

Customizing Target Priorities
---------------------------

Target priorities can be adjusted in the configuration file or programmatically:

.. code-block:: python

   # Modify target priorities
   for target in mission.science_mission.master_target_list:
       if "high_priority" in target.name:
           target.base_priority = 10

Handling Operational Constraints
------------------------------

Additional constraints can be implemented by modifying the allocation functions:

.. code-block:: python

   # Customize constraint handling
   mission._allocate_constraints(operations_schedule)
   
   # Add custom constraint
   custom_constraint = calculate_custom_constraint()
   operations_schedule[custom_constraint] = MissionStatus.DOWNTIME.value

Contributing
===========

Contributions to the CubeSat Mission Planner are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Implement your changes
4. Add tests if applicable
5. Submit a pull request

License
=======

BSD 3-Clause

Contact
=======

Author: Sebastian Escobar

For questions or support, please contact sebastian.escobar@lasp.colorado.edu