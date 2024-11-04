import re
import os

relPath = os.path.dirname(os.path.realpath(__file__))
reqTxtPath = os.path.join(relPath,'..\\requirements.txt')
print(reqTxtPath)
# Read the contents of the requirements.txt file
with open(reqTxtPath, 'r') as file:
    requirements = file.readlines()

# Remove versions from each requirement
updated_requirements = []
for requirement in requirements:
    requirement = re.sub(r'==\d+(\.\d+)*', '', requirement)
    updated_requirements.append(requirement)

# Write the updated requirements to the file
with open(reqTxtPath, 'w') as file:
    file.writelines(updated_requirements)