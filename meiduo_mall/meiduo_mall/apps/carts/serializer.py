from rest_framework import serializers
from goods.models import SKU


class CartSerializer(serializers.Serializer):
    """新增和修改操作购物车序列化器"""

    sku_id = serializers.IntegerField(label="商品id", min_value=1)
    count = serializers.IntegerField(label="购买数量")
    selected = serializers.BooleanField(label="商品勾选状态", default=True)

    def validate_sku_id(self, value):
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("sku_id不存在")
        return value


class SKUCartSerializer(serializers.ModelSerializer):
    """查询购物车序列化器"""
    count = serializers.IntegerField(label="购买数量")
    selected = serializers.BooleanField(label="商品勾选状态")

    class Meta:
        model = SKU
        fields = ["id", "name", "price", "default_image_url", "count", "selected"]


class CartDeleteSerializer(serializers.Serializer):
    """删除购物车商品序列化器"""
    sku_id = serializers.IntegerField(label="商品id", min_value=1)

    def validate_sku_id(self, value):
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("sku_id不存在")
        return value


class CartSelectedAllSerializer(serializers.Serializer):
    """购物车全选序列化器"""
    selected = serializers.BooleanField(label="商品是否全选")
