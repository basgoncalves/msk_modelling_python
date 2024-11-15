import os
class ProjectPaths:
  '''

  '''
  def __init__(self, project_folder=''):

    if project_folder == 'example':
      print('Running example')
      self.project_folder = 'example'

    elif not project_folder or not os.path.isdir(project_folder):
      print('Please select project directory')
      input('Input and Press enter to continue:')
      if not os.path.isdir(project_folder):                
        print('Still not a valid directory')
        self.project_folder = 'did not set'
        return
    
      
    else:
      self.project_folder = project_folder
    
if __name__ == '__main__':
  c = ProjectPaths('c')
  print(c.project_folder)
