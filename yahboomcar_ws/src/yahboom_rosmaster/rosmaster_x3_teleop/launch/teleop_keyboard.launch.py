from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package="rosmaster_x3_teleop",
            executable="keyboard_teleop",
            name="keyboard_teleop",
            output="screen",
            emulate_tty=True,
            parameters=[{
                "cmd_vel_topic": "/mecanum_drive_controller/cmd_vel",
                "use_stamped_vel": True,   #True si /cmd_vel es TwistStamped
                "vx": 0.25,
                "vy": 0.25,
                "wz": 0.8,
                "publish_rate": 20.0,
                "stop_timeout": 0.4,
            }],
        )
    ])