# %% use this to test functions before inputing them into bops or other modules
from bops import *
import ceinms_setup as cs
import bops as bp
from plotting import plot_ceinms as pltc
import replace_markerset as rm
import json

# Load the bops_settings.json file if it exists, otherwise create it
try:
    with open('bops_settings.json', 'r') as file:
        settings = json.load(file)
except FileNotFoundError:
    settings = {}
    with open('bops_settings.json', 'w') as file:
        json.dump(settings, file)

# Print all the tags and subtags
print('printing tags and subtags ...')
if not settings.keys():
    print('No tags and subtags found')
    exit()
for tag, subtags in settings.keys():
    print(tag)
    for subtag in subtags:
        print(f"  - {subtag}")