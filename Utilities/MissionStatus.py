from enum import Enum

class MissionStatus(Enum):
    TARGET2 = -2
    TARGET1 = -1
    DOWNTIME = 0
    CHARGING = 1
    OBSERVING = 2
    POINTING = 3
    DOWNLINK = 4
    SAA = 5
    POLAR = 6

    def get_key(value: int) -> None:
        """
        Get the key (name) of an enum value
        """
        for member in MissionStatus:
            if member.value == value:
                return member.name
        raise ValueError(f"Value '{value}' not found in Enum.")
    
    def get_value(key: str) -> None:
        """
        Get the value of an enum key (name)
        """
        for member in MissionStatus:
            if member.name.casefold() == key.casefold():
                return member.value
        return None

    # DONE
    def plot_color(value = -10) -> str:
        """
        Get the color of an enum value

        Args:
            value (int): The value of the enum

        Returns:
            str: The color used to plot
        """
        color_mapping = {
            MissionStatus.TARGET2.value: 'darkgoldenrod',
            MissionStatus.TARGET1.value: 'firebrick',
            MissionStatus.DOWNTIME.value: 'red',
            MissionStatus.CHARGING.value: 'mediumseagreen',
            MissionStatus.POINTING.value: 'steelblue',
            MissionStatus.DOWNLINK.value: 'tab:orange',
            MissionStatus.SAA.value: 'khaki',
            MissionStatus.POLAR.value: 'khaki'
        }
        return color_mapping.get(value, 'black')
