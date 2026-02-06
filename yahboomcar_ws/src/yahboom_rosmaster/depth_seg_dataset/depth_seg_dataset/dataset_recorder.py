import rclpy
from rclpy.node import Node
from message_filters import Subscriber, ApproximateTimeSynchronizer
from sensor_msgs.msg import Image, PointCloud2
from sensor_msgs_py import point_cloud2
from cv_bridge import CvBridge
import numpy as np
import cv2
import os
import math

def rosimg_to_numpy_raw(img_msg: Image) -> np.ndarray:
    h, w = img_msg.height, img_msg.width
    enc = (img_msg.encoding or "").lower()

    if enc in ("rgb8", "bgr8"):
        return np.frombuffer(img_msg.data, dtype=np.uint8).reshape(h, w, 3)
    if enc in ("rgba8", "bgra8"):
        return np.frombuffer(img_msg.data, dtype=np.uint8).reshape(h, w, 4)
    if enc in ("mono8",):
        return np.frombuffer(img_msg.data, dtype=np.uint8).reshape(h, w)
    if enc in ("mono16", "16uc1"):
        return np.frombuffer(img_msg.data, dtype=np.uint16).reshape(h, w)
    if enc in ("32fc1",):
        return np.frombuffer(img_msg.data, dtype=np.float32).reshape(h, w)

    raise RuntimeError(f"Encoding no soportado: {img_msg.encoding}")

def pointcloud_to_range_map(pc_msg: PointCloud2) -> np.ndarray:
    """Devuelve un mapa (H,W) con distancia euclidiana (m). Requiere PointCloud organizado."""
    width, height = pc_msg.width, pc_msg.height
    if height <= 1:
        raise RuntimeError(
            f"PointCloud NO organizado (height={height}). No se puede mapear 1:1 a imagen."
        )

    # Lee x,y,z en el orden en que vienen
    pts = point_cloud2.read_points(pc_msg, field_names=("x", "y", "z"), skip_nans=False)

    rng = np.full((height, width), np.nan, dtype=np.float32)
    for i, (x, y, z) in enumerate(pts):
        row = i // width
        col = i % width
        if math.isfinite(x) and math.isfinite(y) and math.isfinite(z):
            rng[row, col] = math.sqrt(x*x + y*y + z*z)
    return rng

def decode_panoptic_class_instance(label_raw: np.ndarray, encoding: str):
    """
    Decodifica /panoptic/labels_map (HxWx3 uint8) a:
      - class_id: uint16 (1..106)
      - instance_id: uint16 (0..65535)
    
    Convención típica en Gazebo panoptic:
      RGB8:   [R,G,B] => class_id = B, instance = R + (G<<8)
      BGR8:   [B,G,R] => class_id = R, instance = B + (G<<8)
    """
    enc = (encoding or "").lower()
    if label_raw.ndim != 3 or label_raw.shape[2] < 3 or label_raw.dtype != np.uint8:
        raise RuntimeError(f"labels_map inesperado: shape={label_raw.shape}, dtype={label_raw.dtype}, enc={encoding}")

    if enc.startswith("rgb"):
        r = label_raw[:, :, 0].astype(np.uint16)
        g = label_raw[:, :, 1].astype(np.uint16)
        b = label_raw[:, :, 2].astype(np.uint16)
        class_id = b
        instance_id = r + (g << 8)
        return class_id, instance_id

    if enc.startswith("bgr"):
        b = label_raw[:, :, 0].astype(np.uint16)
        g = label_raw[:, :, 1].astype(np.uint16)
        r = label_raw[:, :, 2].astype(np.uint16)
        class_id = r
        instance_id = b + (g << 8)
        return class_id, instance_id

    # Si no sabes el encoding, intenta como rgb (es lo más común)
    r = label_raw[:, :, 0].astype(np.uint16)
    g = label_raw[:, :, 1].astype(np.uint16)
    b = label_raw[:, :, 2].astype(np.uint16)
    class_id = b
    instance_id = r + (g << 8)
    return class_id, instance_id

