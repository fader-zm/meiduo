from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from QQLoginTool.QQtool import OAuthQQ
from rest_framework_jwt.settings import api_settings

from oauth.models import OAuthQQUser
from oauth.serializers import QQAuthUserSerializer
from django.conf import settings
from .utils import generate_save_user_token, check_save_user_token
from carts.utils import merge_cart
import logging

logger = logging.getLogger("django")


# QQ_CLIENT_ID = '101514053'
# QQ_CLIENT_SECRET = '1075e75648566262ea35afa688073012'
# QQ_REDIRECT_URI = 'http://www.meiduo.site:8080/oauth_callback.html'


class QQOauthURLView(APIView):
    """拼接QQ登录网址"""

    def get(self, request):
        # 提取前端传入的next参数记录用户从哪里去到login界面的  用status记录
        next = request.query_params.get("next", "/")
        # 利用QQ登录SDK
        # 创建QQ登录工具对象
        oath = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                       redirect_uri=settings.QQ_REDIRECT_URI, state=next)
        # 调用对象的方法  获取拼接QQ登录链接
        login_url = oath.get_qq_url()
        return Response({"login_url": login_url})


class QQAuthUserView(APIView):
    """QQ登录成功后的回调处理"""

    def get(self, request):
        # 获取前端传入的code
        code = request.query_params.get("code")
        if not code:
            return Response({"message": "缺少参数"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建QQ工具对象
        oauth = OAuthQQ(client_id=settings.QQ_CLIENT_ID, client_secret=settings.QQ_CLIENT_SECRET,
                        redirect_uri=settings.QQ_REDIRECT_URI)
        # 调用它的get_access_token(code)方法
        try:
            access_token = oauth.get_access_token(code)
            # 调用它的get_open_id(access_token)方法
            openid = oauth.get_open_id(access_token)
        except Exception as e:
            logger.info(e)
            return Response({"message": "QQ服务器不可用"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 查询数据库是否有这个openid
        try:
            authQQUser = OAuthQQUser.objects.get(openid=openid)
        except OAuthQQUser.DoesNotExist:
            # 如果openid没有查到 说明没有绑定过 openid加密后响应给前端保存 后期绑定使用
            secret_openid = generate_save_user_token(openid)
            return Response({"access_token": secret_openid})

        else:
            # 查到了 说明已经绑定过了 直接登录成功 返回JWT状态保存信息
            user = authQQUser.user  # 利用外键查找用户信息
            # 手动生成token
            jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
            jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER
            payload = jwt_payload_handler(user)
            token = jwt_encode_handler(payload)

            response = Response({
                "token": token,
                "username": user.username,
                "user_id": user.id
            })
            # 在此处调用合并购物车方法
            merge_cart(request, user, response)
            return response

    def post(self, request):
        """openid绑定用户借口"""
        serializer = QQAuthUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 函数引用 生成jwt
        payload = jwt_payload_handler(user)  # 根据user生成用户相关的载荷信息
        token = jwt_encode_handler(payload)
        response = Response({
            "username": user.username,
            "user_id": user.id,
            "token": token
        })

        # 在此处调用合并购物车方法
        merge_cart(request, user, response)
        return response
