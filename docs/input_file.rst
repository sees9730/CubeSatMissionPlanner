=========================
Input File Specification
=========================

The CubeSat Mission Planner requires a properly formatted Excel file (.xlsx) containing all the necessary mission parameters, constraints, and configurations. This document details the required worksheets and their formats.

.. contents:: Table of Contents
   :depth: 2
   :local:

Overview
========

The input Excel file must contain the following worksheets:

1. **Plan Info**: Basic mission parameters
2. **Constraints**: Operational constraints
3. **Ground Stations**: Ground station information
4. **SAA**: South Atlantic Anomaly boundary coordinates
5. **Targets**: Scientific targets for observation
6. **Survey**: Survey configurations and priorities
7. **Power Budget**: Energy consumption rates
8. **Data Budget**: Data generation rates

Each worksheet requires specific columns as detailed below.

Plan Info Worksheet
==================

Contains basic mission configuration parameters.

Required Columns:
----------------

* **Satellite Name**: Name of the satellite (string)
* **TLE URL**: URL for TLE data source (string, optional if TLE File is provided)
* **TLE File**: Path to local TLE file (string, optional if TLE URL is provided)
* **Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]**: Mission start time in UTC
* **Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]**: Mission end time in UTC
* **Timestep [sec]**: Simulation time step in seconds (integer, typically 30-60)

Example:
-------

.. csv-table::
   :header: "Satellite Name", "TLE URL", "TLE File", "Simulation Start Time [YYYY-MM-DD HH:MM:SS UTC]", "Simulation End Time [YYYY-MM-DD HH:MM:SS UTC]", "Timestep [sec]"
   
   "SPRITE-DEMO", "https://celestrak.org/NORAD/elements/gp.php?CATNR=46923", "", "2022-09-01 00:00:00", "2022-09-14 00:00:00", "60"

Constraints Worksheet
===================

Defines operational constraints for the satellite.

Required Columns:
----------------

* **Polar Constraint**: Minimum distance from poles in degrees (float)
* **Earth Angle Constraint**: Minimum angle above Earth's horizon for targets in degrees (float)
* **Moon Angle Constraint**: Minimum angle from Moon for targets in degrees (float)

Example:
-------

.. csv-table::
   :header: "Polar Constraint", "Earth Angle Constraint", "Moon Angle Constraint"
   
   "20", "15", "10"

Ground Stations Worksheet
=======================

Lists ground stations for communication and data downlink.

Required Columns:
----------------

* **Name**: Ground station identifier (string)
* **Latitude**: Latitude in degrees (float)
* **Longitude**: Longitude in degrees (float)
* **Altitude [m]**: Altitude in meters (float)
* **Elevation Constraint [deg]**: Minimum elevation angle for visibility in degrees (float)

Example:
-------

.. csv-table::
   :header: "Name", "Latitude", "Longitude", "Altitude [m]", "Elevation Constraint [deg]"
   
   "BOULDER", "40.0150", "-105.2705", "1624", "10"
   "WALLOPS", "37.9402", "-75.4664", "10", "10"
   "SINGAPORE", "1.3521", "103.8198", "15", "10"

SAA Worksheet
===========

Defines the South Atlantic Anomaly (SAA) boundary coordinates.

Required Columns:
----------------

* **Latitude**: Latitude points defining the SAA boundary (float)
* **Longitude**: Longitude points defining the SAA boundary (float)

Notes:
-----

* Coordinates should form a closed polygon
* Points should be ordered to trace the boundary of the SAA region

Example:
-------

.. csv-table::
   :header: "Latitude", "Longitude"
   
   "-30", "-90"
   "-20", "-70"
   "-10", "-50"
   "-20", "-30"
   "-30", "-40"
   "-40", "-60"
   "-30", "-90"

Targets Worksheet
===============

Defines scientific targets for observation.

Required Columns:
----------------

* **Target**: Target identifier (string)
* **Pointing**: Pointing ID for this target (integer or string)
* **HH**: Right ascension hours (integer, 0-23)
* **MM**: Right ascension minutes (integer, 0-59)
* **SS**: Right ascension seconds (float, 0-59.999)
* **dd**: Declination degrees (integer, -90 to +90)
* **mm**: Declination minutes (integer, 0-59)
* **ss**: Declination seconds (float, 0-59.999)
* **Rotation Angle**: Instrument rotation angle in degrees (float)
* **Base Priority**: Base priority value for scheduling (float)
* **Survey**: Associated survey name (string, must match a survey in the Survey worksheet)

Example:
-------

