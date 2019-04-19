from rest_framework import serializers
from .models import User, Address
import re
from django_redis import get_redis_connection
from rest_framework_jwt.settings import api_settings
from celery_tasks.email.tasks import send_verify_email
from goods.models import SKU



class CreateUserSerializer(serializers.ModelSerializer):
    """序列化器"""
    # User模型中可以映射过来的字段 'id' 'username', 'password', 'mobile'
    # 序列化器的所有字段  'id' 'username', 'password', 'mobile' 'password2', 'sms_code', 'allow'
    # 序列化器要校验的字段(前端传入的字段)  'username', 'password', 'password2', 'mobile', 'sms_code', 'allow'

    # 需要反序列化(保存到数据库用户信息)  'username', 'password', 'mobile'
    # 需要序列化的字段(返回前端的信息)   'id', 'username', 'mobile','token'

    password2 = serializers.CharField(label="确认密码", write_only=True)
    sms_code = serializers.CharField(label="验证码", write_only=True)
    allow = serializers.CharField(label="同意协议", write_only=True)
    token = serializers.CharField(label="token", read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'password2', 'mobile', 'sms_code', 'allow', 'token']
        # 修改字段选项
        extra_kwargs = {
            "username": {
                "min_length": 5,
                "max_length": 20,
                "error_messages": {
                    "min_length": "仅仅允许5-20个字符长度的用户名",
                    "max_length": "仅仅允许5-20个字符长度的用户名"}
            },
            "password": {
                "write_only": True,
                "min_length": 8,
                "max_length": 20,
                "error_messages": {
                    "min_length": "仅仅允许8-20个字符长度的密码",
                    "max_length": "仅仅允许8-20个字符长度的密码"}
            },

        }

    # 单独对手机号码进行校验
    def validate_mobile(self, value):
        """校验手机号码"""
        if not re.match(r"1[3-9]\d{9}$", value):
            raise serializers.ValidationError("手机号码错误")
        return value

    # 单独对是否同意协议进行校验
    def validate_allow(self, value):
        """是否同意协议 """
        if value != "true":
            raise serializers.ValidationError("请同意用户协议")
        return value

    # 校验2个密码是否一样 校验验证码是否正确
    def validate(self, attrs):
        # 校验2个密码是否一致
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError("2此输入的密码不一致,重新输入")

        # 校验验证码
        redis_conn = get_redis_connection("verifications")
        mobile = attrs["mobile"]
        real_sms_code = redis_conn.get(mobile)
        # 验证码5分钟过期 或者验证码填写错误 则返回错误
        # 向redis存储数据时都是以字符串进行存储的  但是取出来是bytes类型的  需要解码进行比较
        if real_sms_code is None or attrs["sms_code"] != real_sms_code.decode():
            raise serializers.ValidationError("验证码错误")
        return attrs

    def create(self, validated_data):
        # password2 sms_code  allow 这3个是不需要保存到用户数据库的  需要删除该字段再保存到数据库
        del validated_data["password2"]  # 没有返回值的
        del validated_data["sms_code"]
        del validated_data["allow"]
        # 先取出密码  再删除  不是保存到数据库中
        password = validated_data.pop("password")
        # 创建用户模型对象 给模型中的 username和mobile属性赋值
        user = User(**validated_data)
        # 把密码加密后再赋值给user的password属性   set_password是user对象的方法
        user.set_password(password)
        user.save()

        # 引用jwt中的叫jwt_payload_handler函数(生成payload)
        jwt_payload_handler = api_settings.JWT_PAYLOAD_HANDLER
        jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER  # 函数引用 生成jwt

        payload = jwt_payload_handler(user)  # 根据user生成用户相关的载荷信息
        token = jwt_encode_handler(payload)  # 传入载荷生成完整的jwt

        user.token = token
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'mobile', 'email', 'email_active']


class EmailSerializer(serializers.ModelSerializer):
    """跟新邮箱序列化器"""

    class Meta:
        model = User
        fields = ["id", "email"]
        # 映射古来的email字段required默认是false
        extra_kwargs = {
            "email": {"required": True}
        }

    def update(self, instance, validated_data):
        """重写此方法不是为了修改  是为了激活邮箱"""
        instance.email = validated_data.get("email")
        instance.save()

        # 生成验证连接
        verify_url = instance.generate_email_verify_url()
        # 发送验证邮件
        send_verify_email.delay(instance.email, verify_url)
        return instance


class UserAddressSerializer(serializers.ModelSerializer):
    """ ⽤用户地址序列列化器器 """
    province = serializers.StringRelatedField(read_only=True)
    city = serializers.StringRelatedField(read_only=True)
    district = serializers.StringRelatedField(read_only=True)
    province_id = serializers.IntegerField(label='省ID', required=True)
    city_id = serializers.IntegerField(label='市ID', required=True)
    district_id = serializers.IntegerField(label='区ID', required=True)

    class Meta:
        model = Address
        exclude = ('user', 'is_deleted', 'create_time', 'update_time')

    def validate_mobile(self, value):
        """  验证⼿手机号  """
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError('⼿手机号格式错误')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return Address.objects.create(**validated_data)


class AddressTitleSerializer(serializers.ModelSerializer):
    """
    地址标题
    """

    class Meta:
        model = Address
        fields = ('title',)


class UserBrowserHistorySerializer(serializers.Serializer):
    """"保存商品浏览记录的序列化器"""
    sku_id = serializers.IntegerField(label="商品sku_id", min_value=1)

    def validated_sku_id(self, value):
        """单独对sku_id进行校验"""
        try:
            SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError("sku_id不存在")
        return value

    def create(self, validated_data):
        sku_id = validated_data.get("sku_id")
        user = self.context["request"].user
        redis_conn = get_redis_connection("history")
        # 创建redis的管道
        pl = redis_conn.pipeline()
        # 去重
        pl.lrem("history_%d" % user.id, 0, sku_id)
        # 添加到表头
        pl.lpush("history_%d" % user.id, sku_id)
        # 截取列表前面的5个
        pl.ltrim("history_%d" % user.id, 0, 4)
        # 执行
        pl.execute()
        return validated_data


class SKUSerializer(serializers.ModelSerializer):
    """sku商品序列化器"""

    class Meta:
        mode = SKU
        fields = ["id", "name", "price", "default_image_url", "comments"]
        


