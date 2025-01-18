# Batch render all meshes in the folder DATA_DIR: ["examples/objaverse/", "examples/ours/"]
import os
import subprocess
import argparse

# Create an argument parser to accept the DATA_DIR as a command-line argument
parser = argparse.ArgumentParser()
parser.add_argument('--DATA_DIR', type=str, default='dataset1', help='Path to the folder containing meshes to render')
args = parser.parse_args()

# The directory containing the extracted Blender
NUM = args.DATA_DIR[-1]
BLD_DIR = "/opt/blender-3.6.5-linux-x64/"
DATA_DIR = args.DATA_DIR + "/model"
OUT_DIR = "output/"
SCRIPT = "single_render_eval.py"
RESOLUTION = "512"

models = [d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))]

for model in models:
    print(model)
    with open(f'rendered{NUM}.txt') as file:
        content = file.read()
        rendered = content.splitlines()

    if model in rendered:
        continue
    
    # Command to run
    blenderproc_command = [
        "blenderproc",
        "run",
        "--custom-blender-path="+BLD_DIR,
        "--blender-install-path="+BLD_DIR,
        SCRIPT,
        "--object_path",
        "",
        "--output_dir",
        OUT_DIR,
        "--engine",
        "CYCLES",
        "--camera_dist",
        "1.3",
        "--resolution",
        RESOLUTION
    ]

    model_dir = os.path.join(DATA_DIR, model)

    for shape in os.listdir(model_dir):
        if not shape.endswith('.glb'):
            continue
        print(f"Rendering {shape} ...")
        object_path = f"{model_dir}/{shape}"
        render_path = os.path.join(OUT_DIR, shape[:-4])
        blenderproc_command[6] = object_path
        blenderproc_command[8] = render_path
        subprocess.run(blenderproc_command)


    with open(f'rendered{NUM}.txt', 'a') as f:
        f.write(f"{model}\n")
