import requests

def get_user_data():
    """Fetches a webpage and prompts the user for anthropometric data."""
    
    # Replace with the actual URL you want to fetch
    url = "https://example.com"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        print(f"Webpage content:\n{response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching webpage: {e}")
        return

    username = input("Enter your username: ")
    height = float(input("Enter your height (in cm): "))
    weight = float(input("Enter your weight (in kg): "))
    # Add prompts for other anthropometric measurements as needed
    
    print(f"\nUsername: {username}")
    print(f"Height: {height} cm")
    print(f"Weight: {weight} kg")
    # Print other measurements

if __name__ == "__main__":
    get_user_data()