from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):
    
    def __init__(self, client_path=None, base_url=None):
        # fastDFS的客户端配置文件路径
        self.client_path = client_path or settings.FDFS_CLIENT_CONF
        # storage服务器ip:端口
        self.base_url = base_url or settings.FDFS_BASE_URL
    
    def _open(self, name, mode="rb"):
        """" 用来打开文件的  实现存储到远程fastDFS服务器
        不需要打开文件 所以重写此方法后什么也不用做"""
        pass
    
    def _save(self, name, content):
        """文件存储时调用此方法  但是此方法默认时候保存到本地的
        所以需要去修改 保存到远程服务器"""
        # name  上传文件的名字
        # content 以rb二进制方式打开的文件对象  通过content.read()就可以读取到文件的二进制数据
        
        # 创建fastDFS客户端
        # client = Fdfs_client("meiduo_mall/utils/fastdfs/client.conf")
        # client = Fdfs_client(settings.FDFS_CLIENT_CONF)
        client = Fdfs_client(self.client_path)
        
        # 通过客户端调用上传文件的方法上传文件
        # client.upload_by_filename("上传文件的绝对路径")   上传的文件有后缀 比如png
        # client.upload_by_buffer  可以通过二进制数据进行上传   没有后缀
        ret = client.upload_by_buffer(content.read())
        # 判断文件是否上传成功
        if ret.get("Status") != "Upload successed.":
            raise Exception("Upload file failed")
        # 获取并返回file_id
        file_id = ret.get("Remote file_id")
        return file_id
    
    def exists(self, name):
        """ 当要进行上传时都调用此方法判断文件是否上传
        如果没有上传才会调用save方法"""
        # 返回布尔值 True表示已经上传了  False表示没有上传,才需要上传
        return False
    
    def url(self, name):
        """当访问图片是 就会调用此方法获取图片的绝对路径"""
        # return "http://192.168.248.185:8888/" + file_id
        # return settings.FDFS_BASE_URL + name
        return self.base_url + name

# client = Fdfs_client('meiduo_mall/utils/fastdfs/client.conf')
# ret = client.upload_by_filename('/home/python/Desktop/3.jpg')
