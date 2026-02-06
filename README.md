# ROSMASTER X3 + Gazebo Sim (ROS 2 Jazzy) + Dataset RGB‑D + Segmentación (Panoptic)

Proyecto de simulación del **Yahboom ROSMASTER X3** en **Gazebo Sim** (ROS 2 **Jazzy**) con:

- **Teleoperación por teclado**
- **Generación de dataset** automático para:
  - **RGB** (`rgb/`)
  - **Depth** en metros por píxel (`depth/`)
  - **Segmentación coloreada** (`seg_colored/`)
  - **Segmentación por labels** (`seg_labels/`)

> Dataset pensado para **segmentación** y **profundidad** usando una cámara **RGB‑D** y una cámara de **segmentación/panoptic**.

---

## 🧭 Tabla de contenidos

- [Requisitos](#-requisitos)
- [Descarga del repositorio](#-descarga-del-repositorio)
- [Instalación de dependencias](#-instalación-de-dependencias)
- [Compilación del workspace](#-compilación-del-workspace)
- [Iniciar la simulación](#-iniciar-la-simulación)
- [Cambiar de mundo](#-cambiar-de-mundo)
- [Teleoperación (teclado)](#-teleoperación-teclado)
- [Generación del dataset (RGB‑D + Segmentación)](#-generación-del-dataset-rgb-d--segmentación)
- [Estructura del dataset](#-estructura-del-dataset)
- [Visualizador del dataset](#-visualizador-del-dataset)
- [Clases (labels) y diccionario](#-clases-labels-y-diccionario)
- [Agregar nuevas clases (Label plugin)](#-agregar-nuevas-clases-label-plugin)
- [Troubleshooting](#-troubleshooting)
- [Estructura del proyecto](#-estructura-del-proyecto)

---

## ✅ Requisitos

Entorno probado:

- **Ubuntu 24.04.3 LTS (noble)**, sesión **X11**
- **ROS 2 Jazzy**
- **Gazebo Sim 8.10.0** (`gz-sim8`)

---

## ⬇️ Descarga del repositorio

Repositorio remoto:

- `https://github.com/juanfranciscosm/rosmaster_project.git`

Clonar:

```bash
git clone https://github.com/juanfranciscosm/rosmaster_project.git
cd rosmaster_project
```

---

## 📦 Instalación de dependencias

### 1) Dependencias ROS (rosdep)

Desde el workspace `yahboomcar_ws`:

```bash
cd yahboomcar_ws
source /opt/ros/jazzy/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

> Esto resuelve dependencias declaradas en los `package.xml`.

### 2) Dependencias Python (visualizador / herramientas)

```bash
python3 -m pip install --user opencv-python numpy
```

---

## 🏗️ Compilación del workspace

```bash
cd yahboomcar_ws
source /opt/ros/jazzy/setup.bash
colcon build
source install/setup.bash
```

### Alias útiles (opcional)

Puedes agregar en tu `~/.bashrc`:

```bash
alias build='cd ~/Documentos/rosmaster_project/yahboomcar_ws && colcon build && source ~/.bashrc'
alias x3='bash ~/Documentos/rosmaster_project/yahboomcar_ws/src/yahboom_rosmaster/yahboom_rosmaster_bringup/scripts/rosmaster_x3_gazebo.sh'
```

> Si tienes problemas compilando dentro de un entorno conda (`(base)`), prueba:
> ```bash
> conda deactivate
> cd ~/Documentos/rosmaster_project/yahboomcar_ws
> rm -rf build log install
> colcon build
> ```

---

## ▶️ Iniciar la simulación

### Opción A (recomendada): script `rosmaster_x3_gazebo.sh`

```bash
cd ~/Documentos/rosmaster_project/yahboomcar_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
x3
```

El script lanza Gazebo + controladores (y usa el `launch` del paquete `yahboom_rosmaster_gazebo`).

---

## 🌍 Cambiar de mundo

Para modificar el mundo con el que inicia la simulación (y por tanto el dataset), edita:

```text
~/Documentos/rosmaster_project/yahboomcar_ws/src/yahboom_rosmaster/yahboom_rosmaster_bringup/scripts/rosmaster_x3_gazebo.sh
```

Busca el argumento `world_file:=...` y cámbialo, por ejemplo:

```bash
world_file:=hospital.world
```

### Poses recomendadas por mundo

En el mismo script se suelen ajustar **x/y/z** iniciales del robot. Configuración típica:

- `house.world` → `x:=0.0 y:=0.0 z:=0.05`
- `bookstore.world` → `x:=0.0394 y:=1.5786 z:=0.05`
- `service.world` → `x:=0.0 y:=2.0 z:=0.1`
- `hospital.world` → `x:=0.0 y:=2.0 z:=0.1`

### (Opcional) Mover la cámara del GUI de Gazebo

Ejemplo:

```bash
gz service -s /gui/move_to/pose --reqtype gz.msgs.GUICamera --reptype gz.msgs.Boolean --timeout 2000 --req "pose: {position: {x: 0.0, y: -2.0, z: 2.0} orientation: {x: -0.2706, y: 0.2706, z: 0.6533, w: 0.6533}}"
```

---

## 🕹️ Teleoperación (teclado)

Con la simulación corriendo, en **otra terminal**:

```bash
cd ~/Documentos/rosmaster_project/yahboomcar_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch rosmaster_x3_teleop teleop_keyboard.launch.py
```

Controles (mecanum):

- `W/S`: +X / -X (adelante / atrás)
- `A/D`: +Y / -Y (izq / der, strafe)
- `Q/E`: +Wz / -Wz (giro izq / der)
- `+` / `-`: aumenta / reduce escala
- `SPACE` o `X`: STOP
- `CTRL+C`: salir

---

## 🗂️ Generación del dataset (RGB‑D + Segmentación)

En una **tercera terminal** inicia el recorder:

```bash
cd ~/Documentos/rosmaster_project/yahboomcar_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch depth_seg_dataset dataset_with_bridge.launch.py
```

Este launch levanta el **nodo recorder** (paquete `depth_seg_dataset`) y los bridges necesarios para capturar:

- RGB
- Depth
- Segmentación (panoptic) en:
  - `seg_colored` (imagen coloreada)
  - `seg_labels` (IDs por píxel)

> El dataset se crea dentro de la carpeta `dataset/` en la **raíz** del proyecto.

---

## 🧱 Estructura del dataset

Estructura por escenario (mundo):

```text
dataset/
├── homeWorld/
├── bookstoreWorld/
├── officeWorld/
└── hospitalWorld/
```

Cada escenario contiene:

```text
<World>/
├── depth/        # PNG con profundidad (metros) en cada píxel
├── rgb/          # PNG RGB
├── seg_colored/  # PNG segmentación coloreada
└── seg_labels/   # PNG labels (ground-truth por píxel)
```

**Notas importantes:**
- `depth`: cada píxel guarda la **profundidad en metros** (codificada en imagen).
- `seg_labels`: cada píxel guarda el **ID de label** (entero).
- `seg_colored`: mismo frame pero coloreado para visualizar objetos/clases.

---

## 🖥️ Visualizador del dataset

Dentro del repo hay un visualizador (OpenCV). Ejemplos:

### house.world → `homeWorld`
```bash
python3 dataset_visualizer.py --path ~/Documentos/rosmaster_project/dataset/homeWorld
```

### bookstore.world → `bookstoreWorld`
```bash
python3 dataset_visualizer.py --path ~/Documentos/rosmaster_project/dataset/bookstoreWorld
```

### service.world → `officeWorld`
```bash
python3 dataset_visualizer.py --path ~/Documentos/rosmaster_project/dataset/officeWorld
```

### hospital.world → `hospitalWorld`
```bash
python3 dataset_visualizer.py --path ~/Documentos/rosmaster_project/dataset/hospitalWorld
```

Controles típicos del visualizador:

- `N`: siguiente frame
- `P`: frame anterior
- `Q` o `ESC`: salir

---

## 🏷️ Clases (labels) y diccionario

En `dataset/` existe el archivo:

```text
dataset/label_names.json
```

Ese JSON sirve como **diccionario** para traducir el ID del píxel (en `seg_labels`) a un nombre legible.

> En el visualizador, al hacer clic sobre `seg_labels`, se imprime en consola el **ID** y el **nombre** usando `label_names.json`.

---

## ➕ Agregar nuevas clases (Label plugin)

En Gazebo, la cámara de segmentación “ve” como clase únicamente a modelos etiquetados.

### Agregar `Label` plugin a un modelo (SDF)

Dentro del `<visual>` (o en `<model>`), agrega:

```xml
<plugin filename="gz-sim-label-system" name="gz::sim::systems::Label">
  <label>ID_DE_TU_CLASE</label>
</plugin>
```

Ejemplo:

```xml
<plugin filename="gz-sim-label-system" name="gz::sim::systems::Label">
  <label>17</label>
</plugin>
```

### Si el modelo viene por `<include>` (Fuel / URL)

```xml
<include>
  <uri>https://fuel.gazebosim.org/1.0/OpenRobotics/models/...</uri>
  <plugin filename="gz-sim-label-system" name="gz::sim::systems::Label">
    <label>ID_DE_TU_CLASE</label>
  </plugin>
</include>
```

Luego reinicia la simulación y vuelve a recorrer el mundo para generar nuevas capturas.

---

## 🛠️ Troubleshooting

### 1) El recorder no guarda / no aparecen datos
Asegúrate de que **las 3 terminales** (simulación / teleop / recorder) tengan el **mismo** `GZ_IP` y `GZ_PARTITION`.

Ejemplo (en cada terminal, antes de ejecutar comandos ROS/GZ):

```bash
export GZ_IP=127.0.0.1
export GZ_PARTITION=rosmaster_dataset
```

> Si tu PC tiene varias interfaces (Ethernet/WiFi), usar `127.0.0.1` suele evitar conflictos.

### 2) Limpieza y rebuild (cuando algo se rompe)
Desde `yahboomcar_ws`:

```bash
conda deactivate 2>/dev/null || true
rm -rf build log install
colcon build
source install/setup.bash
```

### 3) Verificar que todo está corriendo (topics)
Con Gazebo y el recorder activos:

```bash
ros2 node list
ros2 topic list -t | sort
```

---

## 📌 Estructura del proyecto

```text
.
├── dataset
│   ├── bookstoreWorld
│   │   ├── depth
│   │   ├── rgb
│   │   ├── seg_colored
│   │   └── seg_labels
│   ├── homeWorld
│   │   ├── depth
│   │   ├── rgb
│   │   ├── seg_colored
│   │   └── seg_labels
│   ├── hospitalWorld
│   │   ├── depth
│   │   ├── rgb
│   │   ├── seg_colored
│   │   └── seg_labels
│   └── officeWorld
│       ├── depth
│       ├── rgb
│       ├── seg_colored
│       └── seg_labels
├── docs
│   └── images
└── yahboomcar_ws
    └── src
        └── yahboom_rosmaster
            ├── depth_seg_dataset
            ├── mecanum_drive_controller
            ├── rosmaster_x3_teleop
            ├── yahboom_rosmaster
            ├── yahboom_rosmaster_bringup
            ├── yahboom_rosmaster_description
            ├── yahboom_rosmaster_docking
            ├── yahboom_rosmaster_gazebo
            ├── yahboom_rosmaster_localization
            ├── yahboom_rosmaster_msgs
            ├── yahboom_rosmaster_navigation
            └── yahboom_rosmaster_system_tests
```

---

## 🧩 Paquetes ROS relevantes

Dentro del workspace (`yahboomcar_ws/src/yahboom_rosmaster`):

- `yahboom_rosmaster_gazebo`: simulación + mundos (`*.world`) + launch principal
- `yahboom_rosmaster_bringup`: scripts de arranque (incluye `rosmaster_x3_gazebo.sh`)
- `rosmaster_x3_teleop`: teleop por teclado
- `depth_seg_dataset`: recorder + launch `dataset_with_bridge.launch.py`

---

## 📣 Créditos

- Yahboom (ROSMASTER X3)
- Open Source Robotics Foundation (Gazebo / ROS 2)
- Automatic Adisson (Simulacion base del proyecto)