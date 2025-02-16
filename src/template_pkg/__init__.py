import os 
import unittest
import msk_modelling_python as msk


def run():
    pass


class test(unittest.TestCase):
    def test_run(self):
        self.assertRaises(Exception, run)
        print("test_run passed!")
        

if __name__ == "__main__":
    try:
        msk.unittest.main()
        msk.log_error('Tests passed for msk_modelling_python package')
    except Exception as e:
        print("Error: ", e)
        msk.log_error(e)
        msk.bops.Platypus().sad()