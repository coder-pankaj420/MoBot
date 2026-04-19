# MoBot 🤖
### Autonomous Mobile Robot — ROS 2 | SLAM | Nav2 | Obstacle Avoidance

MoBot is a differential-drive mobile robot built from scratch in ROS 2, capable of autonomous navigation using SLAM-generated maps and the Nav2 stack. This repository documents everything from robot modelling to full navigation pipeline deployment.

---

## 📁 Repository Structure

```
    └── mobot/                  # Main ROS 2 Python-type package
        ├── description/        # URDF & Xacro files
        │   ├── robot.urdf.xacro         # Top-level robot description
        │   ├── robot_core.xacro         # Chassis, wheels, castor wheel
        │   ├── gazebo_control.xacro     # Differential drive plugin
        │   ├── lidar.xacro              # LiDAR sensor + plugin
        │   ├── camera.xacro             # RGB camera
        │   └── depth_camera.xacro       # Depth camera
        ├── worlds/             # Custom Gazebo world files
        ├── config/             # Parameter YAML files
        │   ├── mapper_params_online_async.yaml   # SLAM Toolbox config
        │   └── nav2_params.yaml                  # Nav2 config
        ├── maps/               # Saved occupancy grid maps
        │   ├── my_map_save.pgm / .yaml      # map_saver_cli output
        │   └── my_map_serial.posegraph / .data  # SLAM Toolbox serialised map
        ├── mobot/              # ROS 2 Python nodes
        │   └── obstacle_avoid.py     # Reactive obstacle avoidance node
        ├── launch/             # Launch files
        │   ├── display.launch.py         # Visualise robot in RViz
        │   └── gazebo.launch.py          # Launch Gazebo simulation
        └── ...
```

---

## 🔧 Robot Description (URDF / Xacro)

MoBot's robot description is modular — the main entry point `robot.urdf.xacro` includes all sub-Xacro files:

### `robot_core.xacro`
Defines the physical structure of the robot:
- **Chassis** — base link with visual, collision, and inertial properties
- **Drive wheels** (left & right) — with visual, collision, and inertia tags
- **Castor wheel** — passive support wheel with proper inertial values

### `gazebo_control.xacro`
- **Differential Drive plugin** — maps velocity commands (`/cmd_vel`) to wheel joint efforts in Gazebo

### `lidar.xacro`
- **LiDAR sensor plugin** — publishes `/scan` topic (LaserScan)

### `camera.xacro`
- **RGB camera plugin** — publishes `/camera/image_raw`

### `depth_camera.xacro`
- **Depth camera plugin** — publishes `/depth_camera/depth/image_raw` and point cloud

---

## 🚀 Launch Files

| Launch File | Description |
|---|---|
| `display.launch.py` | Loads URDF, starts robot_state_publisher, joint_state_publisher, opens RViz |
| `gazebo.launch.py` | Spawns MoBot in custom Gazebo world with all sensor plugins active |

---

## 🌍 Custom Gazebo World

MoBot is tested in a custom-built Gazebo world featuring:
- Surrounding walls to define a closed environment
- Static obstacles placed inside for navigation testing

---

## 📡 Sensor Integration

All sensors are integrated as ROS 2 nodes publishing to standard topics with correct TF frames.

# LiDAR


# RGB Camera

# Depth Camera


## 🗺️ SLAM — Map Generation

SLAM is implemented using **SLAM Toolbox** in `online_async` mode.

**Config file:** `config/mapper_params_online_async.yaml`

**Run SLAM:**
```bash
ros2 launch slam_toolbox online_async_launch.py \
  params_file:=src/mobot/config/mapper_params_online_async.yaml
```

Drive MoBot around the environment to build the map.

---

### 💾 Saving the Map — Two Methods

Once mapping is complete, MoBot's map can be saved in two ways depending on the use case:

---

#### 1. `my_map_save` — Standard Save (map_saver_cli)

```bash
ros2 run nav2_map_server map_saver_cli -f src/mobot/maps/my_map_save
```

Generates:
- `my_map_save.pgm` — occupancy grid image (black = occupied, white = free, grey = unknown)
- `my_map_save.yaml` — metadata (resolution, origin, thresholds)

**Use case:** Loading the map with `nav2_map_server` for autonomous navigation using Nav2. This is the standard format used by the map server to serve the map during the navigation pipeline.

---

#### 2. `my_map_serial` — SLAM Toolbox Serialisation

In RViz, use the **SLAM Toolbox panel → Serialize Map** button, or via CLI:

```bash
ros2 service call /slam_toolbox/serialize_map slam_toolbox/srv/SerializePosegraph \
  "{filename: 'src/mobot/maps/my_map_serial'}"
```

