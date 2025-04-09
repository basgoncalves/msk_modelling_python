from setuptools import setup, find_packages

__version__ = "0.1.0"  # Define the version here

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="msk_modelling_python",
    version=__version__,
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python package for musculoskeletal modelling (initial)",
    long_description=long_description,
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
    ],
    python_requires='>=3.7',
)