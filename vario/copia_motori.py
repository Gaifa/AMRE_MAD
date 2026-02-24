import os
import shutil
from collections import defaultdict

# Percorso di lavoro (radice del progetto = parent of this file's parent)
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(_THIS_DIR)
dest_dir = os.path.join(root_dir, "motors")

# Raccogli tutti i file .mot
mot_files = []
for dirpath, _, filenames in os.walk(root_dir):
    if dirpath == dest_dir:
        continue  # Salta la cartella di destinazione
    for file in filenames:
        if file.lower().endswith(".mot"):
            mot_files.append(os.path.join(dirpath, file))

# Gestione duplicati
name_count = defaultdict(int)
for src_path in mot_files:
    base_name = os.path.basename(src_path)
    name, ext = os.path.splitext(base_name)
    count = name_count[base_name]
    if count == 0:
        dest_name = base_name
    else:
        dest_name = f"{name}_{count}{ext}"
    name_count[base_name] += 1
    dest_path = os.path.join(dest_dir, dest_name)
    shutil.copy2(src_path, dest_path)

print(f"Copiati {len(mot_files)} file nella cartella motors.")
