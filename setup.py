from setuptools import setup, find_packages

setup(
    name='SentinelUE4Tools',
    version='1.0',
    py_modules=['Sentinel','commands','CONSTANTS','editor','utilities','standalone'],
    packages=find_packages(),
    entry_points='''
        [console_scripts]
        sentinel=Sentinel:cli
    ''',
)
