import tkinter as tk
import cv2
import argparse
import os
import re
import numpy as np
import json
import signal
import sys



# ---------------- Utils ----------------
def get_screen_size():
    """Devuelve (screen_w, screen_h) usando tkinter."""
    root = tk.Tk()
    root.withdraw()
    w = root.winfo_screenwidth()
    h = root.winfo_screenheight()
    root.destroy()
    return w, h

def tile_windows_3x2(window_names, margin=6):
    """
    Acomoda 6 ventanas en mosaico: 3 arriba y 3 abajo, cubriendo la pantalla.
    margin = separación (px) para que no se encimen bordes.
    """
    screen_w, screen_h = get_screen_size()
    cols, rows = 3, 2

    cell_w = screen_w // cols
    cell_h = screen_h // rows

    for i, name in enumerate(window_names):
        r = i // cols
        c = i % cols

        x = c * cell_w
        y = r * cell_h

        # tamaño con margen
        w = max(100, cell_w - 2 * margin)
        h = max(100, cell_h - 2 * margin)

        try:
            cv2.resizeWindow(name, w, h)
            cv2.moveWindow(name, x + margin, y + margin)
        except Exception:
            pass

def decode_label_and_instance(labels_map_bgr):
    # labels_map_bgr es uint8 (H,W,3) en BGR
    label = labels_map_bgr[:, :, 0].astype(np.uint16)     # label id
    hi    = labels_map_bgr[:, :, 1].astype(np.uint16)     # instance hi byte
    lo    = labels_map_bgr[:, :, 2].astype(np.uint16)     # instance lo byte
    instance = (hi << 8) + lo
    return label, instance

def make_label_lut(n=256, seed=123):
    # Colores fijos y bien contrastados por label
    rng = np.random.default_rng(seed)
    lut = rng.integers(0, 256, size=(n, 3), dtype=np.uint8)
    lut[0] = (0, 0, 0)  # background negro
    return lut

LABEL_LUT = make_label_lut()

def visualize_labels(label_id_uint16):
    # label_id normalmente cabe en 0..255
    label_u8 = np.clip(label_id_uint16, 0, 255).astype(np.uint8)
    # (H,W) -> (H,W,3) usando LUT
    return LABEL_LUT[label_u8]

# CLAHE para mejorar contraste (instancias)
CLAHE = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

def visualize_instances(instance_id_uint16, clip_percentile=99.5):
    arr = instance_id_uint16.astype(np.float32)

    vmax = np.percentile(arr, clip_percentile)
    if vmax < 1:
        vmax = 1.0

    gray = np.clip(arr, 0, vmax)
    gray = (gray * (255.0 / vmax)).astype(np.uint8)

    # Subir contraste local
    gray = CLAHE.apply(gray)

    return cv2.applyColorMap(gray, cv2.COLORMAP_TURBO)