.. csv-table::
   :header: "Target", "Pointing", "HH", "MM", "SS", "dd", "mm", "ss", "Rotation Angle", "Base Priority", "Survey"
   
   "HZ_43", "1", "13", "16", "21.8", "29", "5", "55", "0", "1", "CVZ_Survey"
   "WD1327", "1", "13", "29", "16.7", "23", "23", "34", "0", "2", "Bright_WD_Survey"
   "G191B2B", "1", "5", "5", "30.6", "52", "49", "51.9", "45", "3", "Bright_WD_Survey"

Survey Worksheet
==============

Defines survey configurations and priorities.

Required Columns:
----------------

* **Survey**: Survey identifier (string)
* **N Targets**: Number of targets in the survey (integer)
* **Pointings Per Target**: Number of pointings per target (integer)
* **ExpTime Per Pointing [s]**: Exposure time per pointing in seconds (float)
* **ExpTime Per Target [s]**: Total exposure time per target in seconds (float)
* **Total ExpTime**: Total survey exposure time in seconds (float)
* **Obs Mode**: Observation mode (string, e.g., "SPECTRUM", "IMAGE")
* **Repeat Targets**: Whether targets can be repeated (boolean or 0/1)
* **SurveyPriority**: Priority of survey for scheduling (integer)
* **Minimum ExpTime [s]**: Minimum acceptable exposure time in seconds (float)

Example:
-------

.. csv-table::
   :header: "Survey", "N Targets", "Pointings Per Target", "ExpTime Per Pointing [s]", "ExpTime Per Target [s]", "Total ExpTime", "Obs Mode", "Repeat Targets", "SurveyPriority", "Minimum ExpTime [s]"
   
   "CVZ_Survey", "3", "1", "300", "300", "900", "SPECTRUM", "1", "1", "180"
   "Bright_WD_Survey", "5", "2", "120", "240", "1200", "IMAGE", "0", "2", "120"
   "Faint_WD_Survey", "10", "3", "600", "1800", "18000", "SPECTRUM", "0", "3", "400"

Power Budget Worksheet
====================

Defines energy consumption rates for different operational modes.

Required Columns:
----------------

* **Key**: Operational mode identifier (string)
* **Value**: Energy consumption rate in watts or joules per second (float)

Special Keys:
-----------

* **INITIAL_CHARGE**: Initial battery charge in joules (float)
* **MAXIMUM_CHARGE**: Maximum battery capacity in joules (float)

Example:
-------

.. csv-table::
   :header: "Key", "Value"
   
   "INITIAL_CHARGE", "100000"
   "MAXIMUM_CHARGE", "150000"
   "DOWNTIME", "-5"
   "CHARGING", "10"
   "OBSERVING", "-15"
   "SLEWING", "-20"
   "TARGET1", "-15"
   "TARGET2", "-15"
   "DOWNLINK", "-25"
   "SAA", "-10"
   "POLAR", "-10"

Data Budget Worksheet
===================

Defines data generation rates for different observation modes.

Required Columns:
----------------

* **Key**: Observation mode identifier (string)
* **Value**: Data generation in megabytes (float)

Special Keys:
-----------

* **INITIAL_DATA_SIZE**: Initial data storage usage in megabytes (float)
* **DOWNLINK_RATE**: Data downlink rate in megabytes per second (float)

Example:
-------

.. csv-table::
   :header: "Key", "Value"
   
   "INITIAL_DATA_SIZE", "0"
   "DOWNLINK_RATE", "0.5"
   "SPECTRUM", "15"
   "IMAGE", "25"
   "CALIBRATION", "10"

Validation Rules
===============

The input file must follow these validation rules:

1. All required worksheets must be present
2. All required columns must be present in each worksheet
3. Data types must match the expected types
4. References between worksheets must be consistent (e.g., Survey names in Targets must exist in the Survey worksheet)
5. Time values must be in the correct format
6. Coordinate values must be within valid ranges
7. Priority values should be non-negative

Common Issues
============

* **TLE Data**: Ensure TLE data is valid and current for the simulation period
* **Time Consistency**: Ensure start time is before end time and the timestep is appropriate
* **Ground Station Coordinates**: Verify ground station coordinates are accurate
* **SAA Boundary**: Ensure SAA boundary forms a closed polygon with counterclockwise vertex ordering
* **Target Coordinates**: Verify right ascension and declination values are accurate
* **Survey Configuration**: Ensure survey exposure times and priorities are consistent
* **Power Budget**: Verify power values are realistic for your CubeSat's specifications
* **Data Budget**: Ensure data generation rates match your instrument capabilities

Examples
=======

A complete example template is available in the repository at:
``examples/mission_template.xlsx``