# make sure to cd into the git repo foler

import subprocess
import sys
import os
import time
import platform
from .git_tools import import_repos, summary_git_status, clear_terminal
import re

repos = import_repos()        
# loop over the list of repos
for i in range(len(repos)):
    repo_directory = repos[i]
    try:         
        os.chdir(repo_directory)
    except:
        print([repo_directory + " does not exist."])
        continue

    time.sleep(0.5)
    output = subprocess.run(["git", "status"], cwd=repo_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
    if output.stdout is not None and not str(output.stdout).__contains__('working tree clean'):
        print(summary_git_status(repo_directory))
        print('trying to push "' + repo_directory + '" ...')
        msg = input('Type the commit message (+ ENTER):') 
        
        # add all the files
        subprocess.run(["git", "add", "."], cwd=repo_directory)
        # commit file
        subprocess.run(["git", "commit", "-m", msg], cwd=repo_directory)
        # push
        subprocess.run(["git", "push"], cwd=repo_directory) 

        clear_terminal()

 