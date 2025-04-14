# python version of Batch OpenSim Processing Scripts (BOPS)
# originally by Bruno L. S. Bedo, Alice Mantoan, Danilo S. Catelli, Willian Cruaud, Monica Reggiani & Mario Lamontagne (2021):
# BOPS: a Matlab toolbox to batch musculoskeletal data processing for OpenSim, Computer Methods in Biomechanics and Biomedical Engineering
# DOI: 10.1080/10255842.2020.1867978

__testing__ = False

import os
import json
import time
import unittest
import numpy as np
import pandas as pd
import c3d
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import math

# end