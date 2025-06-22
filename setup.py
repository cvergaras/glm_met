from setuptools import setup, find_packages

setup(
    name="glm_met",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "earthengine-api",
        "pandas",
        "tqdm"
    ],
    entry_points={
        "console_scripts": [
            "glm-met=glm_met.main:main",
        ],
    },
    author="Your Name",
    description="Download ERA5-Land hourly climate data using GLM .nml location",
    python_requires='>=3.7',
)
