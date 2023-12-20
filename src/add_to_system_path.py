import os
import winreg
import ctypes, sys

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
def remove_to_system_path(path):
        with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as hkey:
            with winreg.OpenKey(hkey, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 0, winreg.KEY_ALL_ACCESS) as key:
                current_path, _ = winreg.QueryValueEx(key, 'Path')
                paths = current_path.split(';')
                paths = [p for p in paths if p != path]
                new_path = ';'.join(paths)
                winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)

def add_to_system_path(path):    
    with winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE) as hkey:
        with winreg.OpenKey(hkey, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 0, winreg.KEY_ALL_ACCESS) as key:
            current_path, _ = winreg.QueryValueEx(key, 'Path')
            new_path = current_path + ';' + path
            winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)

def show_popup(message):
        ctypes.windll.user32.MessageBoxW(0, message, "System Path Update", 1)


if is_admin():    
    path = input('Paste the folder containing the OpenSim bin folder: \n')
    if path.startswith('-rm '):
        path = path[4:]
        print(path)
        remove_to_system_path(path)
        show_popup('Removed from system path: ' + path)
    else:
        add_to_system_path(path)
        show_popup('Added to system path: ' + path)
    
else:
    print('is not admin')
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    

