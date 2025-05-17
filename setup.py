from setuptools import setup, find_packages

setup(
    name="gq_trade_simulator",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "websockets>=11.0.3",
        "numpy>=1.24.3",
        "pandas>=2.0.3",
        "scikit-learn>=1.3.0",
        "PyQt6>=6.5.2",
        "matplotlib>=3.7.2",
        "loguru>=0.7.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        'console_scripts': [
            'gq-simulator=src.main:run',
        ],
    },
) 