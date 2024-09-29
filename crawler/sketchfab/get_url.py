from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import os
import time
import random
import argparse

def monitorMouseClicks(driver):
    # 设置鼠标点击监听器
    driver.execute_script("""
        document.addEventListener('click', function(event) {
            window.clickX = event.clientX;
            window.clickY = event.clientY;
        });
    """)

    # 无限循环监测鼠标点击位置
    try:
        while True:
            time.sleep(1)  # 每秒检查一次
            click_x = driver.execute_script("return window.clickX")
            click_y = driver.execute_script("return window.clickY")
            if click_x is not None and click_y is not None:
                print(f"Mouse clicked at position: x={click_x}, y={click_y}")
                # 重置点击位置
                driver.execute_script("window.clickX = null; window.clickY = null;")
    except KeyboardInterrupt:
        print("Stopped monitoring mouse clicks.")

def selectAcceptAll(driver):
    # 选择Accept All，但不选择Accept All Cookies
    try:
        # 使用显式等待查找包含 "Accept All" 但不包含 "Cookies" 文本的元素
        accept_all_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Accept All') and not(contains(text(), 'Cookies'))]"))
        )
        # 点击元素
        accept_all_element.click()
        print("Clicked Accept All element")
    except Exception as e:
        print(f"Error while clicking Accept All element: {e}")

def clickBlankPosition(driver):
    # 查找空白位置并点击
    try:
        # 使用 JavaScript 查找空白位置
        blank_position = driver.execute_script("""
            var body = document.body;
            var html = document.documentElement;
            var height = Math.max(body.scrollHeight, body.offsetHeight, html.clientHeight, html.scrollHeight, html.offsetHeight);
            var width = Math.max(body.scrollWidth, body.offsetWidth, html.clientWidth, html.scrollWidth, html.offsetWidth);
            return {x: width / 2, y: height / 2};
        """)
        # 使用 ActionChains 点击空白位置
        actions = ActionChains(driver)
        actions.move_by_offset(blank_position['x'], blank_position['y']).click().perform()
    except Exception as e:
        print(f"Error while clicking blank position: {e}")

def pressDownKey(driver, args):
    # 自动持续点击向下键
    try:
        clickBlankPosition(driver)
        actions = ActionChains(driver)
        start_time = time.time()
        while True:
            actions.send_keys(Keys.ARROW_DOWN).perform()
            time.sleep(0.01)  # 控制点击频率
            if time.time() - start_time > args.finish_time:
                break
    except KeyboardInterrupt:
        print("Stopped pressing down key.")

def findModels(driver, datalist):
    # 查找所有模型链接
    try:
        models = driver.find_elements(By.CSS_SELECTOR, 'a[href^="https://sketchfab.com/3d-models/"][href$="#download"]')
        for model in models:
            model_url = model.get_attribute('href')
            if model_url:
                model_url = model_url.split("#")[0]  # 去除 #download 部分
                # print(f"Found model URL: {model_url}")
                datalist.append(model_url)
        print(f"Found {len(models)} models")
        return datalist
        
    except Exception as e:
        print(f"Error while fetching models: {e}")


def getData(args):
    datalist = []  # 用来存储爬取的网页信息

    # 设置 Chrome 选项
    chrome_options = Options()
    if args.headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # 设置 ChromeDriver 路径
    service = Service(args.chromedriver)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(args.baseurl)
    time.sleep(random.uniform(1, 3))  # 随机等待，确保页面加载完成

    # 选择 Accept All
    selectAcceptAll(driver)

    # 持续按下键
    pressDownKey(driver, args)

    # 查找所有模型链接
    datalist = findModels(driver, datalist)

    driver.quit()
    return datalist

def main(args):
    datalist = getData(args)
    # 将所有爬取的网页信息写入文件urls.txt
    with open("crawler/sketchfab/urls.txt", "w") as f:
        for data in datalist:
            f.write(data + "\n")

def get_args(parser: argparse.ArgumentParser):
    # 要爬取的网页链接
    parser.add_argument("--baseurl", default="https://sketchfab.com/3d-models/categories/architecture?features=downloadable&sort_by=-likeCount", type=str, help="The URL to crawl")
    # 设置 ChromeDriver 路径
    parser.add_argument("--chromedriver", default="C:/Program Files/Google/Chrome/Application/chromedriver.exe", type=str, help="The path to ChromeDriver")
    # 是否使用无头模式，即不打开浏览器界面
    parser.add_argument("--headless", default=False, type=bool, help="Whether to use headless mode")
    # 持续按下键的时间
    parser.add_argument("--finish_time", default=1, type=int, help="The time to press down key")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = get_args(parser)
    main(args)