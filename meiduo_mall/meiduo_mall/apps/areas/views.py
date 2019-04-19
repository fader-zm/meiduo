from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView

from .serializers import AreaSerializer, SubSerializer
from .models import Area
from rest_framework.response import Response
from rest_framework.generics import ListAPIView,RetrieveAPIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework_extensions.cache.mixins import CacheResponseMixin


# class AreaListView(APIView):
#     """查询所有的省份"""
#     def get(self,request):
#         # 1.获取指定的查询集
#         qs = Area.objects.filter(parent=None)
#         # 2.创建序列化器 进行序列化
#         serializer = AreaSerializer(qs, many=True)
#         # 3.响应
#         return Response(serializer.data)
#
#
# class AreaDetailView(APIView):
#     """查询单一的省或市"""
#     def get(self,request,pk):
#         # 根据pk找到指定的省份或市
#         try:
#             area = Area.objects.get(id=pk)
#         except Area.DoesNotExist:
#             return  Response({"message":"省份不存在"},status=status.HTTP_404_NOT_FOUND)
#         # 创建序列化器
#         serializer = SubSerializer(area)
#         # 响应
#         return Response(serializer.data)

# class AreaListView(ListAPIView):
#     """查询所有的省份"""
#     serializer_class = AreaSerializer
#     queryset = Area.objects.filter(parent=None)


# class AreaDetailView(RetrieveAPIView):
#     """查询单一的省或市"""
#     serializer_class = SubSerializer
#     queryset = Area.objects.all()

# CacheResponseMixin 只对查所有和查单一进行缓存 缓存到redis中  一定要放在前面
class AreaViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    # 根据行为来判断序列化器和查询集

    pagination_class = None  # 禁用分页

    def get_queryset(self):
        if self.action == "list":
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return AreaSerializer
        else:
            return SubSerializer
