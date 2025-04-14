import math
import time

def print_loading_bar(completion_ratio):
    """Prints a visual loading bar indicating progress.

    Args:
        completion_ratio (float): A value between 0.0 (no progress) and 1.0 (complete).
    """

    # Define bar length and characters
    bar_length = 20  # Adjust for desired visual length
    completed_char = '='
    remaining_char = ' '

    # Calculate completed and remaining sections
    completed_sections = int(math.floor(completion_ratio * bar_length))
    remaining_sections = bar_length - completed_sections

    # Build the progress bar string
    progress_bar = completed_char * completed_sections + remaining_char * remaining_sections

    # Print the progress bar and optional percentage
    print(f"\rProgress: [{progress_bar}] {completion_ratio:.2%}", end="")


if __name__ == "__main__":
    # Example usage
    for i in range(101):
        completion_ratio = i / 100
        print_loading_bar(completion_ratio)
        time.sleep(0.05)  # Simulate work
    print()  # New line after completion