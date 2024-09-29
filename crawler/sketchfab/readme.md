## 爬取sketchfab的示例代码

#### Dependency

- python 3.x
- selenium: 4.x (一个爬虫库)
- chromedriver.exe

#### 必要操作

在sketchfab网站上注册号用户（邮箱+密码），然后在my_account.py里的EMAIL和PASSWORD修改为对应的值。

#### 常见报错

如果报错：chromedriver 版本不匹配，则按照报错信息的指引，去官网上下载对应版本的 chromedriver 即可。

# 配置chromedriver（不然get_url.py跑不了）

1. 下载chrome；
2. 将该目录下的chromedriver.exe复制到chrome安装目录的Application目录下，如 `C:/Program Files/Google/Chrome/Application/chromedriver.exe`。

# 如何爬

1. 运行 `get_url.py`，将爬取的模型url保存在 `urls.txt`中；
2. 运行 `crawler.py`，下载每个url对应的模型；
3. 下载好的模型会保存在 `crawler\sketchfab\data`中。
