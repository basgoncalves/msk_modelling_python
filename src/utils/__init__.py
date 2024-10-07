import os
import pdb 
import inspect

def create_folder(folder_path):
    """Creates a folder in the specified path."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    else:
        print(f"Folder {folder_path} already exists.")
    return folder_path

def print_with_line_number(text):
  """Prints the given text along with the current line number.

  Args:
      text (str): The text to be printed.
  """

  frame = inspect.currentframe().f_back
  lineno = frame.f_lineno

  print(f"Line {lineno}: {text}")

# def add_debug_break():
#   pdb.set_trace()

def header(text):
    """Prints a header with the given text.

    Args:
        text (str): The text to be printed.
    """
    print("\n" + "="*30)
    print(text)
    print("="*30)