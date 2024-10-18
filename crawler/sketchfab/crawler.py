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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import warnings
import re
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

def is_download_complete(download_dir, initial_glb_count):
    # 查看下载目录中 .glb 文件的个数是否增加
    while True:
        current_glb_count = len([file for file in os.listdir(download_dir) if file.endswith(".glb")])
        if current_glb_count > initial_glb_count:
            print("下载完成")
            break
        else:
            print("下载进行中...")
            time.sleep(1)
    return current_glb_count

def load_downloaded_urls(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return set(file.read().splitlines())
    return set()

def save_downloaded_url(file_path, url):
    with open(file_path, 'a') as file:
        file.write(url + '\n')

if __name__ == "__main__":
    # 自己设置1-13
    num=1
    # 下载路径
    download_dir = "C:/Users/Administrator/Downloads"   # 替换为本地Edge默认下载路径
    os.makedirs(download_dir, exist_ok=True)
    downloaded_urls_file = "C:/Users/Administrator/Desktop/py/3D/Machine-Learning-Project/crawler/sketchfab/downloaded_urls_"+str(num)+".txt"

    # 选择对应num的URL文件
    with open("C:/Users/Administrator/Desktop/py/3D/Machine-Learning-Project/crawler/sketchfab/urls_part_"+str(num)+".txt", 'r') as f:
        urls = f.readlines()

    # 加载已下载的URL
    downloaded_urls = load_downloaded_urls(downloaded_urls_file)

    # 获得一个 Edge driver
    edge_options = Options()
    # edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")

    # 设置用户代理
    caps = DesiredCapabilities().EDGE
    caps["pageLoadStrategy"] = "normal"
    caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    service = Service("D:/edgedriver_win64/msedgedriver.exe")
    driver = webdriver.Edge(service=service, options=edge_options)

    # 打开第一个 URL 并登录
    first_page = urls[0].strip()
    driver.get(first_page)
    button = driver.find_element(By.XPATH, '//*[@id="onetrust-accept-btn-handler"]')
    driver.execute_script("arguments[0].click();", button)
    time.sleep(1)

    try:
        button = driver.find_element(By.XPATH, '//*[@id="root"]/header/div/div/a[1]/span')
        driver.execute_script("arguments[0].click();", button)
        time.sleep(0.5)
        name_input = driver.find_element(By.CSS_SELECTOR, 'input[type="email"]')
        password_input = driver.find_element(By.CSS_SELECTOR, 'input[type="password"]')

        name_input.send_keys(EMAIL)
        time.sleep(1)
        password_input.send_keys(PASSWORD)

        button = driver.find_element(By.CSS_SELECTOR, 'button[data-selenium="submit-button"]')
        while True:
            driver.execute_script("arguments[0].click();", button)
            time.sleep(2)

            # 检查是否登录成功
            cookies = driver.get_cookies()
            if len(cookies) == 5:
                print("Login successful")
                break
    except Exception as e:
        print(f"Error during login: {e}")

    driver.refresh()
    time.sleep(1)

    # 记录初始的 .glb 文件个数
    initial_glb_count = len([file for file in os.listdir(download_dir) if file.endswith(".glb")])

    # 下载第一个 URL 的模型
    if first_page not in downloaded_urls:
        try:
            # 向下滚动400像素
            driver.execute_script("window.scrollBy(0,400)")
            time.sleep(1)
            button = driver.find_element(By.XPATH, '//*[@id="root"]/main/section/div/div[1]/div/div[2]/div/div[1]/div[3]/div/button[1]/span[2]')
            driver.execute_script("arguments[0].click();", button)
            time.sleep(1)
            # 等待弹窗出现
            wait = WebDriverWait(driver, 10)
            popup = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'c-popup__content')))
                    
            # 点击弹窗内部的空白区域
            driver.execute_script("arguments[0].click();", popup)
                    
            # 滚动弹窗以加载出下载按钮
            driver.execute_script("arguments[0].scrollBy(0, 400);", popup)
            buttons = driver.find_elements(By.CLASS_NAME, 'button.btn-primary.btn-small.button-extra')
            EC.element_to_be_clickable(buttons[3])
            buttons[3].click()
            time.sleep(5)
        except Exception as e:
            print(f"Error while downloading the first model: {e}")

        initial_glb_count=is_download_complete(download_dir, initial_glb_count)
        save_downloaded_url(downloaded_urls_file, first_page)
    else:
        print(f"URL {first_page} 已下载过，跳过")

    # 下载后续 URL 的模型
    for url in urls[1:]:
        page = url.strip()

        if page not in downloaded_urls:
            # 访问目标网站
            driver.get(page)
            time.sleep(1)

            # 点击 Download 3D Model 按钮
            try:
                # 向下滚动400像素
                driver.execute_script("window.scrollBy(0,400)")
                time.sleep(1)
                button = driver.find_element(By.XPATH, '//*[@id="root"]/main/section/div/div[1]/div/div[2]/div/div[1]/div[3]/div/button[1]/span[2]')
                driver.execute_script("arguments[0].click();", button)
                time.sleep(1)
                # 等待弹窗出现
                wait = WebDriverWait(driver, 10)
                popup = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'c-popup__content')))
                        
                # 点击弹窗内部的空白区域
                driver.execute_script("arguments[0].click();", popup)
                        
                # 滚动弹窗以加载出下载按钮
                driver.execute_script("arguments[0].scrollBy(0, 400);", popup)
                buttons = driver.find_elements(By.CLASS_NAME, 'button.btn-primary.btn-small.button-extra')
                EC.element_to_be_clickable(buttons[3])
                buttons[3].click()
                time.sleep(5)
            except Exception as e:
                print(f"Error while downloading the model from {url}: {e}")

            initial_glb_count=is_download_complete(download_dir, initial_glb_count)
            save_downloaded_url(downloaded_urls_file, page)
        else:
            print(f"URL {page} 已下载过，跳过")

    # 关闭 driver
    driver.quit()

    