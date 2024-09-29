import os
import time
import json

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import warnings
warnings.filterwarnings("ignore")

from my_account import EMAIL, PASSWORD

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

    # 选择urls.txt文件中的每个url作为page的值
    with open("crawler/sketchfab/urls.txt", "r", encoding="utf-8") as f:
        urls = f.readlines()

    for url in urls:
        page = url.strip()
        print(f"Downloading {page}...")

        # 下载路径
        download_dir = r"C:\Users\HYQM\Downloads"
        os.makedirs(download_dir, exist_ok=True)

        # 获得一个 chrome driver
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,  # 禁止下载弹窗
            "download.directory_upgrade": True,     # 在下载时升级目录
            "safebrowsing.enabled": True            # 禁用安全浏览保护，以避免干扰下载
        })
        driver = webdriver.Chrome(options=chrome_options)
        driver.maximize_window()

        # 访问目标网站
        driver.get(page)

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

            time.sleep(10)

            button = driver.find_element(By.CSS_SELECTOR, 'button[title="Download Free 3D Model"]')
            driver.execute_script("arguments[0].click();", button)

            time.sleep(1)
        except:
            pass

        # 点击目标目标
        div = driver.find_element(By.CSS_SELECTOR, 'div[class="c-download__links"]')
        buttons = div.find_elements(By.CSS_SELECTOR, 'button')
        driver.execute_script("arguments[0].click();", buttons[0])

        time.sleep(5)

        is_download_complete(download_dir)

        # 关闭 driver
        driver.close()
