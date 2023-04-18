
# create virtual environment and add the needed packages
# python -m venv .\virtual_env
# cd .\Python_environments\virtual_env\Scripts\  
# .\activate
# data_science_installpkg.py

import subprocess
import sys
import pkg_resources

Packages = ['numpy','c3d','opensim','pyc3dserver','requests','bs4','pandas','selenium','webdriver-manager','matplotlib','docx',
        'autopep8','tk','jupyter','scipy', 'xmltodict','json','tkfilebrowser','customtkinter']

installed_packages = pkg_resources.working_set
installed_packages_list = sorted(['%s==%s' % (i.key, i.version) for i in installed_packages])


for pkg in Packages:
    if any(pkg in s for s in installed_packages_list):
        # print(pkg + ' already installed')
        msg = 'all good'
    else:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg])
