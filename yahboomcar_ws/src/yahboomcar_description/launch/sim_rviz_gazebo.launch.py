from ament_index_python.packages import get_package_share_path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, EnvironmentVariable, TextSubstitution

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
import os
import subprocess
from launch.actions import OpaqueFunction

def write_urdf_file(context, *args, **kwargs):
    model = LaunchConfiguration('model').perform(context)
    ns = LaunchConfiguration('ns').perform(context)

    urdf = subprocess.check_output(['xacro', model, f'ns:={ns}']).decode('utf-8')
    out_path = '/tmp/yahboomcar.urdf'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(urdf)
    return []

def generate_launch_description():
    pkg_path = get_package_share_path('yahboomcar_description')
    default_model_path = pkg_path / 'urdf/yahboomcar_X3.urdf.xacro'
    default_rviz_config_path = pkg_path / 'rviz/yahboomcar.rviz'
    default_world_path = pkg_path / 'worlds/cafe.world'   # <- pon cafe.world aquí

    # Para que Gazebo resuelva: model://yahboomcar_description/...
    # (porque tú estás usando model:// en los meshes)
    share_parent = str(pkg_path.parent)  # .../share
    set_gazebo_model_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=[
            TextSubstitution(text=share_parent),
            TextSubstitution(text=':'),
            EnvironmentVariable('GAZEBO_MODEL_PATH')
        ]
    )

    # Args
    gui_arg = DeclareLaunchArgument(
        name='gui', default_value='true', choices=['true', 'false'],
        description='Flag to enable joint_state_publisher_gui'
    )
    model_arg = DeclareLaunchArgument(
        name='model', default_value=str(default_model_path),
        description='Absolute path to robot urdf/xacro file'
    )
    rviz_arg = DeclareLaunchArgument(
        name='rvizconfig', default_value=str(default_rviz_config_path),
        description='Absolute path to rviz config file'
    )

    world_arg = DeclareLaunchArgument(
        name='world', default_value=str(default_world_path),
        description='Absolute path to Gazebo world file (e.g. cafe.world)'
    )
    gazebo_gui_arg = DeclareLaunchArgument(
        name='gazebo_gui', default_value='true', choices=['true', 'false'],
        description='Run Gazebo client (gzclient)'
    )

    ns_arg = DeclareLaunchArgument(
        name='ns', default_value='yahboomcar',
        description='Argument passed to xacro (ns:=...)'
    )

    generate_urdf_action = OpaqueFunction(function=write_urdf_file)

    spawn_entity_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        output='screen',
        arguments=[
            '-entity', LaunchConfiguration('entity'),
            '-file', '/tmp/yahboomcar.urdf',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
        ],
    )
    spawn_delayed = TimerAction(period=2.5, actions=[spawn_entity_node])

    entity_arg = DeclareLaunchArgument(
        name='entity', default_value='yahboomcar',
        description='Entity name in Gazebo'
    )
    x_arg = DeclareLaunchArgument(name='x', default_value='0.0')
    y_arg = DeclareLaunchArgument(name='y', default_value='0.0')
    z_arg = DeclareLaunchArgument(name='z', default_value='0.25')

    # robot_description desde xacro (pasando ns:=...)
    robot_description = ParameterValue(
        Command(['xacro ', LaunchConfiguration('model'), ' ns:=', LaunchConfiguration('ns')]),
        value_type=str
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen'
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        condition=UnlessCondition(LaunchConfiguration('gui')),
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    joint_state_publisher_gui_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        condition=IfCondition(LaunchConfiguration('gui')),
        output='screen'
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        parameters=[{'use_sim_time': True}],
    )

    # Iniciar Gazebo (gazebo.launch.py de gazebo_ros)
    gazebo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(get_package_share_path('gazebo_ros') / 'launch' / 'gazebo.launch.py')
        ),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'gui': LaunchConfiguration('gazebo_gui'),
            'verbose': 'true'
        }.items()
    )

    # Spawn del robot en Gazebo (desde PARAMETRO robot_description -> robusto)
    spawn_entity_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        output='screen',
        arguments=[
            '-entity', LaunchConfiguration('entity'),
            '-param', 'robot_description',
            '-x', LaunchConfiguration('x'),
            '-y', LaunchConfiguration('y'),
            '-z', LaunchConfiguration('z'),
        ],
        parameters=[{'robot_description': robot_description}]
    )

    # Espera un poquito a que Gazebo levante /spawn_entity
    spawn_delayed = TimerAction(period=2.5, actions=[spawn_entity_node])

    return LaunchDescription([
        set_gazebo_model_path,

        gui_arg, model_arg, rviz_arg,
        world_arg, gazebo_gui_arg,
        ns_arg, entity_arg, x_arg, y_arg, z_arg,

        gazebo_launch,

        joint_state_publisher_node,
        joint_state_publisher_gui_node,
        robot_state_publisher_node,

        # ... gazebo launch + robot_state_publisher + rviz
        generate_urdf_action,

        spawn_delayed,

        rviz_node,
    ])
