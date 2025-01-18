import os
import json
from pathlib import Path

folder_path = Path("./data/Our_data/output")

file_names = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

lvis_split_cc_by = {"train":[], "val": []}

train_file_names = file_names[:-500]
val_file_names = file_names[-500:]

for name in train_file_names:
    lvis_split_cc_by["train"].append(
        {"folder_id": "output", "uid": name}
    )

for name in val_file_names:
    lvis_split_cc_by["val"].append(
       {"folder_id": "output", "uid": name}
    )

with open('our.json', 'w') as json_file:
    json.dump(lvis_split_cc_by, json_file, indent=4)