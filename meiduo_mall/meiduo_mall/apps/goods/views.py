from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.serializer import DetailComments
from .models import SKU
from .serializer import SKUSerializer
from orders.models import OrderGoods


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


class SKUCommentViewSet(APIView):
    """评论展示"""
    
    def get(self, request, sku_id):
        user = request.user
        try:
            ordergood = OrderGoods.objects.filter(sku_id=sku_id, is_commented=1)
        except SKU.DoesNotExist:
            return Response({'message': '商品信息有误'}, status=status.HTTP_400_BAD_REQUEST)
        serializers = DetailComments(data=ordergood, many=True)
        serializers.is_valid()
        return Response(data=serializers.data, status=status.HTTP_200_OK)
