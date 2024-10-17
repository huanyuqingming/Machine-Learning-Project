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
import argparse
import time
import keyboard

def filter_urls(args):
    part_number = 1 #自己设置，1-13
    input_file_path = f"{args.input_file_prefix}_part_{part_number}.txt"
    output_file_path = f"{args.output_file_prefix}_part_{part_number}.txt"

    with open(input_file_path, 'r') as file:
        urls = file.readlines()
    
     # 读取已经存在的URL
    if os.path.exists(output_file_path):
        with open(output_file_path, 'r') as file:
            existing_urls = set(file.read().splitlines())
    else:
        existing_urls = set()

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

    with open(output_file_path, 'a+') as file:
        for url in urls:
            url = url.strip()
            if not url:
                continue

            # 打开链接
            driver.get(url)
            time.sleep(1.5)  # 等待页面加载

            print(f"是否保留链接 {url}? (按 'y' 保留, 'n' 不使用)")

            # 等待用户按键
            while True:
                if keyboard.is_pressed('y'):
                    if url not in existing_urls:
                        file.write(url + '\n')
                        file.flush()
                        os.fsync(file.fileno())
                        existing_urls.add(url)
                        print(f"链接 {url} 已保留")
                    else:
                        print(f"链接 {url} 已存在，跳过")
                    break
                elif keyboard.is_pressed('n'):
                    print(f"链接 {url} 不使用")
                    break
                time.sleep(0.1)  # 防止CPU占用过高

    print("筛选完成")


def get_args(parser: argparse.ArgumentParser):
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 读取urls路径前缀
    parser.add_argument("--input_file_prefix", default=os.path.join(base_dir, "urls"), type=str, help="The prefix of the input file")
    # 保存筛选后的urls路径前缀
    parser.add_argument("--output_file_prefix", default=os.path.join(base_dir, "filtered_urls"), type=str, help="The prefix of the output file")
    # 设置 EdgeDriver 路径
    parser.add_argument("--edgedriver", default="D:/edgedriver_win64/msedgedriver.exe", type=str, help="The path to EdgeDriver")
    # 是否使用无头模式，即不打开浏览器界面
    parser.add_argument("--headless", default=False, type=bool, help="Whether to use headless mode")
    # 持续按下键的时间
    parser.add_argument("--finish_time", default=1, type=int, help="The time to press down key")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    args = get_args(parser)
    filter_urls(args)