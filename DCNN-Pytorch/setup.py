import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()
package_name = "deepracing_models"
setup(
    name = package_name,
    version = "0.0.0",
    author = "Trent Weiss",
    author_email = "ttw2xk@virginia.edu",
    description = ("Some deepracing python stuff."),
    license = "BSD",
    keywords = "Some deepracing python stuff",
   # url = "http://packages.python.org/an_example_pypi_project",
    packages=[package_name,
              os.path.join(package_name,"data_loading"),
              os.path.join(package_name,"data_loading","proto_datasets"),
              os.path.join(package_name,"endtoend_controls"),
              os.path.join(package_name,"math_utils"),
              os.path.join(package_name,"nn_models"),
              os.path.join(package_name,"training_utils"),
              ],
   # long_description=read('README'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
    ],
    install_requires=open("requirements.txt").readlines(),
)