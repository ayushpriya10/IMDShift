from setuptools import setup, find_packages

setup(
    name='IMDShift',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'click',
        'tqdm',
        'boto3',
        'prettytable'
    ],
    entry_points={
        'console_scripts': [
            'imdshift = IMDShift.imdshift:cli_handler',
        ],
    },
)