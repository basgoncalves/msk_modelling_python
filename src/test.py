import os
import subprocess



def activate_virtual_environment(venv_path=''):
    if not venv_path:
        parent_folder = os.path.dirname(os.path.abspath(__file__))
        venv_path = os.path.join(parent_folder,'..', 'virtual_environment')
    
    activate_script = os.path.join(venv_path, 'Scripts', 'activate')
    
    with open(activate_script) as f:
        code = compile(f.read(), activate_script, 'exec')
        exec(code, dict(__file__=activate_script))

    print(activate_script)
    subprocess.call(activate_script, shell=True)

activate_virtual_environment()