class DatasetRecorder(Node):
    def __init__(self):
        super().__init__("dataset_recorder")

        base_dir = "/home/robotica-cidis/Documentos/rosmaster_project/dataset"
        self.rgb_dir = f"{base_dir}/rgb"
        self.depth_dir = f"{base_dir}/depth"
        self.seg_color_dir = f"{base_dir}/seg_colored"
        self.seg_label_dir = f"{base_dir}/seg_labels"

        for d in [self.rgb_dir, self.depth_dir, self.seg_color_dir, self.seg_label_dir]:
            os.makedirs(d, exist_ok=True)

        self.bridge = CvBridge()

        self.save_interval = 1.0
        self.last_save_time = self.get_clock().now()
        self._printed_encodings = False

        self.rgb_sub = Subscriber(self, Image, "/cam_1/color/image_raw")
        self.pc_sub = Subscriber(self, PointCloud2, "/cam_1/depth/color/points")
        self.seg_color_sub = Subscriber(self, Image, "/cam_1/panoptic/colored_map")
        self.seg_label_sub = Subscriber(self, Image, "/cam_1/panoptic/labels_map")

        self.sync = ApproximateTimeSynchronizer(
            [self.rgb_sub, self.pc_sub, self.seg_color_sub, self.seg_label_sub],
            queue_size=50,
            slop=0.2,
        )
        self.sync.registerCallback(self.callback)
        self.get_logger().info("Dataset recorder started")

    def callback(self, rgb: Image, pc: PointCloud2, seg_color: Image, seg_label: Image):
        now = self.get_clock().now()
        dt = (now - self.last_save_time).nanoseconds * 1e-9
        if dt < self.save_interval:
            return

        stamp = rgb.header.stamp.sec * 1_000_000_000 + rgb.header.stamp.nanosec

        if not self._printed_encodings:
            self.get_logger().info(f"ENC rgb: {rgb.encoding}")
            self.get_logger().info(f"ENC seg_color: {seg_color.encoding}")
            self.get_logger().info(f"ENC seg_label: {seg_label.encoding}")
            self.get_logger().info(f"PC frame_id: {pc.header.frame_id} height={pc.height} width={pc.width}")
            self._printed_encodings = True

        # RGB
        rgb_img = self.bridge.imgmsg_to_cv2(rgb, desired_encoding="bgr8")
        cv2.imwrite(f"{self.rgb_dir}/{stamp}.png", rgb_img)

        # Seg colored
        seg_color_img = self.bridge.imgmsg_to_cv2(seg_color, desired_encoding="bgr8")
        cv2.imwrite(f"{self.seg_color_dir}/{stamp}.png", seg_color_img)

        # Seg labels RAW + ids (FUENTE DE VERDAD)
        # 3) Seg labels RAW
        seg_label_raw = rosimg_to_numpy_raw(seg_label)
        np.save(f"{self.seg_label_dir}/{stamp}_raw.npy", seg_label_raw)

        # 3b) Decodifica panoptic: clase + instancia
        class_id, instance_id = decode_panoptic_class_instance(seg_label_raw, seg_label.encoding)
        np.save(f"{self.seg_label_dir}/{stamp}_class.npy", class_id)       # uint16
        np.save(f"{self.seg_label_dir}/{stamp}_instance.npy", instance_id) # uint16

        # (Opcional) preview para ver la clase (NO para IDs)
        # normaliza class_id a 0..255
        class_vis = (class_id.astype(np.float32) * (255.0 / max(1.0, float(class_id.max())))).astype(np.uint8)
        cv2.imwrite(f"{self.seg_label_dir}/{stamp}_class_preview.png", class_vis)


        # Depth: usa DISTANCIA euclidiana (m)
        rng_m = pointcloud_to_range_map(pc)  # float32 (m)
        np.save(f"{self.depth_dir}/{stamp}.npy", rng_m)

        rng_mm = np.nan_to_num(rng_m * 1000.0, nan=0.0, posinf=0.0, neginf=0.0).astype(np.uint16)
        cv2.imwrite(f"{self.depth_dir}/{stamp}.png", rng_mm)

        self.get_logger().info(f"Saved frame {stamp}")
        self.last_save_time = now

def main(args=None):
    rclpy.init(args=args)
    node = DatasetRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
