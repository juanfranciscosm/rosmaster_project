from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():

    bridges = [

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge_colored_map',
            arguments=[
                '/cam_1/panoptic/colored_map'
                '@sensor_msgs/msg/Image'
                '@gz.msgs.Image'
            ],
            output='screen'
        ),

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge_labels_map',
            arguments=[
                '/cam_1/panoptic/labels_map'
                '@sensor_msgs/msg/Image'
                '@gz.msgs.Image'
            ],
            output='screen'
        ),

        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name='bridge_panoptic_info',
            arguments=[
                '/cam_1/panoptic/camera_info'
                '@sensor_msgs/msg/CameraInfo'
                '@gz.msgs.CameraInfo'
            ],
            output='screen'
        ),
    ]

    recorder = Node(
        package='depth_seg_dataset',
        executable='dataset_recorder',
        name='dataset_recorder',
        output='screen'
    )

    return LaunchDescription(bridges + [recorder])
