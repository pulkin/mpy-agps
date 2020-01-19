from setuptools import setup
import sdist_upip

setup(name='micropython-agps',
      version='0.1.1',
      description='Assisted location services for MicroPython',
      long_description=open("README.md", 'r').read(),
      long_description_content_type='text/markdown',
      url='https://github.com/pulkin/mpy-agps',
      author='pulkin',
      author_email='gpulkin@gmail.com',
      cmdclass={'sdist': sdist_upip.sdist},
      py_modules=['agps'])
