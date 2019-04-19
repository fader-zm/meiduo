import base64
import pickle

from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializer import CartSerializer, SKUCartSerializer, CartDeleteSerializer, CartSelectedAllSerializer
from rest_framework import status
from django_redis import get_redis_connection
from goods.models import SKU


class CartView(APIView):
    """购物车的增删改查"""

    def perform_authentication(self, request):
        """重写此方法可以延迟dispatch之前的认证操作 当执行request.user或request.auth才会进行认证"""
        pass

    def post(self, request):
        """新增购物车商品"""
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 获取校验后的数据
        sku_id = serializer.validated_data.get("sku_id")
        count = serializer.validated_data.get("count")
        selected = serializer.validated_data.get("selected")

        try:
            # 执行此行代码时会进行认证逻辑  登录用户不会报错 但是未登录会报错 自己捕获异常
            user = request.user
        except:
            user = None
        response = Response(serializer.data, status=status.HTTP_201_CREATED)
        # is_authenticated()方法判断用户是否登录
        if user and user.is_authenticated:
            # 登录用户购物车用redis保存
            """
            hash: {'sku_id_1': 2, 'sku_id_16':1}
            set: {sku_id_1}
            """
            # 创建redis连接对象
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()
            # 添加到hash字典  如果添加的商品存在 会做增量,如果不存在就会新增
            pl.hincrby("cart_%d" % user.id, sku_id, count)
            # 把勾选的商品的sku_id添加到set集合
            if selected:
                pl.sadd("selected_%d" % user.id, sku_id)
            pl.execute()
            # return Response(serializer.data,status=status.HTTP_201_CREATED)

        else:  # 未登录用户购物车用cookie保存
            """
            {
                'sku_id_1': {'count': 1, 'selected': True},
                'sku_id_16': {'count': 1, 'selected': True}
            }
            """
            # 获取cookie购物车数据
            cart_str = request.COOKIES.get("cart")
            if cart_str: # 购物车有商品
                # 字符串转换成bytes类型字符串
                cart_str_bytes = cart_str.encode()
                # bytes类型字符串 转成bytes类型
                cart_bytes = base64.b64decode(cart_str_bytes)
                # bytes类型 转成字典
                cart_dict = pickle.loads(cart_bytes)
            else:  # 购物车空的 第一次添加购物车
                cart_dict = {}

            # 增量计数  先判断添加到购物车的商品是否之前添加过
            if sku_id in cart_dict:
                origin_count = cart_dict[sku_id]["count"]
                count += origin_count
            #  把商品添加到购物车
            cart_dict[sku_id] = {
                "count": count,
                "selected": selected
            }
            #  把购物车设置到cookie  必须是字符串类型
            cart_bytes = pickle.dumps(cart_dict)
            cart_str_bytes = base64.b64encode(cart_bytes)
            cart_str = cart_str_bytes.decode()
            # 创建响应对象 设置cookie(字符串)
            # response = Response(serializer.data,status=status.HTTP_201_CREATED)
            response.set_cookie("cart", cart_str)
        return response

    def get(self, request):
        """查询购物车"""
        try:
            user = request.user
        except:
            user = None
        if user and user.is_authenticated:
            # 创建redis连接对象 获取hash数据和set集合数据(bytes类型数据)
            redis_conn = get_redis_connection("cart")
            cart_redis_dict = redis_conn.hgetall("cart_%d" % user.id)
            selecteds = redis_conn.smembers("selected_%d" % user.id)
            cart_dict = {}
            for sku_id_bytes in cart_redis_dict:
                cart_dict[int(sku_id_bytes)] = {
                    "count": int(cart_redis_dict[sku_id_bytes]),
                    "selected": sku_id_bytes in selecteds
                }
        else:
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                cart_str_bytes = cart_str.encode()
                cart_bytes = base64.b64decode(cart_str_bytes)
                cart_dict = pickle.loads(cart_bytes)
            else:
                return Response({"message": "没有购物车商品"})
        # 从字典中去除所有的sku_id,即是字典的键
        sku_ids = cart_dict.keys()
        # 直接查询出所有的sku模型返回查询集  可能是无序的
        skus = SKU.objects.filter(id__in=sku_ids)
        # 给每个sku增加count和selected属性
        for sku in skus:
            sku.count = cart_dict[sku.id]["count"]
            sku.selected = cart_dict[sku.id]["selected"]
        # 创建序列化器进行序列化
        serializer = SKUCartSerializer(skus, many=True)
        return Response(serializer.data)

    def put(self, request):
        """购物车修改"""
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # 获取校验后的数据
        sku_id = serializer.validated_data.get("sku_id")
        count = serializer.validated_data.get("count")
        selected = serializer.validated_data.get("selected")

        try:
            user = request.user
        except:
            user = None
        response = Response(serializer.data)
        if user and user.is_authenticated:
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()
            pl.hset("cart_%d" % user.id, sku_id, count)
            if selected:
                pl.sadd("selected_%d" % user.id, sku_id)
            else:  # 把钩去掉 要在集合删除对应的sku_id
                pl.srem("selected_%d" % user.id, sku_id)
            pl.execute()
            # return Response(serializer.data)

        else:
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return Response({"message": "没有购物车数据"})
            #  直接覆盖原来的cookie字典数据
            cart_dict[sku_id] = {
                "count": count,
                "selected": selected
            }
            # 把cookie字典转换成字符串
            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # response = Response(serializer.data)
            response.set_cookie("cart", cart_str)
        return response

    def delete(self, request):
        """删除购物车商品"""
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data.get("sku_id")

        try:
            user = request.user
        except:
            user = None
        response = Response(status=status.HTTP_204_NO_CONTENT)
        if user and user.is_authenticated:
            redis_conn = get_redis_connection("cart")
            pl = redis_conn.pipeline()
            pl.hdel("cart_%d" % user.id, sku_id)
            pl.srem("selected_%d" % user.id, sku_id)
            pl.execute()
            # Response(status=status.HTTP_204_NO_CONTENT)
        else:
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return Response({"message": "cookie不存在"})
            # 把要删除的sku_id从cookie字典中删除
            if sku_id in cart_dict:
                del cart_dict[sku_id]
            # 判断购物车是否还有商品 再决定要不要设置回cookie
            if len(cart_dict):   # 购物车还有商品
                cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
                # response = Response(status=status.HTTP_204_NO_CONTENT)
                response.set_cookie("cart", cart_str)
            else:  # 购物车商品全部删除清空了
                # response = Response(status=status.HTTP_204_NO_CONTENT)
                response.delete_cookie("cart")
        return response


class CartSelectedAll(APIView):
    """购物车的全选操作"""

    def perform_authentication(self, request):
        pass

    def put(self,request):
        serializer = CartSelectedAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data.get("selected")

        try:
            user = request.user
        except:
            user = None

        response = Response(serializer.data)
        if user and user.is_authenticated:
            redis_conn = get_redis_connection("cart")
            cart_redis_dict = redis_conn.hgetall("cart_%d" % user.id)
            sku_ids = cart_redis_dict.keys()
            if selected:
                redis_conn.sadd("selected_%d" % user.id, *sku_ids)
            else:
                redis_conn.srem("selected_%d" % user.id, *sku_ids)
            # return Response(serializer.data)
        else:
            cart_str = request.COOKIES.get("cart")
            if cart_str:
                cart_dict = pickle.loads(base64.b64decode(cart_str.encode()))
            else:
                return Response({"message":"cookie没有数据"})

            for sku_id in cart_dict:
                cart_dict[sku_id]["selected"] = selected

            cart_str = base64.b64encode(pickle.dumps(cart_dict)).decode()
            # response = Response(serializer.data, status=status.HTTP_201_CREATED)
            response.set_cookie("cart",cart_str)
        return response



