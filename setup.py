from setuptools import setup

with open('biometrics_charts/version.py') as f:
    exec(f.read())


setup(
    name='biometrics_charts',
    description='This is a plugin for the biometrics-tracker application.  It produces charts and graphs of biometric readings)',
    version=__version__,
    packages=['biometrics_charts',
              ]
)
