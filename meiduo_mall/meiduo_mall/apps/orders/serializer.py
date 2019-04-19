from rest_framework import serializers
from goods.models import SKU
from .models import OrderInfo, OrderGoods
from django.utils.datetime_safe import datetime
from decimal import Decimal
from django_redis import get_redis_connection
from django.db import transaction


class CartSKUSerializer(serializers.ModelSerializer):
    """订单中的商品序列化器"""
    count = serializers.IntegerField(label="商品购买数量")
    
    class Meta:
        model = SKU
        fields = ["id", "name", "default_image_url", "price", "count"]


class OrderSettlementSerializer(serializers.Serializer):
    """订单序列化器"""
    skus = CartSKUSerializer(many=True)
    freight = serializers.DecimalField(label="运费", max_digits=10, decimal_places=2)


class CommitOrderSerializer(serializers.ModelSerializer):
    """保存订单序列器"""
    
    class Meta:
        model = OrderInfo
        fields = ['address', 'pay_method', 'order_id']
        read_only_fields = ['order_id']
        extra_kwargs = {
            "address": {"write_only": True},
            "pay_method": {"write_only": True}
        }
    
    def create(self, validated_data):
        """保存订单"""
        # 获取当前保存订单需要的信息
        user = self.context["request"].user
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + "%09d" % user.id
        address = validated_data.get("address")
        pay_method = validated_data.get("pay_method")
        
        # 根据付款方式 来决定订单状态
        status = OrderInfo.ORDER_STATUS_ENUM["UNPAID"] if pay_method == OrderInfo.PAY_METHODS_ENUM["ALIPAY"] else \
            OrderInfo.ORDER_STATUS_ENUM["UNSEND"]
        
        # 手动开启事物
        with transaction.atomic():
            save_point = transaction.savepoint()  # 创建事物保存点
            try:
                # 保存订单基本信息
                orderinfo = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal("0.00"),
                    freight=Decimal("10.00"),
                    pay_method=pay_method,
                    status=status
                )
                
                # 从redis中读取购物车中被选中的商品信息
                redis_conn = get_redis_connection("cart")
                cart_dict_redis = redis_conn.hgetall("cart_%d" % user.id)
                selected_redis = redis_conn.smembers("selected_%d" % user.id)
                
                for sku_id_bytes in selected_redis:
                    while True:  # 让客户可以参与多次抢单  直到库存真的不足才停止
                        sku = SKU.objects.get(id=sku_id_bytes)
                        # 获取当前商品的购买数量
                        buy_count = int(cart_dict_redis[sku_id_bytes])
                        # 把当前sku商品的原库存和原销量取出来
                        origin_sales = sku.sales
                        origin_stock = sku.stock
                        if origin_stock < buy_count:
                            raise serializers.ValidationError("库存不足")
                        # 计算新的库存和销量 并保存
                        new_sales = origin_sales + buy_count
                        new_stock = origin_stock - buy_count
                        
                        # sku.sales = new_sales
                        # sku.stock = new_stock
                        # sku.save()
                        result = SKU.objects.filter(stock=origin_stock, id=sku_id_bytes).update(stock=new_stock,
                                                                                                sales=new_sales)
                        if result == 0:  # 如果没有修改成功,说明处于资源抢夺状态 有人先下单
                            continue
                        
                        # 修改SPU的销量 利用外键goods
                        spu = sku.goods
                        spu.sales += buy_count
                        spu.save()
                        
                        # 保存订单商品信息
                        OrderGoods.objects.create(
                            order=orderinfo,
                            sku=sku,
                            count=buy_count,
                            price=sku.price,
                        )
                        
                        # 累加计算商品数量和总价
                        orderinfo.total_count += buy_count
                        orderinfo.total_amount += (sku.price * buy_count)
                        break  # 当前客户购买该商品下单成功 停止抢购,进行下一个商品的购买
                
                # 最后加入运费 只需要加一次
                orderinfo.total_amount += orderinfo.freight
                orderinfo.save()
                transaction.savepoint_commit(save_point)
            except Exception as e:
                # 进行暴力回滚
                print(e)
                transaction.savepoint_rollback(save_point)
                
                raise serializers.ValidationError("库存不足")
        
        # 清空购物车中已买的商品
        pl = redis_conn.pipeline()
        pl.hdel("cart_%d" % user.id, *selected_redis)
        pl.srem("selected_%d" % user.id, *selected_redis)
        pl.execute()
        # 返回订单模型
        return orderinfo


class SKUOrderSerializers(serializers.ModelSerializer):
    """sku商品order序列化器"""
    
    class Meta:
        model = SKU
        fields = ["name", "price", "default_image_url"]


class OrderGoodsSerializer(serializers.ModelSerializer):
    """订单商品序列化器"""
    sku = SKUOrderSerializers()
    
    class Meta:
        model = OrderGoods
        fields = ["count", "price", "sku"]


class UserOrderSerializer(serializers.ModelSerializer):
    """用户订单获取序列化器"""
    skus = OrderGoodsSerializer(many=True)
    create_time = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S')
    
    class Meta:
        model = OrderInfo
        fields = ["order_id", "create_time", "total_amount", "freight", "pay_method", "status", "skus"]
    

