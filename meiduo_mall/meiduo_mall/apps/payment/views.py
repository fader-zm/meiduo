from alipay import AliPay
from django.shortcuts import render
from rest_framework.views import APIView
from orders.models import OrderInfo
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import os
from .models import Payment


class PaymentVIew(APIView):
    """生成支付连接"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, order_id):
        # 获取当前的请求用户对象
        user = request.user
        # 根据订单号 来校验订单的有效性
        try:
            order_model = OrderInfo.objects.get(order_id=order_id, user=user,
                                                status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"])
        except OrderInfo.DoesNotExist:
            return Response({"message": "订单不存在"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建alipay支付对象
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            # 指定应用自己的私钥的绝对路径
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            # 指定alipay公钥的绝对路径 验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),
            sign_type="RSA2",  # 加密方式RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )
        
        # 调用SDK的方法得到支付链接后面的查询参数  拼接支付链接
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单编号
            total_amount=str(order_model.total_amount),  # 不能识别decimal 要转换类型
            subject="美多商城%s" % order_id,  # 标题
            return_url="http://www.meiduo.site:8080/pay_success.html"  # 支付成功后回调的url
        )
        
        alipay_url = settings.ALIPAY_URL + "?" + order_string
        return Response({'alipay_url': alipay_url})


class PaymentStatusView(APIView):
    """修改订单状态,保存支付宝交易号"""
    
    def put(self, request):
        # 获取前端以查询字符串方式传入的数据
        query_dict = request.query_params
        # 需要把query_dict转成字典 把sign部分移除 再进行验证
        data = query_dict.dict()
        sign = data.pop("sign")
        
        # 创建alipay对象,然后调用verify方法进行验证 是否是支付宝回传的
        alipay = AliPay(
            appid=settings.ALIPAY_APPID,
            app_notify_url=None,  # 默认回调url
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "keys/app_private_key.pem"),
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "keys/alipay_public_key.pem"),  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            sign_type="RSA2",  # 加密方式RSA2
            debug=settings.ALIPAY_DEBUG  # 默认False
        )
        
        if alipay.verify(data, sign):
            # 取出美多商城订单编号和支付宝交易号   把2个编号绑定保存到MySQL表payment
            order_id = data.get("out_trade_no")
            trade_no = data.get("trade_no")
            Payment.objects.create(
                order_id=order_id,
                trade_id=trade_no
            )
            # 修改支付成功的订单状态   乐观锁
            OrderInfo.objects.filter(order_id=order_id, status=OrderInfo.ORDER_STATUS_ENUM["UNPAID"]).update(
                status=OrderInfo.ORDER_STATUS_ENUM["UNSEND"])
        else:
            return Response({"meassage": "非法请求"}, status=status.HTTP_403_FORBIDDEN)
        
        # 把支付宝交易返回前端
        return Response({"trade_id": trade_no})
