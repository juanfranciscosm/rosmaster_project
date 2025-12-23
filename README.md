# Yahboomcar X3 en Gazebo (ROS2 Jazzy + Gazebo)

Fuente: [Automatic Adisson](https://www.youtube.com/playlist?list=PLNWNEEf8BvG64FVZT4IdieI1PuYnHkUrt)

---

## Requisitos

- Ubuntu (recomendado 24.04)
- ROS 2 **Jazzy Jalisco**
- **Gazebo Classic 11**
- Instalar dependencias desde **yahboomcar_ws/**
```bash
rosdep install -i --from-path src --rosdistro $ROS_DISTRO -y
```

# Visualizar simulacion en rviz

Puedes agregar al final de `~/.bashrc`:

```bash
echo "alias yahboom='ros2 launch urdf_tutorial display.launch.py model:=/home/juafrsan/Desktop/rosmaster_project/yahboomcar_ws/src/yahboom_rosmaster/yahboom_rosmaster_description/urdf/robots/rosmaster_x3.urdf.xacro'" >> ~/.bashrc
```

Luego:

```bash
source ~/.bashrc
```

```bash
yahbooom
```



## Run a world

From the repository root:

```bash
cd yahboom_rosmaster_gazebo
export IGN_GAZEBO_RESOURCE_PATH="$PWD/models:$PWD/worlds:$IGN_GAZEBO_RESOURCE_PATH"
ign gazebo -r -v 4 worlds/example.world
```

- `-r` runs in real time  
- `-v 4` increases verbosity for debugging
