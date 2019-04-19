from django_redis import get_redis_connection
from rest_framework import serializers

from .models import OAuthQQUser, OAuthSinaUser
from users.models import User
from .utils import check_save_user_token


class QQAuthUserSerializer(serializers.Serializer):
    """openid绑定用户的序列化器"""
    # 4个字段直接自己定义  mobile  password sms_code  access_token
    access_token = serializers.CharField(label='操作凭证')
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')
    password = serializers.CharField(label='密码', max_length=20, min_length=8)
    sms_code = serializers.CharField(label='短信验证码')
    
    def validate(self, attrs):
        # 把加密的openid取出来 解密
        access_token = attrs.pop("access_token")
        openid = check_save_user_token(access_token)
        if openid is None:
            raise serializers.ValidationError("openid无效")
        #  把解密的openid重新添加到attr字典中
        attrs["openid"] = openid
        
        # 校验验证码
        redis_conn = get_redis_connection("verifications")
        mobile = attrs["mobile"]
        real_sms_code = redis_conn.get(mobile)
        if real_sms_code is None or attrs["sms_code"] != real_sms_code.decode():
            raise serializers.ValidationError("验证码错误")
        
        # 用手机号码查询User表 看是否用户存在,存在则再判断密码是否正确
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNOtExist:
            pass
        else:
            if user.check_password(attrs["password"]) is False:
                raise serializers.ValidationError("密码错误")
            else:
                attrs["user"] = user
        
        return attrs
    
    def create(self, validated_data):
        # 获取validated_data中的user
        user = validated_data.get("user")
        # 如果没有user 新建一个user
        if user is None:
            user = User(
                username=validated_data.get("mobile"),
                mobile=validated_data.get("mobile"),
            )
            user.set_password(validated_data.get("password"))
            user.save()
        # 把openid和user绑定
        OAuthQQUser.objects.create(
            openid=validated_data.get("openid"),
            user=user
            # user_id = user.id
        )
        # 返回user
        return user


class SinaAuthUserViewSerializer(serializers.Serializer):
    # mobile  password  sms_code  access_token
    access_token = serializers.CharField(label='操作凭证')
    mobile = serializers.RegexField(label='手机号', regex=r'^1[3-9]\d{9}$')
    password = serializers.CharField(label='密码', max_length=20, min_length=8)
    sms_code = serializers.CharField(label='短信验证码')
    
    def validate(self, attrs):
        
        access_token = attrs.get('access_token')
        # print(access_token)
        if not access_token:
            raise serializers.ValidationError('access_token无效')
        
        redis_conn = get_redis_connection('verifications')
        mobile = attrs['mobile']
        real_sms_code = redis_conn.get(mobile)
        
        if real_sms_code is None or attrs['sms_code'] != real_sms_code.decode():
            raise serializers.ValidationError('验证码错误')
        
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            pass
        else:
            if user.check_password(attrs['password']) is False:
                raise serializers.ValidationError('密码错误')
            else:
                attrs['user'] = user
        
        return attrs
    
    def create(self, validated_data):
        
        user = validated_data.get('user')
        if user is None:
            user = User(
                username=validated_data.get('mobile'),
                mobile=validated_data.get('mobile'),
            )
            user.set_password(validated_data.get('password'))
            user.save()
        
        OAuthSinaUser.objects.create(
            access_token=validated_data.get('access_token'),
            user=user,
        )
        
        return user
