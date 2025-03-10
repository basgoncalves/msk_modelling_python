import os
import unittest
import msk_modelling_python as msk
from msk_modelling_python.src.ui.ui_examples import (get_ui_settings, show_warning, pop_up_message, close_all,
                                                     select_folder, create_folder, select_file, box_list_selection)



class test(unittest.TestCase):
    def test_APP(self):
        pass
        

if __name__ == "__main__":
    try:
        msk.unittest.main()
        msk.log_error('Tests passed for msk_modelling_python.src.ui')
    except Exception as e:
        print("Error: ", e)
        msk.log_error(e)
        msk.Platypus().sad()
    
