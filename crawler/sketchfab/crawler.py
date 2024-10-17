import os
import time
import json
import shutil
import zipfile

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
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
    while True:
        files = os.listdir(download_dir)
        if any(file.endswith(".crdownload") for file in files):
            print("下载进行中...")
            time.sleep(1)
        else:
            print("下载完成！")
            break

if __name__ == "__main__":
    # 下载路径
    download_dir = "E:/3Dmodels"   # 替换为本地Edge默认下载路径
    os.makedirs(download_dir, exist_ok=True)
    # final_dir = "crawler/sketchfab/data"
    # os.makedirs(final_dir, exist_ok=True)

    # 选择urls.txt文件中的每个url作为page的值
    with open("C:/Users/Administrator/Desktop/py/3D/Machine-Learning-Project/crawler/sketchfab/urls.txt", "r") as f:
        urls = f.readlines()

    # 获得一个 Edge driver
    edge_options = Options()
    edge_options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,  # 禁止下载弹窗
        "download.directory_upgrade": True,     # 在下载时升级目录
        "safebrowsing.enabled": True            # 禁用安全浏览保护，以避免干扰下载
    })
    # 设置用户代理
    caps = DesiredCapabilities().EDGE
    caps["pageLoadStrategy"] = "normal"
    caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    service = Service("D:\edgedriver_win64\msedgedriver.exe")
    driver = webdriver.Edge(service=service, options=edge_options)
    # driver.maximize_window()

    # 打开第一个 URL 并登录
    first_page = urls[0].strip()
    driver.get(first_page)
    button = driver.find_element(By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')
    driver.execute_script("arguments[0].click();", button)
    time.sleep(1)

    # 点击 Download 3D Model 按钮
    button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
    driver.execute_script("arguments[0].click();", button)
    time.sleep(1)

    # 尝试登录
    try:
        name_input = driver.find_element(By.CSS_SELECTOR, 'input[type="email"]')
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')

        name_input.send_keys(EMAIL)
        password_input.send_keys(PASSWORD)

        button = driver.find_element(By.CSS_SELECTOR, 'button[data-selenium="submit-button"]')
        driver.execute_script("arguments[0].click();", button)
        time.sleep(2)
    except Exception as e:
        print(f"Error during login: {e}")

    # 下载第一个 URL 的模型
    try:
        # 向下滚动400像素
        driver.execute_script("window.scrollBy(0,400)")
        time.sleep(1)
        button = driver.find_element(By.XPATH, '//*[@id="root"]/main/section/div/div[1]/div/div[2]/div/div[1]/div[3]/div/button[1]/span[2]')
        driver.execute_script("arguments[0].click();", button)
        time.sleep(1)
    except Exception as e:
        print(f"Error while downloading the first model: {e}")

    is_download_complete(download_dir)

    # 下载后续 URL 的模型
    for url in urls[1:]:
        page = url.strip()
        print(f"Downloading {page}...")

        # 访问目标网站
        driver.get(page)
        time.sleep(1)

        # 点击 Download 3D Model 按钮
        try:
            button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
            driver.execute_script("arguments[0].click();", button)
            time.sleep(1)

            # 向下滚动400像素
            driver.execute_script("window.scrollBy(0,400)")
            time.sleep(1)
            button = driver.find_element(By.XPATH, '//*[@id="root"]/main/section/div/div[1]/div/div[2]/div/div[1]/div[3]/div/button[1]/span[2]')
            driver.execute_script("arguments[0].click();", button)
            time.sleep(1)
        except Exception as e:
            print(f"Error while downloading the model: {e}")

        is_download_complete(download_dir)

    # 关闭 driver
    driver.quit()

    # # 将文件移动至本目录
    # files = os.listdir(download_dir)
    # for file in files:
    #     if file.endswith(".zip"):
    #         shutil.move(os.path.join(download_dir, file), os.path.join(final_dir, file))

    # # 将文件解压到同名文件夹
    # for file in os.listdir(final_dir):
    #     if file.endswith(".zip"):
    #         unzip_to_same_named_folder(os.path.join(final_dir, file))