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

关于收包程序需要调用到的服务，我设计成了热重载的模式，每当大家完成代码更改后

到服务器中
```bash
cd /home/test/test/oct_outsource_inner_pipe
git pull
```
即可完成behaviour模块的热更新，无需重启整个服务或者单个behaviour服务

### 关于log在哪里

所有outsource的log都存放在
> /var/lib/docker/volumes/outsource-pip_outsourcelogs/_data
当我们ll时会看到
```bash
drwxr-xr-x 2 root root    4096  9月 16 11:04 ./
drwx-----x 3 root root    4096  8月 13 10:29 ../
-rw-r--r-- 1 root root     551  9月 16 11:04 behaviour.log
-rw-r--r-- 1 root root   24420  9月 15 18:25 behaviour.log.2026-09-15
-rw-r--r-- 1 root root    3887  9月 16 11:04 permissionmanager.log
-rw-r--r-- 1 root root   39373  8月 13 18:45 permissionmanager.log.2026-08-13
-rw-r--r-- 1 root root   23202  8月 14 16:16 permissionmanager.log.2026-08-14
-rw-r--r-- 1 root root    2656  9月  1 10:24 permissionmanager.log.2026-09-01
-rw-r--r-- 1 root root   16417  9月  2 14:59 permissionmanager.log.2026-09-02
-rw-r--r-- 1 root root   34093  9月  3 14:59 permissionmanager.log.2026-09-03
-rw-r--r-- 1 root root     101  9月  4 11:09 permissionmanager.log.2026-09-04
-rw-r--r-- 1 root root   17746  9月  8 19:08 permissionmanager.log.2026-09-08
-rw-r--r-- 1 root root    3115  9月  9 14:45 permissionmanager.log.2026-09-09
-rw-r--r-- 1 root root   53801  9月 15 18:25 permissionmanager.log.2026-09-15
-rw-r--r-- 1 root root     740  9月 16 11:04 versionwatch.log
-rw-r--r-- 1 root root     441  8月 14 16:16 versionwatch.log.2026-08-14
-rw-r--r-- 1 root root     126  9月  1 10:23 versionwatch.log.2026-09-01
-rw-r--r-- 1 root root   66874  9月  2 17:10 versionwatch.log.2026-09-02
-rw-r--r-- 1 root root    6125  9月  3 12:49 versionwatch.log.2026-09-03
-rw-r--r-- 1 root root 1409207  9月  8 19:17 versionwatch.log.2026-09-08
-rw-r--r-- 1 root root     677  9月  9 14:51 versionwatch.log.2026-09-09
-rw-r--r-- 1 root root   26642  9月 15 18:30 versionwatch.log.2026-09-15
```
针对不同模块的不同服务会有不同的log，在这里我们只需要关注behaviour.log即可

### 收包环节代码的开发注意事项

针对不同环节的代码，都存放在了 /behaviour/dispatch_bahav/{你的环节}.py中

针对一些通用调用的工具，存放在了 /behaviour/utils中包括Deadline的一些官方函数，这块后续可能需要进一步补充，封装成易于我们自己调用的类

同样，不同的环节的逻辑能力也是以Component类来实现的，Component继承自StepComponent类
所有Component的类需要依赖的数据都在self.event中

Event类
```python
@dataclass
class Event():
    vendor: str
    manifest_file:str = ''
    asset:str = ''
    step:str = ''
    checksum:str = ''
    version:str = ''
    dst_path:str = ''
```

关于许多文件合规性检查都在父类中已经实现，我们在子类中只需要关注两个成员函数即可

- check_extra

        这一块是根据不同环节的需求，针对外包商回传的manifest文件和回传数据做更详细的补充
        manifest文件可以通过self.event.manifest_file来获取到，这个文件是一个json文件
        如果检查到错误，需要return 错误说明，如果全部检查通过，也需要return ''


- publish_to_deadline

        这一块主要是当所有数据回收成功后自动发布的逻辑，
        需要在这块实现如何将回传到w盘的数据发布到shogun中
        具体的发布需要使用农场机器进行操作，不能直接在服务器中操作（主要也操作不了）
        可以在self.event.dst_path中找到数据回传到了w盘的哪个具体位置，需要注意的是这个路径是linux路径
        如果发布到deadline中需要将此路径转换成windows挂载的路径！



### 如何测试

1. **登录 FTP**
   使用 filezilla 客户端连接到指定的外包商测试账号。

2. **准备标准文件**
   准备好用于测试收包功能的标准数据文件。

3. **上传至指定目录**
   将文件上传到以下路径结构中：
   ```text
   /{外包商}/{资产}/{环节}/
   ```

4. **触发收包程序**
   在上述同一目录下放入 `manifest.json` 文件，系统将自动识别并触发收包流程。
> 📎 **参考文档**：`manifest.json` 的格式规范请参阅 [设计纲要](thinking.md)

### 成功的收包流程

最终一个成功的收包流程以

1. 外包数据成功扫入到w盘中
2. w盘中的数据成功发布到shotgun上
3. shotgun发布成功后根据我们的发布流程在I盘有对应的落盘文件
4. 成功后钉钉通知到相关人员（相关环节制片，相关外包商）

以上四点为准


