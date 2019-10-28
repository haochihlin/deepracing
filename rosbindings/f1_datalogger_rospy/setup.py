from setuptools import find_packages
from setuptools import setup
import os
package_name = 'f1_datalogger_rospy'

setup(
    name=package_name,
    version='0.0.0',
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    author='Trent Weiss',
    author_email='ttw2xk@virginia.edu',
    maintainer='Trent Weiss',
    maintainer_email='ttw2xk@virginia.edu',
    keywords=['ROS'],
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Topic :: Software Development',
    ],
    description=(
        'A package for utilizing the F1 Datalogger in Python'
    ),
    license='Apache License, Version 2.0',
    tests_require=['pytest'],
    packages=list(set(find_packages(exclude=['test'])+[
                os.path.join(package_name,"controls"),
              ])),

    entry_points={
        'console_scripts': [
            'pose_publisher = %s.scripts.pose_publisher:main' % (package_name),
            'pure_pursuit = %s.scripts.admiralnet_endtoend:main' % (package_name),
            # 'talker = demo_nodes_py.topics.talker:main',
            # 'listener_qos = demo_nodes_py.topics.listener_qos:main',
            # 'talker_qos = demo_nodes_py.topics.talker_qos:main',
            # 'listener_serialized = demo_nodes_py.topics.listener_serialized:main',
            # 'add_two_ints_client = demo_nodes_py.services.add_two_ints_client:main',
            # 'add_two_ints_client_async = demo_nodes_py.services.add_two_ints_client_async:main',
            # 'add_two_ints_server = demo_nodes_py.services.add_two_ints_server:main'
        ],
    },
)