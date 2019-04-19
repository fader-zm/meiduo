from django.conf import settings
from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.settings import api_settings
from itsdangerous import TimedJSONWebSignatureSerializer as TJWSSerializer
from random import randint

from goods.serializer import SKUSerializer
from utils.exceptions import logger
from .models import User
from .serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, UserBrowserHistorySerializer, ModifyPasswordSerializers, ChangePasswordSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.mixins import UpdateModelMixin
from django_redis import get_redis_connection
from goods.models import SKU
from rest_framework_jwt.views import ObtainJSONWebToken
from carts.utils import merge_cart
from datetime import datetime
from . import constants
from celery_tasks.sms.tasks import send_sms_code



class UserView(CreateAPIView):
    """用户注册 本质是新增"""
    # 指定序列化器
    serializer_class = CreateUserSerializer


class UserNameCountView(APIView):
    """判断用户是否注册"""
    
    def get(self, request, username):
        count = User.objects.filter(username=username).count()
        print(count)
        data = {
            "username": username,
            "count": count
        }
        return Response(data)


class UserMobileCountView(APIView):
    """判断用户号码是否注册"""
    
    def get(self, request, mobile):
        count = User.objects.filter(mobile=mobile).count()
        print(count)
        data = {
            "mobile": mobile,
            "count": count
        }
        return Response(data)


class UserDetailVIew(RetrieveAPIView):
    """用户详细信息展示"""
    serializer_class = UserDetailSerializer
    # 指定通过认证 也就是登录用户
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """重写genericVIew的get_object方法 返回要展示的对象"""
        return self.request.user


class EmailView(UpdateAPIView):
    """跟新保存用户的邮箱"""
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class EmailVerifyView(APIView):
    """邮箱验证激活"""
    
    def get(self, request):
        # 获取token
        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 验证token
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        user.email_active = True
        user.save()
        return Response({'message': 'OK'})


