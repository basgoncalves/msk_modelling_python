from setuptools import setup, find_packages

__version__ = '0.0.2'  # Define the version here

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="msk_modelling_python",
    version=__version__,
    author="Bas",
    author_email="basilio.goncalves7@gmail.com",
    description=f"A Python package for musculoskeletal modelling (version {__version__})",
    long_description=f"{long_description}\n\nVersion: {__version__}",
    long_description_content_type="text/markdown",
    url="https://github.com/your_username/msk_modelling_python",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "numpy",
        "numpy-stl",
        "pandas",
        "c3d",
        "pyperclip",
        "customtkinter",
        "matplotlib"
    ],
    
    package_data={
        'msk_modelling_python': ['*.json', '*.ins', '*.txt'],
    },
    python_requires='>=3.8',
)