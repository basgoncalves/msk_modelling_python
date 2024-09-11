import subprocess
import re

def sanitize_input(data, allowed_chars=r"\w\s\.\-_\(\)\[\]!"):
  """
  Sanitizes user input by removing potentially harmful characters.

  Args:
      data: The string to be sanitized.
      allowed_chars: A regular expression defining allowed characters (default: alphanumeric, whitespace, basic punctuation).

  Returns:
      The sanitized string.
  """

  # Remove HTML tags and escape potentially harmful characters
  clean_data = re.sub(r"<[^>]*>", "", data)  # Remove HTML tags
  clean_data = html.escape(clean_data)  # Escape special characters

  # Restrict to allowed characters based on the regular expression
  clean_data = re.sub(r"[^{}]".format(allowed_chars), "", clean_data)

  # Additional checks (optional)
  # - Check for control characters (e.g., \n, \t) and remove if necessary
  # - Check for specific patterns that might be indicative of attacks (e.g., SQL injection)

  return clean_data


def run_cmd(cmd):
  # Sanitize user input (remove potentially harmful characters)
  sanitized_cmd = sanitize_input(cmd)
  # Split the command and arguments
  cmd_parts = sanitized_cmd.split()
  try:
    subprocess.run(cmd_parts, check=True)  # Execute the command
    print("Command executed successfully!")
  except subprocess.CalledProcessError as e:
    print(f"Error: {e}")

def main():
  user_input = input("Enter command (after -bops): ")
  if user_input.startswith("-bops"):
    cmd = user_input.split()[1:]  # Extract command after "-bops"
    run_cmd(" ".join(cmd))  # Join arguments back into a string
  else:
    print("Invalid input. Start with '-bops'")

if __name__ == "__main__":
  main()
