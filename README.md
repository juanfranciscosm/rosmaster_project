# Yahboomcar X3 en Gazebo (ROS 2 Humble + Gazebo Classic 11)

Fuente: [Automatic Adisson](https://www.youtube.com/playlist?list=PLNWNEEf8BvG64FVZT4IdieI1PuYnHkUrt)

---

## Requisitos

- Ubuntu (recomendado 22.04)
- ROS 2 **Humble**
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
