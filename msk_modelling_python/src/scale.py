import os 
import json
import opensim as osim


class Simulation:
    '''
    Class to store data from different file types
    
    '''
    def __init__(self):
        pass
    
    def osim(self, filepath=None):
        '''
        bops.read().osim()
        '''
        if not filepath:
            filepath = filedialog.askopenfilename()
        
        class OsimData:
            def __init__(self):
                self.path = filepath
                self.model = None
                self.trials = None
                self.groups = None
                self.force_platforms = None
                self.camera_info = None
                self.analog_info = None
                self.markers = []
                self.analog = []
                self.df = None