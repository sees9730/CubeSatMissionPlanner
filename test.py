import pandas as pd
import matplotlib.pyplot as plt

# Load the CSV file
file_path = 'Final_Updated_Points.csv'
points_df = pd.read_csv(file_path)

# Plotting the points
plt.figure(figsize=(8, 8))
plt.plot(points_df['X'], points_df['Y'], 'o-', label='Path')

# Adding labels and title
plt.xlabel('X')
plt.ylabel('Y')
plt.title('Plot of X and Y Coordinates')
plt.legend()

# Display the plot
plt.grid(True)
plt.show()
