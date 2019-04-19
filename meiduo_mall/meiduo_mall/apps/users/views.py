from django.shortcuts import render
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView, ListAPIView
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_jwt.settings import api_settings

from goods.serializer import SKUSerializer
from .models import User, Address
from .serializers import CreateUserSerializer, UserDetailSerializer, EmailSerializer, UserAddressSerializer, \
    AddressTitleSerializer, UserBrowserHistorySerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.mixins import UpdateModelMixin
from django_redis import get_redis_connection
from goods.models import SKU
from rest_framework_jwt.views import ObtainJSONWebToken
from carts.utils import merge_cart
from datetime import datetime


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