Generates:
- `my_map_serial.posegraph` — pose graph with all node positions and constraints
- `my_map_serial.data` — raw scan data associated with each node

**Use case:** Resuming and continuing SLAM from where you left off — the robot can be re-localised into this map and continue mapping new areas without starting from scratch. More flexible than the standard save for ongoing mapping sessions.

---

| | `my_map_save` | `my_map_serial` |
|---|---|---|
| Format | `.pgm` + `.yaml` | `.posegraph` + `.data` |
| Used for | Nav2 navigation | Resuming / extending SLAM |
| Loaded by | `nav2_map_server` | SLAM Toolbox deserialise |
| Editable image | ✅ Yes | ❌ No |
| Resume mapping | ❌ No | ✅ Yes |

---

## 🌳 TF Tree

The TF tree defines the coordinate frame relationships between all robot links and sensors.

**View the TF tree:**
```bash
ros2 run tf2_tools view_frames
```
This generates a `frames.pdf` in your current directory.
---

## 🚧 Obstacle Avoidance Node

MoBot includes a reactive obstacle avoidance node written in Python that runs independently of the Nav2 stack, using raw LiDAR scan data to stop or steer away from obstacles in real time.

**File:** `mobot/obstacle_avoid.py`

### How it works
- Subscribes to `/scan` (LaserScan)
- Divides the scan into **front**, **left**, and **right** zones
- Publishes velocity commands to `/cmd_vel` based on zone readings:
  - No obstacle → move forward
  - Front blocked → stop and turn
  - Side blocked → steer away

### Run the node
```bash
ros2 run mobot obstacle_avoidance
```

### Topics

| Topic | Type | Role |
|---|---|---|
| `/scan` | `sensor_msgs/LaserScan` | Input — LiDAR data |
| `/cmd_vel` | `geometry_msgs/Twist` | Output — velocity commands |

### Key Parameters (tunable in code)
```python
SAFE_DISTANCE  = 0.4   # metres — minimum distance before reacting
FORWARD_SPEED  = 0.15  # m/s
TURN_SPEED     = 0.5   # rad/s
```


---

## 🧭 Navigation — Nav2 Pipeline

Autonomous navigation is handled by the **Nav2** stack using the saved SLAM map.

**Config file:** `config/nav2_params.yaml`

### Steps to run Navigation:

**1. Launch the map server and localise with AMCL:**
```bash
ros2 run nav2_map_server map_server --ros-args -p yaml_filename:=src/mobot/maps/my_map_save.yaml
ros2 run nav2_amcl amcl
```

**2. Set the map → odom TF (via CLI):**
```bash
ros2 run tf2_ros static_transform_publisher 0 0 0 0 0 0 map odom
```

**3. Send a navigation goal:**
```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: 'map'}, pose: {position: {x: 1.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
```

Or use the **2D Nav Goal** button in RViz for interactive goal setting.

---

## ⚙️ Configuration Files

### SLAM Toolbox — `mapper_params_online_async.yaml`
Key parameters:
- `mode: mapping` — online async SLAM mode
- `resolution`, `max_laser_range` — tuned for MoBot's LiDAR specs

### Nav2 — `nav2_params.yaml`
Key components configured:
- **Controller server** — local planner (DWA)
- **Planner server** — global planner (NavFn / A*)
- **AMCL** — particle filter localisation
- **Costmap** — inflation radius, obstacle layers

---

## 🛠️ Work In Progress

The following features are actively being developed:

- [ ] **PID velocity controller** — closed-loop speed control for smoother motion
- [ ] **ros2_control integration** — hardware abstraction layer for wheel controllers
- [ ] **Path planning benchmarking** — comparing A\*, DWA, and other planners
- [ ] **Hardware deployment** — testing on physical MoBot platform

---

## 📦 Dependencies

```bash
sudo apt install ros-humble-slam-toolbox
sudo apt install ros-humble-nav2-bringup
sudo apt install ros-humble-gazebo-ros-pkgs
sudo apt install ros-humble-ros2-control ros-humble-ros2-controllers
```

---

## 🏗️ Build & Run

```bash
# Clone and build
cd ~/mobot_ws
colcon build --symlink-install
source install/setup.bash

# Display robot in RViz
ros2 launch mobot display.launch.py

# Launch Gazebo simulation
ros2 launch mobot gazebo.launch.py 

# Run obstacle avoidance node
ros2 run mobot obstacle_avoidance
```

---

## 👤 Author

**Pankaj Talwar**
B.Tech Automation & Robotics Engineering — USAR, GGSIPU, Delhi
