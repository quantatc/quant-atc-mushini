from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="quant-atc-mushini",
    version="0.4.0",
    author="Ansto Tafara Chibamu",
    description="A modular trading system supporting multiple strategies and brokers",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",  # Your repository URL
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "MetaTrader5>=5.0.0",
        "pandas>=1.3.0",
        "numpy>=1.20.0",
        "pandas-ta",
        "python-dotenv>=0.19.0",
    ],
    entry_points={
        "console_scripts": [
            "quant-atc=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md"],
    },
)