from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import os
import time
import random
import argparse
from my_account import EMAIL, PASSWORD

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

def findModels(driver, datalist):
    # 查找所有模型链接
    try:
        models = driver.find_elements(By.CSS_SELECTOR, 'a[href^="https://sketchfab.com/3d-models/"][href$="#download"]')
        new_urls = []
        for model in models:
            model_url = model.get_attribute('href')
            if model_url:
                model_url = model_url.split("#")[0]  # 去除 #download 部分
                if model_url not in datalist:  # 避免重复添加
                    datalist.append(model_url)
                    new_urls.append(model_url)
        return new_urls
        
    except Exception as e:
        print(f"Error while fetching models: {e}")
        return []

def getData(args):
    datalist = []
    # 设置 Edge 选项
    edge_options = Options()
    if args.headless:
        edge_options.add_argument("--headless")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    
    # 设置用户代理
    caps = DesiredCapabilities().EDGE
    caps["pageLoadStrategy"] = "normal"
    caps["phantomjs.page.settings.userAgent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"

    # 设置 EdgeDriver 路径
    service = Service(args.edgedriver)
    driver = webdriver.Edge(service=service, options=edge_options)

    # 打开网页
    driver.get(args.baseurl)
    time.sleep(2)  

    # 选择 Accept All
    selectAcceptAll(driver)
    time.sleep(1)
    
    try:
        button = driver.find_element(By.XPATH, '//*[@id="root"]/header/div/div/a[1]/span')
        driver.execute_script("arguments[0].click();", button)
        time.sleep(1)
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
            if len(cookies) == 3:
                print("Login successful")
                break
    except Exception as e:
        print(f"Error during login: {e}")
        return datalist

    # 打开文件以追加模式写入
    with open("C:/Users/Administrator/Desktop/py/3D/Machine-Learning-Project/crawler/sketchfab/urls.txt", "a") as f:
        # 滚动页面以触发懒加载，确保获取所有图片链接
        scroll_increment = 400
        num_downloads = 0
        while num_downloads <= 12000:
            # 滚动到页面底部
            while True:
                scrollTop = driver.execute_script("return document.documentElement.scrollTop || document.body.scrollTop")
                driver.execute_script(f"window.scrollBy(0, {scroll_increment})")
                time.sleep(0.5)  # 随机等待，模拟人类行为
                new_scrollTop = driver.execute_script("return document.documentElement.scrollTop || document.body.scrollTop")
                if new_scrollTop == scrollTop:
                    break
            
            new_urls = findModels(driver, datalist)
            # 将新添加的URL写入文件
            for url in new_urls:
                f.write(url + "\n")
            
            # 回滚一步找到 "LOAD MORE" 按钮并点击
            driver.execute_script(f"window.scrollBy(0, -{scroll_increment})")
            try:
                load_more_button = driver.find_element(By.CSS_SELECTOR, 'button.btn-primary.btn-large')
                driver.execute_script("arguments[0].click();", load_more_button)
                time.sleep(3)  # 等待新内容加载
            except:
                pass

    driver.quit()

    return datalist

def main(args):
    datalist = getData(args)
    # 将所有爬取的网页信息写入文件urls.txt
    # with open("C:/Users/Administrator/Desktop/py/3D/Machine-Learning-Project/crawler/sketchfab/urls.txt", "a") as f:
    #     for data in datalist:
    #         f.write(data + "\n")

def get_args(parser: argparse.ArgumentParser):

    # 要爬取的网页链接
    parser.add_argument("--baseurl", default="https://sketchfab.com/3d-models/categories/architecture?features=downloadable&sort_by=-likeCount", type=str, help="The URL to crawl")
    # 设置 EdgeDriver 路径
    parser.add_argument("--edgedriver", default="D:\edgedriver_win64\msedgedriver.exe", type=str, help="The path to EdgeDriver")
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