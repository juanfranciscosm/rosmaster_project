# Yahboomcar X3 en Gazebo (ROS 2 Humble + Gazebo Classic 11)

Guía **estándar** (replicable en otra PC) para que el robot **aparezca en el escenario** de Gazebo.

El problema típico cuando *solo aparece en la lista* es que Gazebo **no encuentra los meshes (.STL)**, entonces el modelo se spawnea “vacío”.

---

## Requisitos

- Ubuntu (recomendado 22.04)
- ROS 2 **Humble**
- **Gazebo Classic 11**
- Workspace con `yahboomcar_description` (y el resto del robot) compilado con `colcon`

---

## 1) Compilar el workspace

```bash
cd ~/Desktop/rosmaster_project/yahboomcar_ws
colcon build --symlink-install
```

---

## 2) Cargar entorno (ROS + Gazebo + workspace)

En **cada terminal** donde vayas a correr Gazebo o spawnear el robot:

```bash
source /opt/ros/humble/setup.bash
source /usr/share/gazebo/setup.sh
source ~/Desktop/rosmaster_project/yahboomcar_ws/install/setup.bash
```

> Esto también evita el warning de shaders: `GAZEBO_RESOURCE_PATH ... improperly set`.

---

## 3) ✅ Paso CLAVE: hacer que Gazebo encuentre los meshes

Si tu URDF / `robot_description` referencia meshes como:

- `model://yahboomcar_description/meshes/...`

entonces Gazebo debe poder resolver `yahboomcar_description` dentro de su “model path”.

### Opción A (la más segura): symlink a `~/.gazebo/models`

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/rosmaster_project/yahboomcar_ws/install/setup.bash

PKG_PREFIX=$(ros2 pkg prefix yahboomcar_description)

mkdir -p ~/.gazebo/models
rm -rf ~/.gazebo/models/yahboomcar_description
ln -s "$PKG_PREFIX/share/yahboomcar_description" ~/.gazebo/models/yahboomcar_description
```

### Opción B (alternativa): exportar `GAZEBO_MODEL_PATH`

```bash
source /opt/ros/humble/setup.bash
source ~/Desktop/rosmaster_project/yahboomcar_ws/install/setup.bash

PKG_PREFIX=$(ros2 pkg prefix yahboomcar_description)
export GAZEBO_MODEL_PATH="$PKG_PREFIX/share:${GAZEBO_MODEL_PATH}"
echo $GAZEBO_MODEL_PATH
```

> Usa **A o B**. Si no haces esto, verás errores tipo `Failed to find mesh file ...STL` y el robot no se renderiza.

---

## 4) Reiniciar Gazebo y lanzar el mundo

Si te sale `Address already in use` (ya hay un `gzserver` corriendo):

```bash
killall -9 gzserver gzclient gazebo 2>/dev/null
```

Lanzar mundo vacío:

```bash
ros2 launch gazebo_ros gazebo.launch.py world:=/usr/share/gazebo-11/worlds/empty.world verbose:=true
```

---

## 5) Lanzar simulacion de RVIZ

En otra terminal (con el entorno sourceado):

```bash
ros2 launch yahboomcar_description display_X3.launch.py
```

---

## 6) Spawnear el robot (con altura)

En otra terminal (con el entorno sourceado):

```bash
ros2 run gazebo_ros spawn_entity.py -topic robot_description -entity yahboomcar -x 0 -y 0 -z 0.25

```

---

## Troubleshooting rápido

### Robot aparece en la lista, pero NO se ve (ni con Collisions)
Casi siempre es **ruta de meshes**.

- Revisa la consola de `gzserver`:
  - Si ves: `Failed to find mesh file ...STL` → repite el **Paso 3** y **reinicia Gazebo**.

### Warning de shaders / recursos
- Asegura que ejecutaste:
  ```bash
  source /usr/share/gazebo/setup.sh
  ```

### `Address already in use`
- Mata procesos de Gazebo:
  ```bash
  killall -9 gzserver gzclient gazebo
  ```

---

## (Opcional) Hacerlo permanente en la PC

Puedes agregar al final de `~/.bashrc`:

```bash
# ROS 2 + Gazebo (Yahboomcar)
source /opt/ros/humble/setup.bash
source /usr/share/gazebo/setup.sh
source ~/Desktop/rosmaster_project/yahboomcar_ws/install/setup.bash
export GAZEBO_MODEL_PATH="$(ros2 pkg prefix yahboomcar_description)/share:${GAZEBO_MODEL_PATH}"
```

Luego:

```bash
source ~/.bashrc
```