def load_label_names():
    """
    Carga un diccionario {int_label: "Nombre"} desde un JSON en el mismo directorio del script.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # nombres que intentará encontrar (en orden)
    candidates = [
        "label_names.json",
        "labels.json",
        "label_dict.json",
        "class_map.json",
    ]

    for fname in candidates:
        fpath = os.path.join(script_dir, fname)
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Convierte keys "1" -> 1
            out = {}
            for k, v in data.items():
                try:
                    out[int(k)] = str(v)
                except Exception:
                    pass

            print(f"[OK] Cargué labels desde: {fpath} ({len(out)} clases)")
            return out

    print("[WARN] No encontré label_names.json (u otros). Solo mostraré el número de label.")
    return {}


def add_colored_to_image(image, colored):
    base = cv2.resize(image, (colored.shape[1], colored.shape[0])).astype(np.uint8)
    overlay = colored.astype(np.uint8)
    return cv2.addWeighted(base, 1.0, overlay, 0.5, 0.0)

labels_map_raw = None   # el verdadero (para clicks)
labels_map = None
LABEL_NAMES = load_label_names()

def mouse_callback(event, x, y, flags, param):
    global labels_map_raw, LABEL_NAMES
    if event == cv2.EVENT_LBUTTONDOWN and labels_map_raw is not None:
        label = int(labels_map_raw[y, x, 0])

        hi = int(labels_map_raw[y, x, 1])
        lo = int(labels_map_raw[y, x, 2])
        instance_count = hi * 256 + lo

        name = LABEL_NAMES.get(label, "Unknown")
        print(f"label: {label} ({name}) .. instance count: {instance_count}")


def list_files(folder):
    if not os.path.isdir(folder):
        raise RuntimeError(f"No existe la carpeta: {folder}")
    files = []
    for fn in os.listdir(folder):
        full = os.path.join(folder, fn)
        if os.path.isfile(full):
            files.append(full)
    return sorted(files)

def basename_no_ext(path):
    return os.path.splitext(os.path.basename(path))[0]

def key_basename(path):
    return basename_no_ext(path)

def key_last_number(path):
    """
    Extrae el ÚLTIMO grupo de dígitos del nombre.
    Ej:
      image_000123.png -> "000123"
      labels_map_12.png -> "12"
    """
    b = basename_no_ext(path)
    m = re.search(r'(\d+)(?!.*\d)', b)  # último grupo de números
    return m.group(1) if m else None

def build_dict(paths, key_func):
    d = {}
    for p in paths:
        k = key_func(p)
        if k is None:
            continue
        # Si se repite key, nos quedamos con el primero (o podrías guardar lista)
        if k not in d:
            d[k] = p
    return d

def preview_names(paths, n=5):
    return [os.path.basename(p) for p in paths[:n]]

def make_pairs(images_files, labels_files, colored_files, mode="auto"):
    """
    Devuelve lista de tuplas: [(img_path, label_path, colored_path), ...]
    mode: auto | basename | digits | sorted
    """
    if mode in ("basename", "auto"):
        img_d = build_dict(images_files, key_basename)
        lab_d = build_dict(labels_files, key_basename)
        col_d = build_dict(colored_files, key_basename)

        common = sorted(set(img_d) & set(lab_d) & set(col_d))
        if common:
            pairs = [(img_d[k], lab_d[k], col_d[k]) for k in common]
            return pairs, "basename"

        if mode == "basename":
            return [], "basename"

    if mode in ("digits", "auto"):
        img_d = build_dict(images_files, key_last_number)
        lab_d = build_dict(labels_files, key_last_number)
        col_d = build_dict(colored_files, key_last_number)

        common = sorted(set(img_d) & set(lab_d) & set(col_d), key=lambda x: int(x))
        if common:
            pairs = [(img_d[k], lab_d[k], col_d[k]) for k in common]
            return pairs, "digits"

        if mode == "digits":
            return [], "digits"

    # Fallback por orden (como zip original)
    if mode in ("sorted", "auto"):
        n = min(len(images_files), len(labels_files), len(colored_files))
        pairs = list(zip(images_files[:n], labels_files[:n], colored_files[:n]))
        return pairs, "sorted"

    return [], mode

# ---------------- Main ----------------
parser = argparse.ArgumentParser()
parser.add_argument('--path', type=str, required=True, help='Segmentation Dataset Path')
parser.add_argument('--match', type=str, default='auto',
                    choices=['auto', 'basename', 'digits', 'sorted'],
                    help='Método de emparejamiento entre carpetas')
parser.add_argument('--loop', action='store_true', help='Loop al llegar al final')
args = parser.parse_args()

root = args.path
images_path = os.path.join(root, "images")
labels_map_path = os.path.join(root, "labels_maps")
colored_map_path = os.path.join(root, "colored_maps")

images_files = list_files(images_path)
labels_files = list_files(labels_map_path)
colored_files = list_files(colored_map_path)

print("Ejemplos de nombres (primeros 5):")
print(" images     :", preview_names(images_files))
print(" labels_maps:", preview_names(labels_files))
print(" colored_maps:", preview_names(colored_files))
print()

pairs, used_mode = make_pairs(images_files, labels_files, colored_files, mode=args.match)

if not pairs:
    raise RuntimeError(
        "No pude emparejar archivos entre images/, labels_maps/ y colored_maps/.\n"
        "Prueba con --match digits o --match sorted.\n"
        "También revisa que las tres carpetas tengan el mismo número de frames."
    )

if used_mode == "sorted":
    print("[WARN] No hubo match por nombre/índice numérico. Estoy emparejando SOLO por orden alfabético.")
elif used_mode == "digits":
    print("[OK] Emparejando por el ÚLTIMO número en el nombre del archivo (modo digits).")
else:
    print("[OK] Emparejando por nombre base exacto (modo basename).")

print(f"Total pares encontrados: {len(pairs)}\n")

# Ventanas
cv2.namedWindow('image', cv2.WINDOW_NORMAL)
cv2.namedWindow('labels_map', cv2.WINDOW_NORMAL)
cv2.namedWindow('colored_map', cv2.WINDOW_NORMAL)
cv2.namedWindow('segmentation', cv2.WINDOW_NORMAL)
cv2.namedWindow('labels_vis', cv2.WINDOW_NORMAL)
cv2.namedWindow('instance_vis', cv2.WINDOW_NORMAL)

# Orden sugerido:
# Arriba: image | segmentation | colored_map
# Abajo: labels_map | labels_vis | instance_vis
WINDOW_ORDER = ["image", "segmentation", "colored_map",
                "labels_map", "labels_vis", "instance_vis"]

tile_windows_3x2(WINDOW_ORDER, margin=6)


cv2.setMouseCallback('labels_map', mouse_callback)

global tiled_once
tiled_once = False

idx = 0
total = len(pairs)

print("Controles:")
print("  N: siguiente | P: anterior | Q/ESC: salir")
print("  Click en labels_map para ver (label, instance_count)\n")

def cleanup_and_exit(signum=None, frame=None):
    print("\n[INFO] Ctrl+C detectado. Cerrando ventanas...")
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    sys.exit(0)

# Captura Ctrl+C
signal.signal(signal.SIGINT, cleanup_and_exit)



try:
    while True:
        img_path, lab_path, col_path = pairs[idx]
        
        image = cv2.imread(img_path, cv2.IMREAD_COLOR)
        labels_map_raw = cv2.imread(lab_path, cv2.IMREAD_COLOR)
        colored_map = cv2.imread(col_path, cv2.IMREAD_COLOR)

        """
        image = cv2.imread(img_path, cv2.IMREAD_COLOR)
        labels_map = cv2.imread(lab_path, cv2.IMREAD_COLOR)
        colored_map = cv2.imread(col_path, cv2.IMREAD_COLOR)
        """

        if image is None or labels_map_raw is None or colored_map is None:
            print(f"[WARN] No pude leer alguno de estos:\n  {img_path}\n  {lab_path}\n  {col_path}")
        else:
            
            colored_image = add_colored_to_image(image, colored_map)
            label_id, instance_id = decode_label_and_instance(labels_map_raw)

            labels_vis = visualize_labels(label_id)
            inst_vis   = visualize_instances(instance_id)

            # Alto contraste: blanco = segmentado (label>0), negro = fondo (label==0)
            label_id = labels_map_raw[:, :, 0]  # canal del label
            mask = (label_id == 0).astype(np.uint8) * 255

            cv2.imshow("labels_map", mask)  # se ve clarísimo
            cv2.imshow("labels_vis", labels_vis)
            cv2.imshow("instance_vis", inst_vis)
            cv2.imshow("segmentation", colored_image)
            cv2.imshow("image", image)
            cv2.imshow("colored_map", colored_map)

            print(f"[{idx+1}/{total}]")
            print(" image     :", os.path.basename(img_path))
            print(" labels_map:", os.path.basename(lab_path))
            print(" colored   :", os.path.basename(col_path))

            if not tiled_once:
                tile_windows_3x2(WINDOW_ORDER, margin=6)
                tiled_once = True

        k = cv2.waitKey(0) & 0xFF

        if k in (27, ord('q'), ord('Q')):
            break
        elif k in (ord('n'), ord('N')):
            idx += 1
            if idx >= total:
                idx = 0 if args.loop else total - 1
        elif k in (ord('p'), ord('P')):
            idx -= 1
            if idx < 0:
                idx = total - 1 if args.loop else 0
finally:
    cv2.destroyAllWindows()

cv2.destroyAllWindows()