class AddressViewSet(UpdateModelMixin, GenericViewSet):
    """用户收货地址增删改查"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserAddressSerializer
    
    # 指定查询集
    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)
    
    def create(self, request):
        user = request.user
        num = user.addresses.all().count()
        # 下面的过滤方式也可以
        # Address.objects.filter(user=user)
        if num >= 20:  # 地址数量最多20
            return Response({"message": "收货地址已满不能添加"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    # GET /addresses/
    def list(self, request):
        """ 用户地址列表数据 """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': 20,
            'addresses': serializer.data,
        })
    
    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """处理删除"""
        address = self.get_object()
        # 进行逻辑删除
        address.is_deleted = True
        address.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # put /addresses/pk/title/
    # 需要请求体参数 title
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """ 修改标题"""
        address = self.get_object()
        serializer = AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """ 设置默认地址 """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)


class UserBrowserHistoryView(CreateAPIView):
    """用户商品浏览记录仪"""
    serializer_class = UserBrowserHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """查询用户的浏览记录"""
        # 创建redis连接对象
        redis_conn = get_redis_connection("history")
        user = request.user
        # 获取redis中当前用户的浏览记录列表数据 bytes类型数据
        sku_ids = redis_conn.lrange("history_%d" % user.id, 0, -1)
        # 把sku_id对应的sku模型查询出来
        # SKU.objects.filter(id__in=sku_ids)  # 用此方式获取sku模型顺序就乱了
        sku_list = []
        for sku_id in sku_ids:
            sku = SKU.objects.get(id=sku_id)
            sku_list.append(sku)
            # 创建序列化器进行序列化
        serializer = SKUSerializer(sku_list, many=True)
        return Response(serializer.data)


jwt_response_payload_handler = api_settings.JWT_RESPONSE_PAYLOAD_HANDLER


class UserAuthorizeView(ObtainJSONWebToken):
    """自定义账号密码登录  实现购物车合并功能"""
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            #  账号登录时合并购物车
            merge_cart(request, user, response)
            return response
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# /accounts/xxxx/sms/token/ ?text= + &image_code_id='
class VerifyImageCode(APIView):
    """ 验证用户是否存在和验证码是否正确"""
    
    def get(self, request, username):
        # 获取前端传入的参数
        image_code = request.query_params.get("text")
        image_code_id = request.query_params.get("image_code_id")
        
        # 判断用户是否存在  不存在就不修改
        try:
            user = User.objects.filter(Q(username=username) | Q(mobile=username)).first()
            mobile = user.mobile
        except:
            return Response({"message": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        # 从redis获取真是的图形验证码 进行对比
        redis_conn = get_redis_connection("verifications")
        # 'Image_Code_%s' % image_code_id
        real_image_code = redis_conn.get('Image_Code_%s' % image_code_id).decode()
        if not real_image_code:
            return Response({"message": "验证码过期"})
        if image_code.lower() != real_image_code.lower():
            return Response({"message": "验证码错误"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 生成token
        serializer = TJWSSerializer(settings.SECRET_KEY, 300)
        data = {"mobile": mobile}
        token = serializer.dumps(data).decode()
        mobile1 = mobile[0:3] + "****" + mobile[7:]
        data = {
            "mobile": mobile1,
            "access_token": token
        }
        return Response(data)


#  sms_codes/?access_token=
class SendSmsCode(APIView):
    """发送短信验证码"""
    
    def get(self, request):
        # 获取前端传入的token 解析得到mobile
        token = request.query_params.get("access_token")
        serializer = TJWSSerializer(settings.SECRET_KEY, 300)
        data = serializer.loads(token)
        mobile = data.get("mobile")
        try:
            user = User.objects.get(mobile=mobile)
        except:
            return Response({"message": "用户不存在"}, status=status.HTTP_404_NOT_FOUND)
        
        # 连接redis 保存验证码
        redis_conn = get_redis_connection("verifications")
        send_flag = redis_conn.get("send_flag_%s" % mobile)
        if send_flag:
            return Response({"message": "手机已经发送验证码"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 没发送过验证码,就生成验证码,并且保存验证码到redis数据库
        real_sms_code = "%06d" % randint(0, 999999)
        logger.info(real_sms_code)
        
        pl = redis_conn.pipeline()
        pl.setex(mobile, 300, real_sms_code)
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        pl.execute()
        # 触发异步任务 发送短信
        send_sms_code.delay(mobile, real_sms_code)
        # 响应
        return Response({"message": "ok"})


# accounts/xxxx/password/token/?sms_code=xxx
class VrerifySmsCode(APIView):
    """验证短信短信验证码"""
    
    def get(self, request, username):
        # 获取客户输入的验证码
        sms_code = request.query_params.get("sms_code")
        user = User.objects.filter(Q(username=username) | Q(mobile=username)).first()
        mobile = user.mobile
        # 获取redis数据库的真是验证码 进行比较
        redis_conn = get_redis_connection("verifications")
        real_sms_code = redis_conn.get(mobile)
        if not real_sms_code:
            return Response({"message": "短信验证码过期"})
        if sms_code != real_sms_code.decode():
            return Response({"message": "验证码错误"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 生成token返回给前端
        serializer = TJWSSerializer(settings.SECRET_KEY, 300)
        data1 = {"user_id": user.id, }
        token = serializer.dumps(data1).decode()
        data = {
            "user_id": user.id,
            "access_token": token
        }
        return Response(data)


# users/'+ this.user_id +'/password/
class ModifyPassword(APIView):
    """修改密码"""
    
    def post(self, request, user_id):
        # 获取前端在token包装的user_id
        token = request.data.get("access_token")
        #
        serializer = TJWSSerializer(settings.SECRET_KEY, 300)
        data = serializer.loads(token)
        real_user_id = data.get("user_id")
        
        # 判断id是否一样
        if int(user_id) != real_user_id:
            return Response({"message": "用户id不一致"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = User.objects.get(id=user_id)
        serializer = ModifyPasswordSerializers(user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# /users/'+vm.user_id+'/password/
class ChangePassword(UpdateAPIView):
    """修改密码"""
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def get_object(self):
        return self.request.user
