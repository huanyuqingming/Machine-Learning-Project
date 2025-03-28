## 爬取sketchfab的示例代码

#### Dependency

- python 3.x
- selenium: 4.x (一个爬虫库)
- chromedriver.exe / edgedriver.exe
- keyboard
- tqdm
- transformer
- sentencepiece
反正没有的库装就好了

#### 必要操作

在sketchfab网站上注册号用户（邮箱+密码），然后在my_account.py里的EMAIL和PASSWORD修改为对应的值。

#### 常见报错

如果报错：chromedriver 版本不匹配，则按照报错信息的指引，去官网上下载对应版本的 chromedriver 即可。

# 配置chromedriver或者edgedriver

1. 下载chrome
2. 将该目录下的chromedriver.exe复制到chrome安装目录的Application目录下，如 `C:/Program Files/Google/Chrome/Application/chromedriver.exe`。
3. edge同理，把上述所有chrome换成edge就行

# 如何筛选

1. 修改`selector.py`的edgedriver路径
2. 运行程序，y保留n舍去，不用按enter确认

# 如何下载
1. 检查是否有`my_account.py`，文件内容为：
    ```
    EMAIL = "your_email_address"
    PASSWORD = "your_password"
    ```
2. 修改`cwarler.py`中`get_args()`的参数
3. 保证`data`文件夹中没有`.crdownload`文件
4. 狠狠地运行

# 如何添加描述
1. 确保此前下载在`data`文件夹中的`.glb`文件的修改日期顺序与`downloaded_urls.txt`中的顺序一致
2. 运行`get_description.py`