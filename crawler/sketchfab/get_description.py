import os
import time
import json
import shutil
import zipfile
import argparse
from tqdm import tqdm
from transformers import MarianMTModel, MarianTokenizer

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import warnings
warnings.filterwarnings("ignore")

from my_account import EMAIL, PASSWORD

def translate_to_chinese_offline(text):
    model_name = 'Helsinki-NLP/opus-mt-en-zh'
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    
    translated = model.generate(**tokenizer(text, return_tensors="pt", padding=True))
    translation = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]
    return translation[0]

def copy_text_from_page(driver, url, css_selector):
    # 打开网页
    driver.get(url)
    
    # 等待页面加载完成
    time.sleep(2)
    
    try:
        # 查找特定元素并获取其文本内容
        element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )
        text = element.text
        return text
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_files_in_creation_order(directory):
    # 获取所有文件夹
    directorys = [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]
    files = []
    for d in directorys:
        # 获取文件夹中的所有文件名
        files_in_d = os.listdir(os.path.join(directory, d))
        for file in files_in_d:
            files.append(os.path.join(d, file))
    
    # 获取每个文件的创建时间，并按修改日期排序
    files = sorted(files, key=lambda x: os.path.getctime(os.path.join(directory, x)))
    
    return files

def move_glb_files_to_folders(data_dir):
    # 获取 data 目录中的所有文件名
    files = os.listdir(data_dir)
    
    cnt = 0
    for file in files:
        if file.endswith('.glb'):
            cnt += 1
            # 获取文件名（不包括扩展名）
            file_name = os.path.splitext(file)[0]
            
            # 创建同名文件夹
            new_folder_path = os.path.join(data_dir, file_name)
            os.makedirs(new_folder_path, exist_ok=True)
            
            # 移动 .glb 文件到新创建的同名文件夹中
            old_file_path = os.path.join(data_dir, file)
            new_file_path = os.path.join(new_folder_path, file)
            shutil.move(old_file_path, new_file_path)
    
    print(f"共移动 {cnt} 个 .glb 文件到同名文件夹中。")

def main(args):
    # 将所有.glb文件移动到同名文件夹中
    move_glb_files_to_folders(args.download_dir)

    files = get_files_in_creation_order(args.download_dir)

    # 将files写入ordered_files.txt
    os.makedirs(os.path.dirname(r"crawler\sketchfab\ordered_files.txt"), exist_ok=True)
    with open(r"crawler\sketchfab\ordered_files.txt", "w") as f:
        for file in files:
            # 只取file字符串中"\\"前的部分
            file = file.split("\\")[0]
            f.write(file + "\n")

    # 选择downloaded_urls.txt文件中的每个url作为downloaded_urls的值
    os.makedirs(os.path.dirname(args.downloaded_urls_file), exist_ok=True)
    with open(args.downloaded_urls_file, "r") as f:
        downloaded_urls = f.readlines()

    # 导入ordered_files.txt文件中的所有文件名
    with open(r"crawler\sketchfab\ordered_files.txt", "r") as f:
        files = f.readlines()

    # 设置 Chrome 选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 如果你不想打开浏览器窗口，可以使用无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--enable-unsafe-swiftshader")
    
    # # 设置用户代理
    # caps = DesiredCapabilities().CHROME
    # caps["pageLoadStrategy"] = "normal"
    # caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    # 设置用户代理
    caps = webdriver.DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"
    caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    service = Service(args.chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # driver.maximize_window()

    css_selector = "div.C_9eTPtA.markdown-rendered-content"

    # 爬取url中的描述
    for i, url in enumerate(downloaded_urls):
        print(f"{i+1}/{len(downloaded_urls)}：正在爬取{url}中的描述")
        english_text = copy_text_from_page(driver, url, css_selector)
        path = 'crawler/sketchfab/data/' + files[i].strip() + '/description.txt'
        # 如果没有文件，则创建
        print(f"英文描述：{english_text}")
        chinese_text = translate_to_chinese_offline(english_text)
        print(f"中文描述：{chinese_text}")
 
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(url)
            f.write('\n')
            f.write(english_text)
            f.write('\n\n')
            f.write(chinese_text)
        

    # 关闭 driver
    driver.quit()

# 在这里改参数
def get_args(parser: argparse.ArgumentParser):

    parser.add_argument('--download_dir', type=str, default=r"D:\Machine Learning Project\crawler\sketchfab\data", help="下载路径")
    parser.add_argument('--urls_file', type=str, default=r"crawler\sketchfab\filtered_urls_part_5.txt", help="URLs文件路径")
    parser.add_argument('--downloaded_urls_file', type=str, default=r"crawler\sketchfab\downloaded_urls.txt", help="已下载URLs文件路径")
    parser.add_argument('--chrome_driver_path', type=str, default=r"C:\Program Files\Google\Chrome\Application\chromedriver.exe", help="Chrome driver路径")
    return parser.parse_args()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = get_args(parser)
    main(args)