from glob import glob

from setuptools import setup

setup(
    name='drawer_picking',
    version='0.2.0',
    packages=['drawer_picking'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/drawer_picking']),
        ('share/drawer_picking', ['package.xml']),
        ('share/drawer_picking/launch', glob('launch/*.launch.py')),
        ('share/drawer_picking/config', glob('config/*')),
        ('share/drawer_picking/meshes', glob('meshes/*.stl')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='B002 Future Lab',
    description='MyCobot 280 JN drawer picking state machine',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'drawer_state_machine = drawer_picking.main:main',
            'drawer_teach = drawer_picking.teach:main',
            'cabinet_marker = drawer_picking.cabinet:main',
        ],
    },
)
