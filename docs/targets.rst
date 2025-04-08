=================
Targets
=================

Understanding Targets in CubeSat Mission Planning
================================================

Targets are celestial objects that the CubeSat will observe during its mission. The mission planner uses algorithms to determine when and how each target should be observed based on visibility constraints, priorities, and scientific objectives organized into surveys.

.. contents:: Table of Contents
   :depth: 2
   :local:

Target Definition
===============

In the CubeSat Mission Planner, a target is defined by:

1. **Celestial coordinates** (Right Ascension and Declination)
2. **Instrument configuration** (Rotation Angle)
3. **Priority** for scheduling
4. **Association** with a specific scientific survey

Each target represents a specific celestial object (such as a star, galaxy, or other astronomical body) that requires observation to fulfill the mission's scientific goals.

Target Specification in the Input File
====================================

Targets are specified in the :ref:`targets_info_section` of the input Excel file. Each row represents a unique target or a specific pointing for a multi-pointing target.

Key Concepts in Target Specification:
-----------------------------------

* **Target Name and Pointing ID**: Each target has a name (identifier) and a pointing ID 
    - For targets requiring observation from multiple angles, the same target name can have multiple entries with different pointing IDs.
    - For targets with a single observation angle, a single pointing ID (e.g., "1" or "A") is used.

* **Celestial Coordinates**: Specified in the equatorial coordinate system:
    - **Right Ascension**: Given in hours (HH), minutes (MM), and seconds (SS)
    - **Declination**: Given in degrees (dd), minutes (mm), and seconds (ss)
    - These coordinates precisely define the target's position in the sky. More accurate coordinates lead to better observation planning.

* **Rotation Angle**: Defines the orientation of the instrument relative to the target.
    - Important for spectrographic observations or specific instrument alignments.
    - Measured in degrees (0-360°).

* **Base Priority**: A numerical value determining the target's importance.
    - **Lower values indicate higher priority for scheduling.**
    - Used in the scheduling algorithm to resolve conflicts when multiple targets are visible.

* **Survey Association**: Each target must belong to a survey.
    - Links the target to specific observation parameters defined in the :ref:`survey_info_section`.
    - Determines exposure time, observation mode, and other parameters.

Example Target Entry:
------------------

.. csv-table::
   :header: "Target", "Pointing", "HH", "MM", "SS", "dd", "mm", "ss", "Rotation Angle", "Base Priority", "Survey"
   
   "HZ_43", "1", "13", "16", "21.8", "29", "5", "55", "0", "1", "CVZ_Survey"

This example defines a target named "HZ_43" (which is a white dwarf star) with right ascension 13h 16m 21.8s and declination +29° 5' 55", to be observed with a rotation angle of 0 degrees. It has a base priority of 1 and belongs to the "CVZ_Survey" survey.

Multi-Pointing Targets
--------------------

Some scientific objectives require observing the same target from multiple angles or at slightly different celestial coordinates. In this case, the same target name will have multiple entries with different pointing IDs:

.. csv-table::
   :header: "Target", "Pointing", "HH", "MM", "SS", "dd", "mm", "ss", "Rotation Angle", "Base Priority", "Survey"
   
   "NGC1851", "1", "5", "14", "6.3", "-40", "2", "50", "0", "2", "Cluster_Survey"
   "NGC1851", "2", "5", "14", "6.3", "-40", "2", "50", "45", "2", "Cluster_Survey"
   "NGC1851", "3", "5", "14", "6.3", "-40", "2", "50", "90", "2", "Cluster_Survey"

This example shows a target (globular cluster NGC1851) with three different pointings, each with a different rotation angle (0°, 45°, and 90°) to capture different aspects of the cluster.

Target Visibility
===============

For a target to be observable, it must meet several visibility constraints at a given time:

1. **Earth Angle Constraint**: Target must be a minimum angular distance above Earth's horizon
2. **Moon Angle Constraint**: Target must be a minimum angular distance from the Moon
3. **Polar Constraint**: Satellite must not be near polar regions during observation
4. **South Atlantic Anomaly (SAA)**: Satellite must not be in the SAA during observation
5. **Eclipse Condition**: Observations typically occur during eclipse periods when the satellite is in Earth's shadow

The mission planner calculates visibility windows for each target throughout the mission duration, considering all these constraints.

For more information on the constraints, see the :ref:`constraints_info_section`.

Target Treatment in the Algorithm
==============================

The CubeSat Mission Planner processes targets in the following way:

1. **Visibility Calculation**:
   * For each target, the planner calculates visibility periods throughout the mission
   * Visibility is determined by checking all constraints at each time step

2. **Eclipse Association**:
   * Visibility periods are compared with eclipse periods
   * The planner identifies which targets are visible during each eclipse

3. **Priority Adjustment**:
   * The base priority of each target is adjusted based on:
     * Current visibility duration
     * Previous observation time (for repeated targets)
     * Survey priority
     * Special scientific considerations

4. **Target Selection and Scheduling**:
   * The planner selects the highest priority target(s) for each eclipse
   * Allocates pointing operations before observation
   * Schedules target observations during optimal visibility periods
   * Ensures minimum exposure time requirements are met

5. **Command Generation**:
   * Converts scheduled observations into spacecraft commands
   * Specifies target coordinates, instrument settings, and timing

Target Observation Modes
=====================

Targets can be observed in different modes as specified in the Survey worksheet:

* **SPECTRUM**: Spectroscopic observation (typically generating less data)
* **IMAGE**: Imaging observation (typically generating more data)
* **CALIBRATION**: Calibration observation for instrument alignment and sensitivity

The observation mode affects:
* Data generation rate
* Power consumption
* Required exposure time
* Scientific value of the observation

Target Completion Tracking
=======================

The mission planner tracks the completion status of each target:

* **Current Exposure Time**: Accumulated observation time for the target
* **Required Exposure Time**: Total observation time needed (from Survey worksheet)
* **Completion Percentage**: Progress toward observation goal

This information is visualized in the target completion plot, showing how observation time accumulates throughout the mission.

Best Practices for Target Definition
=================================

1. **Coordinate Accuracy**:
   * Ensure celestial coordinates are accurate and in the correct format
   * Verify coordinates with astronomical databases

2. **Priority Assignment**:
   * Assign priorities strategically based on scientific importance
   * Consider seasonal visibility when assigning priorities
   * Group related targets in the same survey

3. **Survey Association**:
   * Match targets with appropriate surveys based on scientific objectives
   * Ensure survey parameters (exposure time, observation mode) are appropriate for the target

4. **Target Distribution**:
   * Distribute targets across different regions of the sky
   * Avoid clustering all high-priority targets in similar sky positions
   * Consider including targets in the Continuous Viewing Zone (CVZ) for reliable observation opportunities

5. **Multi-Pointing Strategy**:
   * Use multi-pointing for complex targets requiring different perspectives
   * Consider rotation angles that provide complementary scientific data
   * Balance the number of pointings with mission time constraints

Target-Related Commands
====================

When a target is scheduled for observation, the mission planner generates commands like:

.. code-block:: json

   {
     "utc_time": "2022/245-15:30:00",
     "command_type": "fsw",
     "mnemonic": "SCI_START",
     "args": {
       "TYPE": "SPECTRUM",
       "TIME": 300,
       "OBS_ID": 42
     }
   }

This command instructs the spacecraft to:
* Begin a scientific observation at the specified time
* Use the SPECTRUM observation mode
* Observe for 300 seconds
* Associate the data with observation ID 42

The mission planner automatically sequences these commands with the necessary pointing operations to ensure the spacecraft is properly oriented before observation begins.