import os
import pdb 
import inspect



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