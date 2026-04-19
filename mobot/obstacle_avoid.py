
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
import math


class ObstacleAvoidance(Node):

    def __init__(self):
        super().__init__('obstacle_avoidance')

        # Parameters — tune without recompiling
        self.declare_parameter('max_linear',       0.3)
        self.declare_parameter('max_angular',      0.8)
        self.declare_parameter('front_threshold',  0.8)   # start reacting (m)
        self.declare_parameter('stop_distance',    0.35)  # hard stop (m)

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)

        self.get_logger().info('Smooth obstacle avoidance started.')

    # ── Min range within a degree sector ──────────────────────────────────
    def sector_min(self, msg: LaserScan, start_deg: float, end_deg: float) -> float:
        min_r = math.inf
        angle = msg.angle_min

        for r in msg.ranges:
            deg = math.degrees(angle)
            if start_deg <= deg <= end_deg:
                if math.isfinite(r) and msg.range_min < r < msg.range_max:
                    min_r = min(min_r, r)
            angle += msg.angle_increment

        return min_r

    # ── Cosine ease: 0.0 at stop_dist, 1.0 at threshold ──────────────────
    def smooth_factor(self, dist: float, stop_dist: float, threshold: float) -> float:
        if dist <= stop_dist:
            return 0.0
        if dist >= threshold:
            return 1.0
        t = (dist - stop_dist) / (threshold - stop_dist)   # 0 → 1
        return 0.5 * (1.0 - math.cos(t * math.pi))         # cosine ease

    # ── Repulsion strength: 0 (far) → 1 (very close) ─────────────────────
    def repulsion(self, dist: float, max_dist: float) -> float:
        if not math.isfinite(dist) or dist >= max_dist:
            return 0.0
        return 1.0 - (dist / max_dist)

    # ── Main scan callback ────────────────────────────────────────────────
    def scan_callback(self, msg: LaserScan):
        max_linear      = self.get_parameter('max_linear').value
        max_angular     = self.get_parameter('max_angular').value
        front_threshold = self.get_parameter('front_threshold').value
        stop_distance   = self.get_parameter('stop_distance').value

        # Sector readings
        front       = self.sector_min(msg, -30.0,  30.0)
        front_left  = self.sector_min(msg,  30.0,  60.0)
        front_right = self.sector_min(msg, -60.0, -30.0)
        left        = self.sector_min(msg,  60.0,  90.0)
        right       = self.sector_min(msg, -90.0, -60.0)

        cmd = Twist()

        # ── 1. Linear velocity: cosine-smoothed ──
        lin_scale    = self.smooth_factor(front, stop_distance, front_threshold)
        cmd.linear.x = max_linear * lin_scale

        # ── 2. Angular velocity: weighted repulsion ──
        # Right obstacles push LEFT (+z), left obstacles push RIGHT (-z)
        push = (
              self.repulsion(front_right, front_threshold) * 1.5   # front sectors weighted more
            - self.repulsion(front_left,  front_threshold) * 1.5
            + self.repulsion(right,       front_threshold) * 0.8
            - self.repulsion(left,        front_threshold) * 0.8
        )

        push          = max(-1.0, min(1.0, push))   # clamp to [-1, 1]
        cmd.angular.z = max_angular * push

        # ── 3. Hard stop safety override ──
        if front <= stop_distance:
            cmd.linear.x  = 0.0
            cmd.angular.z = max_angular if push >= 0.0 else -max_angular
            self.get_logger().warn(f'HARD STOP — too close! ({front:.2f} m)')

        self.get_logger().info(
            f'front={front:.2f} lin={cmd.linear.x:.2f} ang={cmd.angular.z:.2f} | '
            f'FL={front_left:.2f} FR={front_right:.2f} L={left:.2f} R={right:.2f}'
        )

        self.cmd_pub.publish(cmd)


def main(args=None):
    rclpy.init(args=args)
    node = ObstacleAvoidance()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()