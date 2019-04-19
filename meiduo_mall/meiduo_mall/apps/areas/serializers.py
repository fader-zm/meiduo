from rest_framework import serializers

from areas.models import Area


class AreaSerializer(serializers.ModelSerializer):
    # 省的序列化器
    class Meta:
        model = Area
        fields = ["id", "name"]


class SubSerializer(serializers.ModelSerializer):
    """详情视图使用的序列化器"""
    subs = AreaSerializer(many=True)

    class Meta:
        model = Area
        fields = ["id", "name", "subs"]
