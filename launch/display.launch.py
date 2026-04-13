import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    
    pkg_path = get_package_share_directory('mobot')
    
    xacro_file= os.path.join(pkg_path,'description','robot.urdf.xacro')
    
    doc = xacro.process_file(xacro_file)
    robot_description = doc.toxml()
        
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}]
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui'
    )

    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
    )

    return LaunchDescription([
        robot_state_publisher,
        joint_state_publisher_gui,
        rviz2
    ])