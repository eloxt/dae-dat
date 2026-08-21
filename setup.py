from setuptools import find_packages, setup


setup(
    name="surge-dae-dat",
    version="0.1.0",
    description="Generate dae-compatible geodata dat files from SukkaW/Surge rules",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    entry_points={"console_scripts": ["surge-dae-dat=surge_dae_dat.cli:main"]},
)
