from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource

import os
import xacro
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_path = get_package_share_directory('mobot')
    
    xacro_file= os.path.join(pkg_path,'description','robot.urdf.xacro')
    
    doc = xacro.process_file(xacro_file)
    robot_description = doc.toxml()

    # 🔹 Start Gazebo
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('gazebo_ros'),
                'launch',
                'gazebo.launch.py'
            )
        )
    )

    return LaunchDescription([

        # 1️⃣ Launch Gazebo
        gazebo,

        # 2️⃣ Publish robot description
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}]
        ),
        
        

        # 3️⃣ Spawn robot
        Node(
            package='gazebo_ros',
            executable='spawn_entity.py',
            arguments=[
            '-topic', '/robot_description',
            '-entity', 'my_robot',
            '-z', '-0.05'],
            
            output='screen'
        )
    ])