from ament_index_python.packages import get_package_share_path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_desc = get_package_share_path('yahboomcar_description')
    pkg_gazebo = get_package_share_path('gazebo_ros')

    default_model_path = pkg_desc / 'urdf/yahboomcar_X3.urdf'
    default_rviz_config_path = pkg_desc / 'rviz/yahboomcar.rviz'
    default_world_path = pkg_gazebo / 'worlds/empty.world'  # puedes cambiarlo por tu world

    # Args
    gui_arg = DeclareLaunchArgument(
        name='gui', default_value='false', choices=['true', 'false'],
        description='Joint state publisher GUI'
    )
    rviz_enable_arg = DeclareLaunchArgument(
        name='rviz', default_value='false', choices=['true', 'false'],
        description='Open RViz'
    )
    model_arg = DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='Absolute path to robot urdf/xacro'
    )
    rviz_arg = DeclareLaunchArgument(
        name='rvizconfig', default_value=str(default_rviz_config_path),
        description='Absolute path to rviz config file'
    )
    world_arg = DeclareLaunchArgument(
        name='world', default_value=str(default_world_path),
        description='Absolute path to world file (.world)'
    )
    use_sim_time_arg = DeclareLaunchArgument(
        name='use_sim_time', default_value='true', choices=['true', 'false'],
        description='Use simulation time'
    )

    # Robot description (si tu archivo es URDF puro igual suele funcionar con xacro)
    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('model')]),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        condition=UnlessCondition(LaunchConfiguration('gui')),
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('gui')),
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # Start Gazebo (Classic) with a world
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(pkg_gazebo / 'launch' / 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': LaunchConfiguration('world')
        }.items()
    )

    # Spawn robot into Gazebo from robot_description topic
    spawn_entity_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'yahboomcar_x3',
            '-x', '0.0', '-y', '0.0', '-z', '0.15'
        ]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    return LaunchDescription([
        gui_arg,
        rviz_enable_arg,
        model_arg,
        rviz_arg,
        world_arg,
        use_sim_time_arg,

        robot_state_publisher_node,
        joint_state_publisher_node,
        joint_state_publisher_gui_node,

        gazebo_launch,
        spawn_entity_node,

        rviz_node,
    ])
