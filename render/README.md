# Rendering scripts

## Installation

```bash
# Download Blender for Linux
wget https://mirrors.ocf.berkeley.edu/blender/release/Blender3.6/blender-3.6.5-linux-x64.tar.xz
# Extract the downloaded Blender archive to /opt/
tar -xvf blender-3.6.5-linux-x64.tar.xz -C /opt/
# Install BlenderProc
pip install blenderproc==2.6.1
# Install required dependencies
apt update && apt install -y libsm6 libglfw3-dev
```

## Render

```bash
python render_all.py --DATA_DIR ./dataset1
```
