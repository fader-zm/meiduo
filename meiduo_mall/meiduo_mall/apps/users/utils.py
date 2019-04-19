from django.contrib.auth.backends import ModelBackend
import re
from .models import User


def jwt_response_payloads_handler(token, user=None, request=None):
    """重写JWT登录视图的构造响应数据函数,多追加 user_id和username"""
    # 该函数默认是只有返回token值  但是需要返回user的部分信息 所以需要重写
    return {
        "token": token,
        "username": user.username,
        "user_id": user.id
    }


# 动态获取user
def get_user_by_account(account):
    """通过传入的账号动态获取user 模型对象"""
    # 有可以是手机号, 有可能是用户名
    try:
        if re.match(r"^1[3-9]\d{9}$", account):
            user = User.objects.get(mobile=account)
        else:
            user = User.objects.get(username=account)
    except User.DoesNotExist:
        return None
    else:
        return user


class USerNameMobileAuthBacend(ModelBackend):
    """修改django的认证类  为了实现多账号登录  即号码 用户名都可以登录"""
    def authenticate(self, request, username=None, password=None, **kwargs):
        # 获取user
        user = get_user_by_account(username)
        # 判断当前前端传入的密码是否正确
        if user and user.check_password(password):
             # 返回user
            return user
