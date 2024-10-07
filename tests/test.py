# my_package.py

import pyperclip

class mcf:
    def __init__(self):
        pass

    header = staticmethod(lambda: pyperclip.copy("#%% ################################################## \n " +
                                                 " #                 Description:                        \n " +
                                                 "######################################################"))

# main.py

print(mcf.header())