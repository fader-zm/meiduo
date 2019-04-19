from django.shortcuts import render
from rest_framework.views import APIView
from random import randint
from django_redis import get_redis_connection
from meiduo_mall.libs.yuntongxun.sms import CCP
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
import logging

from meiduo_mall.utils.exceptions import logger
from . import constants
from celery_tasks.sms.tasks import send_sms_code
from .captcha.captcha import captcha

logger = logging.getLogger('django')


class SMSCodeView(APIView):
    """短信验证"""
    
    def get(self, request, mobile):
        # 创建redis连接对象
        redis_conn = get_redis_connection("verifications")
        # 先从redis数据库中获取发送标记,判断是否发了  60秒内不能重复发送
        send_flag = redis_conn.get("send_flag_%s" % mobile)
        if send_flag:
            return Response({"message": "手机已经发送验证码"}, status=status.HTTP_400_BAD_REQUEST)
        
        # 没发送过验证码,就生成验证码,并且保存验证码到redis数据库
        sms_code = "%06d" % randint(0, 999999)
        logger.info(sms_code)
        
        # 创建redis管道命令 把多次redis操作装入管道中 一次性执行命令 减少redis的连接操作次数 提升性能
        pl = redis_conn.pipeline()
        # redis保存验证码 有效时间300秒
        # redis_conn.setex(mobile,constants.SMS_CODE_REDIDS_EXPIRES,sms_code)
        pl.setex(mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # 存储一个标记有效时间60秒 判断该手机是否再60秒内发送过验证码
        # redis_conn.setex(mobile,constants.SEND_SMS_CODE_INTERVAL,1)
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)
        # 执行管道
        pl.execute()
        # 利用容联云通讯发送验证码  5分钟
        # CCP().send_template_sms(mobile,[sms_code,constants.SMS_CODE_REDIDS_EXPIRES/60],1)
        # 触发异步任务 将异步任务添加到celery任务队列
        # send_sms_code(mobile,sms_code)  # 普通调用函数
        send_sms_code.delay(mobile, sms_code)  # 触发异步任务
        # 响应
        return Response({"message": "ok"})


class ImageCodeView(APIView):
    def get(self, request, image_code_id):
        image_name, real_image_code, image_data = captcha.generate_captcha()
        print(real_image_code)
        
        redis_conn = get_redis_connection('verifications')
        
        redis_conn.setex('Image_Code_%s' % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, real_image_code)
        
        # 直接返回图片数据可能不能兼容所有浏览器
        # 设置响应头中返回数据格式为：png
        # response.headers['Content-Type'] = 'png/image'
        
        return HttpResponse(image_data)
