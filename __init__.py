import os



from . import bops
from . import classes
from . import utils

try:
    breakpoint()
    from .src import ceinms
except ImportError:
    print("Warning: ceinms module not found. Ensure it is installed correctly.")


# Define package version
__version__ = "0.1.0"

# Optional: Print a message upon package import, including the example data path
# print(f"msk_modelling_python package v{__version__} loaded.")
# print(f"Example data path set to: {EXAMPLE_DATA_PATH}")

# Ensure the example data directory exists (optional, creates if not found)
# if not os.path.exists(EXAMPLE_DATA_PATH):
#     try:
#         os.makedirs(EXAMPLE_DATA_PATH)
#         print(f"Created example data directory: {EXAMPLE_DATA_PATH}")
#     except OSError as e:
#         print(f"Error creating example data directory: {e}")
