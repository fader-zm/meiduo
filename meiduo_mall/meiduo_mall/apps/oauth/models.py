from django.db import models
from users.models import User
from meiduo_mall.utils.models import BaseModel


class OAuthQQUser(BaseModel):
    """    QQ登录⽤用户数据    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='⽤用户')
    openid = models.CharField(max_length=64, verbose_name='openid', db_index=True)
    
    class Meta:
        db_table = 'tb_oauth_qq'
        verbose_name = 'QQ登录⽤用户数据'
        verbose_name_plural = verbose_name


class OAuthSinaUser(BaseModel):
    """
    Sina登录用户数据
    """
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, verbose_name='用户')
    access_token = models.CharField(max_length=64, verbose_name='access_token', db_index=True)
    
    class Meta:
        db_table = 'tb_oauth_sina'
        verbose_name = 'sina登录用户数据'
        verbose_name_plural = verbose_name
