import os
import zipfile
import shutil

# 输入文件和文件夹路径
txt_file = 'name.txt'
search_dir = '/data/youjunqi/One-2-3-45/data/Our_data/zero12345_narrow/output'
output_zip = './gt.zip'

# 创建一个临时文件夹
temp_dir = os.path.join(search_dir, 'temp')
if not os.path.exists(temp_dir):
    os.makedirs(temp_dir)

# 读取 txt 文件中的每一行并查找对应的文件夹
with open(txt_file, 'r') as f:
    folder_names = f.readlines()

# 查找文件夹并复制到临时文件夹
for folder_name in folder_names:
    folder_name = folder_name.strip()  # 去掉换行符
    folder_path = os.path.join(search_dir, folder_name)
    if os.path.isdir(folder_path):
        shutil.copytree(folder_path, os.path.join(temp_dir, folder_name))
    else:
        print(f"Folder '{folder_name}' not found in {search_dir}")

# 打包文件夹为 zip 文件
with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), temp_dir))

# 删除临时文件夹
shutil.rmtree(temp_dir)

print(f"Zip file created at {output_zip}")