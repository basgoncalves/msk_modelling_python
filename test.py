import matplotlib.pyplot as plt

def capture_mouse_clicks():
    # Create a figure and plot some data
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3, 4, 5], [2, 4, 6, 8, 10], 'ro')
    ax.set_title('Click on the plot')

    # Capture mouse clicks on the plot
    points = plt.ginput(n=2, show_clicks=True)

    # Print the captured points
    print("Captured points:")
    for point in points:
        print(f"x: {point[0]}, y: {point[1]}")

    # Close the figure
    plt.close(fig)

# Call the function to capture mouse clicks
capture_mouse_clicks()
