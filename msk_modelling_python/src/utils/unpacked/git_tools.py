
import os
import platform
import re
import subprocess

def import_repos():
    device_details = platform.uname()
    name_pc = device_details.node
    # list of directories where repos are stored depending on current local machine
    if name_pc == 'Bas-PC' or name_pc == 'DESKTOP-8KRF896':
        repos =[r'C:\Git\research_documents',
                r'C:\Git\python_projects',
                r'C:\Git\msk_modelling_matlab',
                r'C:\Git\msk_modelling_python',
                r'C:\Git\research_data',
                r'C:\Git\personal']
    else:
        repos = []
        print('Current machine not configured. Add folder paths to the script or perform "git pull manually"')
            
    return repos

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')
    
def summary_git_status(repo_directory):
    
    output = subprocess.run(["git", "status"], cwd=repo_directory, stdout=subprocess.PIPE, stderr=subprocess.PIPE) 
    string = output.stdout.decode('utf-8')
    # split based on the possible git status outputs: https://git-scm.com/docs/git-status
    parts = re.split(r'nM\t|nA\t|nD\t|nT\t|nR\t|nC\t|nU\t', string) # Split the string based on the delimiters using regular expression
    parts = [part for part in parts if part] # Remove empty strings from the list
    changes_summary = '\n'.join(parts) # Join the parts with newlines
    
    return changes_summary


def split_changes_summary_in_different_lines(string):
    # split based on the possible git status outputs: https://git-scm.com/docs/git-status
    parts = re.split(r'nM\t|nA\t|nD\t|nT\t|nR\t|nC\t|nU\t', string) # Split the string based on the delimiters using regular expression
    parts = [part for part in parts if part] # Remove empty strings from the list
    result = '\n'.join(parts) # Join the parts with newlines
    return result

# END