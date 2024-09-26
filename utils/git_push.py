# make sure to cd into the git repo foler

import subprocess
import sys
import os
from .git_tools import summary_git_status
repo_directory = os.getcwd()

# git status print
output = subprocess.run(["git", "status"], cwd=repo_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
if output.stdout is not None and not str(output.stdout).__contains__('working tree clean'):
    print(summary_git_status(repo_directory))

    msg = input('Type the commit message (+ ENTER):') 
    
    subprocess.run(["git", "add", "."], cwd=repo_directory)
    # commit file
    subprocess.run(["git", "commit", "-m", msg], cwd=repo_directory)
    # push
    subprocess.run(["git", "push"], cwd=repo_directory) 
else:
    print('Nothing to commit!')