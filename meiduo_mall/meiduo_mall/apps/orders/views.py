from rest_framework.views import APIView
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated

from goods.models import SKU
from decimal import Decimal
from .serializer import OrderSettlementSerializer, UserOrderSerializer, CommitOrderSerializer
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView, ListAPIView
from orders.models import OrderInfo


class OrderSettlementView(APIView):
    """订单结算"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # 创建连接对象　获取hash和set数据
        redis_conn = get_redis_connection("cart")
        cart_hash_dict = redis_conn.hgetall("cart_%d" % user.id)
        selected_dict = redis_conn.smembers("selected_%d" % user.id)

        # 把勾选的商品和数量再包装到一个新的字典
        cart_dict = {}
        for sku_id in selected_dict:
            cart_dict[int(sku_id)] = int(cart_hash_dict[sku_id])

        # 遍历勾选的商品　给每一个商品添加一个count属性
        skus = SKU.objects.filter(id__in=cart_dict.keys())

        for sku in skus:
            sku.count = cart_dict[sku.id]

        # 定义运费
        freight = Decimal("10.00")
        # 序列化时,可以对单个/查询集/列表/字典进行序列化
        data_dict = {"freight": freight, "skus": skus}
        serializer = OrderSettlementSerializer(data_dict)
        return Response(serializer.data)


class CommitOrderView(CreateAPIView, ListAPIView):
    """保存订单"""
    permission_classes = [IsAuthenticated]
    
    # 获取序列化器
    def get_serializer_class(self):
        if self.request.method == 'POST':
            serializer_class = CommitOrderSerializer
        else:
            serializer_class = UserOrderSerializer
        return serializer_class

    # 指定查询集
    def get_queryset(self):
        if self.request.method == 'GET':
            user = self.request.user
            queryset = OrderInfo.objects.filter(user=user)
            return queryset
