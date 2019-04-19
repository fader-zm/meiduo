from itsdangerous import TimedJSONWebSignatureSerializer as TJSSerializer, BadData
from django.conf import settings


def generate_save_user_token(openid):
    """对openid进行加密"""
    serializer = TJSSerializer(settings.SECRET_KEY,600)
    data = {"openid":openid}
    # dumps进行加密  data是一个字典类型数据  返回bytes类型数据 要解码
    token = serializer.dumps(data)
    return token.decode()


def check_save_user_token(access_token):
    """传入加密的openid进行解密并返回"""
    serializer = TJSSerializer(settings.SECRET_KEY, 600)
    try:
        data = serializer.loads(access_token)
    except BadData:
        return None
    else:
        return data.get("openid")

