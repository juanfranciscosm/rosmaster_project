#!/usr/bin/env python3
import sys
import select
import termios
import tty
from dataclasses import dataclass

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TwistStamped


@dataclass
class Vel:
    x: float = 0.0   # forward/back
    y: float = 0.0   # left/right strafe (mecanum)
    wz: float = 0.0  # yaw


HELP = """
TELEOP Rosmaster X3 (ROS 2 Jazzy)
--------------------------------
Movimiento (mecanum):
  W/S : +X / -X (adelante / atrás)
  A/D : +Y / -Y (izq / der - strafe)
  Q/E : +Wz / -Wz (giro izq / der)

Velocidad:
  +   : aumenta escala
  -   : reduce escala

Seguridad:
  SPACE o X : STOP (0,0,0)
  CTRL-C    : salir
"""


def get_key(stream, timeout: float) -> str:
    rlist, _, _ = select.select([stream], [], [], timeout)
    if rlist:
        return stream.read(1)
    return ""


class KeyboardTeleop(Node):
    def __init__(self):
        super().__init__("keyboard_teleop")

        # Parámetros básicos
        self.declare_parameter("cmd_vel_topic", "/mecanum_drive_controller/cmd_vel")
        self.declare_parameter("use_stamped_vel", True)  # True => TwistStamped
        self.declare_parameter("frame_id", "base_link")

        # Velocidades base (m/s y rad/s)
        self.declare_parameter("vx", 0.25)
        self.declare_parameter("vy", 0.25)
        self.declare_parameter("wz", 0.8)

        # Escala y límites
        self.declare_parameter("scale", 1.0)
        self.declare_parameter("scale_step", 0.1)
        self.declare_parameter("scale_min", 0.1)
        self.declare_parameter("scale_max", 2.5)

        # Publicación / seguridad
        self.declare_parameter("publish_rate", 20.0)   # Hz
        self.declare_parameter("stop_timeout", 0.4)    # s sin tecla => STOP

        self.cmd_vel_topic = self.get_parameter("cmd_vel_topic").value
        self.use_stamped = bool(self.get_parameter("use_stamped_vel").value)
        self.frame_id = self.get_parameter("frame_id").value

        self.vx = float(self.get_parameter("vx").value)
        self.vy = float(self.get_parameter("vy").value)
        self.wz = float(self.get_parameter("wz").value)

        self.scale = float(self.get_parameter("scale").value)
        self.scale_step = float(self.get_parameter("scale_step").value)
        self.scale_min = float(self.get_parameter("scale_min").value)
        self.scale_max = float(self.get_parameter("scale_max").value)

        self.publish_rate = float(self.get_parameter("publish_rate").value)
        self.stop_timeout = float(self.get_parameter("stop_timeout").value)

        if self.use_stamped:
            self.pub = self.create_publisher(TwistStamped, self.cmd_vel_topic, 10)
        else:
            self.pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)

        self.vel = Vel()
        self.last_key_time = self.get_clock().now()

        self.timer = self.create_timer(1.0 / self.publish_rate, self._on_timer)

        self.get_logger().info(f"Publicando a: {self.cmd_vel_topic} | stamped={self.use_stamped}")
        self.get_logger().info(HELP)

    def _on_timer(self):
        # Si pasó mucho tiempo sin tecla, frenamos
        dt = (self.get_clock().now() - self.last_key_time).nanoseconds / 1e9
        if dt > self.stop_timeout:
            self.vel = Vel(0.0, 0.0, 0.0)

        # Publicar
        if self.use_stamped:
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = self.frame_id
            msg.twist.linear.x = self.vel.x
            msg.twist.linear.y = self.vel.y
            msg.twist.angular.z = self.vel.wz
            self.pub.publish(msg)
        else:
            msg = Twist()
            msg.linear.x = self.vel.x
            msg.linear.y = self.vel.y
            msg.angular.z = self.vel.wz
            self.pub.publish(msg)

    def handle_key(self, key: str):
        key = key.lower()
        moved = True

        if key == "w":
            self.vel.x = +self.vx * self.scale
            self.vel.y = 0.0
            self.vel.wz = 0.0
        elif key == "s":
            self.vel.x = -self.vx * self.scale
            self.vel.y = 0.0
            self.vel.wz = 0.0
        elif key == "a":
            self.vel.y = +self.vy * self.scale
            self.vel.x = 0.0
            self.vel.wz = 0.0
        elif key == "d":
            self.vel.y = -self.vy * self.scale
            self.vel.x = 0.0
            self.vel.wz = 0.0
        elif key == "q":
            self.vel.wz = +self.wz * self.scale
            self.vel.x = 0.0
            self.vel.y = 0.0
        elif key == "e":
            self.vel.wz = -self.wz * self.scale
            self.vel.x = 0.0
            self.vel.y = 0.0
        elif key in [" ", "x"]:
            self.vel = Vel(0.0, 0.0, 0.0)
        elif key == "+":
            self.scale = min(self.scale_max, self.scale + self.scale_step)
            self.get_logger().info(f"scale={self.scale:.2f}")
            moved = False
        elif key == "-":
            self.scale = max(self.scale_min, self.scale - self.scale_step)
            self.get_logger().info(f"scale={self.scale:.2f}")
            moved = False
        else:
            moved = False

        if moved:
            self.last_key_time = self.get_clock().now()


def main():
    stream = sys.stdin
    if not stream.isatty():
        try:
            stream = open('/dev/tty')
        except OSError:
            print("ERROR: No hay TTY disponible para leer teclado. Ejecuta en una terminal real.", file=sys.stderr)
            return 1

    settings = termios.tcgetattr(stream)
    tty.setcbreak(stream.fileno())

    rclpy.init()
    node = KeyboardTeleop()

    try:
        while rclpy.ok():
            key = get_key(stream, 0.05)
            if key:
                if key == "\x03":
                    break
                node.handle_key(key)
            rclpy.spin_once(node, timeout_sec=0.0)
    finally:
        node.get_logger().info("Saliendo y enviando STOP...")
        node.vel = Vel(0.0, 0.0, 0.0)
        for _ in range(5):
            rclpy.spin_once(node, timeout_sec=0.0)
        node.destroy_node()
        rclpy.shutdown()
        termios.tcsetattr(stream, termios.TCSADRAIN, settings)
        if stream is not sys.stdin:
            stream.close()

    return 0

if __name__ == "__main__":
    main()
