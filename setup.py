from setuptools import setup, find_packages

__version__ = '0.1.32'  # Define the version here

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
        "numpy>=1.21.0",
        "numpy-stl>=2.16.0",
        "pandas>=1.3.0",
        "c3d>=0.3.0",
        "customtkinter>=5.2.0",
        "tkinter>=8.6.0",
    ],
    python_requires='>=3.8',
)