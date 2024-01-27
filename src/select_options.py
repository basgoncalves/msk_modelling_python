import sys

def select():
    # Check if the number of command line arguments is not equal to 2
    if len(sys.argv) != 2:
        print("usage: setup.py option1 or option2")
        sys.exit(1)

    # Get the command line argument
    option = sys.argv[1]

    # Check the value of the command line argument
    if option == "option1":
        # Do something for option1
        print("Option 1 selected")
    elif option == "option2":
        # Do something for option2
        print("Option 2 selected")
    else:
        # Invalid command line argument
        print("usage: setup.py option1 or option2")
        sys.exit(1)

if __name__ == "__main__":
    select()