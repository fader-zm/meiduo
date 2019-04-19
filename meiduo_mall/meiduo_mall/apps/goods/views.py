from django.shortcuts import render
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from .models import SKU
from .serializer import SKUSerializer

from rest_framework.permissions import IsAuthenticated


class SKUListView(ListAPIView):
    """商品;列表数据查询"""
    serializer_class = SKUSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["create_time", "price", "sales"]

    def get_queryset(self):
        # 如果再当前视图中没有去定义get/post方法,那么就没办法用参数来接受正则组提取出来的url路径参数
        # 此时可以利用视图对象的args 或 kwargs来接收
        category_id = self.kwargs.get("category_id")
        return SKU.objects.filter(is_launched=True, category_id=category_id)


# /orders/
# class UserOrderView(ListAPIView):
#     """用户订单列表获取"""
#     # 认证用户是否登录
#     permission_classes = [IsAuthenticated]
    """
    需要定义序列化器
    前端: 订单创建时间, 订单号, 图片, 描述, 商品价格, 数据, 价格, 总金额, 支付方式, 订单状态
    表: order_info, order_goods, sku
    create_time, order_id, default_image_url, name, price, total_count, total_amount, freight, pay_method, status
    """
    
    # # 指定序列化器
    # serializer_class = UserOrderSerializer
    #
    # # 指定查询集
    # def get_queryset(self):
    #     user = self.request.user
    #     queryset = OrderInfo.objects.filter(user=user)
    #     return queryset
    
    