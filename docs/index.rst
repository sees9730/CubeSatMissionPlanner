================================
CubeSat Mission Planner
================================

A comprehensive mission planning and scheduling system for astronomical space telescope CubeSat operations in Low Earh Orbit (LEO),
optimizing target observations during eclipse periods while accounting for
various operational constraints.

.. contents:: Table of Contents
   :depth: 3
   :local:

Overview
========

The CubeSat Mission Planner is a scheduling system designed to optimize 
satellite operations, particularly focusing on scientific observations during eclipse periods (when the satellite is occulted from the Sun, by Earth).
It manages complex constraints including South Atlantic Anomaly (SAA) avoidance, polar region
keepouts, ground station communications, earth and moon angle keepouts, and target availability. 

Key Features
-----------

* Fully automatic scheduling of observations during eclipse periods
* Optimal target selection and slewing operations based on constraints
* Target prioritization based on visibility and science requirements
* Management of pointing operations with slew time costs
* Power and data budget tracking
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

    TBD

..    # Clone the repository
..    git clone https://github.com/username/cubesat-mission-planner.git
..    cd cubesat-mission-planner
   
..    # Install dependencies
..    pip install -r requirements.txt

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

License
=======

BSD 3-Clause

Contact
=======

Author: Sebastian Escobar

For questions or support, please contact sebastian.escobar@lasp.colorado.edu