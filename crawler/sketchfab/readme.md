## 爬取sketchfab的示例代码

#### Dependency

- python 3.x
- selenium: 4.x (一个爬虫库)
- chromedriver.exe / edgedriver.exe
- keyboard
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

1. 修改selector的读取和写入文件路径以及你的edgedriver路径
2. 运行程序，y保留n舍去，不用按enter确认

# 如何下载
1. 待定
