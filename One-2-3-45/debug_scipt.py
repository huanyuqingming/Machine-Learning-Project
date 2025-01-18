import os
from pathlib import Path
import numpy as np
import json
from tqdm import tqdm
import cv2

with open("/opt/app/One-2-3-45/data/Our_data/lvis_split_cc_by.json") as f:
    data = json.load(f)

for mod in tqdm(data["val"]):
    depth_filename = os.path.join(os.path.join("/opt/app/One-2-3-45/data/Our_data/", 'zero12345_narrow', mod["folder_id"], mod["uid"], f'view_0_depth_mm.png'))
    depth_h = cv2.imread(depth_filename, cv2.IMREAD_UNCHANGED)
    if depth_h is None:
        print("No file: ", mod["uid"])
        continue
    depth_h = depth_h.astype(np.uint16) / 1000.0
    depth_h = cv2.resize(depth_h, (256, 256))

    depth_h = 0.299 * depth_h[:, :, 0] + 0.587 * depth_h[:, :, 1] + 0.114 * depth_h[:, :, 2]
    if depth_h.sum() == 0:
        print("Empty: ", mod["uid"])
        continue