try:
    import opensim as osim
except:      
    print('=============================================================================================')
    print('could not import opensim')
    print('Check if __init__.py has "." before packages (e.g. "from .simbody" instead of "from simbody")')
    pythonPath = os.path.dirname(sys.executable)
    initPath = os.path.join(pythonPath,'lib\site-packages\opensim\__init__.py')
    print('init path is: ', initPath)    
    print('=============================================================================================\n\n\n\n\n')