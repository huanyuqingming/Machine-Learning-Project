import os
import time
import json
import shutil
import zipfile
import argparse
from tqdm import tqdm

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import warnings
warnings.filterwarnings("ignore")

from my_account import EMAIL, PASSWORD

def unzip_to_same_named_folder(zip_path):
    # 获取ZIP文件的名称（不包括扩展名）
    zip_name = os.path.basename(zip_path)
    zip_folder_name = os.path.splitext(zip_name)[0]
    
    # 构建目标文件夹路径
    dest_folder_path = os.path.join(os.path.dirname(zip_path), zip_folder_name)
    
    # 确保目标文件夹存在
    if not os.path.exists(dest_folder_path):
        os.makedirs(dest_folder_path)
    
    # 打开ZIP文件
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # 解压到目标文件夹
        zip_ref.extractall(dest_folder_path)

def is_download_complete(download_dir):
    # 轮询下载目录，直到没有.crdownload文件
    with tqdm(desc="Downloading", bar_format="{desc}: {elapsed}") as pbar:
        while True:
            files = os.listdir(download_dir)
            if any(file.endswith(".crdownload") for file in files):
                time.sleep(1)
            else:
                break
            pbar.update(1)
    print("Download complete.")

def login(driver):
    # 尝试登录
    try:
        name_input = driver.find_element(By.CSS_SELECTOR, 'input[type="email"]')
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')

        name_input.send_keys(EMAIL)
        password_input.send_keys(PASSWORD)

        button = driver.find_element(By.CSS_SELECTOR, 'button[data-selenium="submit-button"]')
        driver.execute_script("arguments[0].click();", button)

        time.sleep(10)

    except:
        pass

def download(driver, download_dir):
    # 点击下载按钮
    try:
        button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
        driver.execute_script("arguments[0].click();", button)

        time.sleep(5)
    except:
        pass
    # 点击目标目标
    div = driver.find_element(By.CSS_SELECTOR, 'div[class="c-download__links"]')
    buttons = div.find_elements(By.CSS_SELECTOR, 'button')
    driver.execute_script("arguments[0].click();", buttons[3])

    time.sleep(5)

    is_download_complete(download_dir)

def main(args):
    # 下载路径
    download_dir = args.download_dir
    os.makedirs(download_dir, exist_ok=True)
    # final_dir = "crawler/sketchfab/data"
    # os.makedirs(final_dir, exist_ok=True)

    # 选择urls.txt文件中的每个url作为page的值
    with open(args.urls_file, "r") as f:
        urls = f.readlines()

    # 选择downloaded_urls.txt文件中的每个url作为downloaded_urls的值
    os.makedirs(os.path.dirname(args.downloaded_urls_file), exist_ok=True)
    with open(args.downloaded_urls_file, "r") as f:
        downloaded_urls = f.readlines()

    # 获得一个 Chrome driver
    chrome_options = Options()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,  # 禁止下载弹窗
        "download.directory_upgrade": True,     # 在下载时升级目录
        "safebrowsing.enabled": True            # 禁用安全浏览保护，以避免干扰下载
    })
    # 设置用户代理
    caps = DesiredCapabilities().CHROME
    caps["pageLoadStrategy"] = "normal"
    caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    service = Service(args.chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    # driver.maximize_window()

    # 打开第一个 URL并下载
    # 访问目标网站
    for url in urls:
        if url in downloaded_urls:
            print(f"URL {url} has been downloaded.")
            continue
        else:
            page = url
            break

    print(f"Downloading {page}...")
    driver.get(page)

    time.sleep(1)

    # 点击 Download 3D Model 按钮
    button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
    driver.execute_script("arguments[0].click();", button)

    time.sleep(1)

    login(driver)

    download(driver, download_dir)

    # 保存已下载的 URL
    with open(args.downloaded_urls_file, 'a') as f:
        f.write(page)
    with open(args.downloaded_urls_file, "r") as f:
        downloaded_urls = f.readlines()

    # 下载后续 URL 的模型
    for url in urls:
        if url in downloaded_urls:
            print(f"URL {url} has been downloaded.")
            continue
        else:
            page = url
        print(f"Downloading {page}...")

        # 访问目标网站
        driver.get(page)
        time.sleep(1)

        # 点击 Download 3D Model 按钮
        button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
        driver.execute_script("arguments[0].click();", button)

        download(driver, download_dir)

        # 保存已下载的 URL
        with open(args.downloaded_urls_file, 'a') as f:
            f.write(page)
        with open(args.downloaded_urls_file, "r") as f:
            downloaded_urls = f.readlines()

    # 关闭 driver
    driver.quit()

    # 解压所有下载的ZIP文件
    zip_files = [file for file in os.listdir(download_dir) if file.endswith(".zip")]
    for zip_file in zip_files:
        zip_path = os.path.join(download_dir, zip_file)
        unzip_to_same_named_folder(zip_path)

# 在这里改参数
def get_args(parser: argparse.ArgumentParser):
    parser.add_argument('--download_dir', type=str, default=r"D:\Machine Learning Project\crawler\sketchfab\data", help="下载路径")
    parser.add_argument('--urls_file', type=str, default=r"crawler\sketchfab\urls.txt", help="URLs文件路径")
    parser.add_argument('--downloaded_urls_file', type=str, default=r"crawler\sketchfab\downloaded_urls.txt", help="已下载URLs文件路径")
    parser.add_argument('--chrome_driver_path', type=str, default=r"C:\Program Files\Google\Chrome\Application\chromedriver.exe", help="Chrome driver路径")
    return parser.parse_args()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = get_args(parser)
    main(args)