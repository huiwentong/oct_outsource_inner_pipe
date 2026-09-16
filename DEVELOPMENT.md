# 协同开发说明

---
## 开发前准备

需要安装uv

cd 进相关开发包有pyproject.toml的根目录

执行 uv sync 完成所有伊赖补全

执行完uv sync 后将自己的IDE的 interpreter path或者python environment 指定为根目录的.venv/Script/python.exe 即可

如果后续计划将某些应用放入到rez环境中执行，那么在启动ide的时候使用命令行启动
> rez env oct [其他的需要依赖的包] -- {你的IDE}.exe

这样就可以在IDE中自动补全类似于 import oct 或者import oct_houdini之类的调用了
测试代码的话也改成 
> rez env oct [其他的需要依赖的包] -- uv run python -m {你需要测试的模块}



---

## 关于发包程序

发包程序的开发，我们只关注gui_manager这个包即可

发包程序的快速启动命令

```bash
cd gui_manager
uv run python -m collector
```

对于单环节的开发，我们只需要关注环节代码即可

环节代码： /gui_manager/components/{你的环节}.py

在此之外还还需要关注一些通用的依赖模块

通用工具位置： /gui_manager/utils/

### 首先介绍环节代码中的开发注意事项

这里使用了注册机制，所以在环节代码中的类不做强制命名要求，但是
类必须挂上注册装饰器以及dataclass装饰器

```python
@register("mod")
@dataclass
class ModComponent(StepComponent):
```
这个Component类中我们只需要关注三个成员函数实现

* analysis_relies

        这个函数里面是必须实现的
        需要分析出来该资产的收包环节会对哪些上游环节和资产产生依赖
        并赋值self.rely_step和self.rely_assets

* analysis_transfer_folders

        这个函数根据环节来进行选择实现
        这个函数主要用于收集所有的需要发送到ftp的文件或者文件夹
        并把这些自动拾取到的上游资产文件赋值给self.transfer_folders
        这个dataclass成员变量是一个字典
        其中key是寻找到的数据的源路径
        value是应该放入ftp的目标路径
        一般父类会解析出来当前资产环节在ftp的目标路径是什么
        可以参考
        > self.transfer_folders[i] = str(Path(self.ftp_tar) / Path(i).name)


* extra_ui

        这个函数可以选择性的实现
        可能对于大部分环节都不需要实现一个额外的ui
        这个函数主要用于给默认的环节ui下面添加额外的ui控件
        这个空间可以辅助操作人员显示更多的信息
        或者向关键数据中(self.transfer_folders,self.rely_step和self.rely_assets)传递额外的变动

### 关于如何验证

验证环节的逻辑是否执行成功主要从几个层面来验证

- 目标文件是否有被上传到ftp对应路径中

        验证方式：登录filezila到相应目录中查看是否上传
- 文件传输到ftp后是否有给到正确的权限
- - 方法一：直接进入服务器

        登录ftp服务器{192.168.20.217}(临时服务器后续会变)
        进入ftp的容器中
        docker exec -it outsource-pip-vsftpd-1 bash
        cd到/srv/ftp/oct/... 然后getfacl {你的目标文件}
- - 方法二：使用网络请求对文件进行查看

        curl -s "http://{192.168.20.217}/get_path_group?_path=/srv/ftp/oct/mk2/asset/dasheng/mod" | python3 -m json.tool

- 指定的外包成员是否拿到了正确的权限
- - 方法一：直接进入服务器

        登录ftp服务器{192.168.20.217}(临时服务器后续会变)
        进入ftp的容器中
        docker exec -it outsource-pip-vsftpd-1 bash
        cd到/srv/ftp/oct/... 然后执行groups username
- - 方法二：使用网络请求对文件进行查看

        curl -s "http://{192.168.20.217}/user_groups?uname=yuanli" | python3 -m json.tool


---

## 关于收包程序

收包程序的开发，稍微有些复杂，它涉及到多个互相引用的docker服务


