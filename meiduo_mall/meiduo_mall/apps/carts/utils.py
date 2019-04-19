import base64, pickle
from django_redis import get_redis_connection


def merge_cart(request, user, response):
    """合并购物车数据"""
    # 获取cookie购物车数据
    cookie_str = request.COOKIES.get("cart")

    # 如果cookie中没有购物车数据 直接返回
    if not cookie_str:
        return

    # 如果有购物车数据 取出cookie 转成字典 添加到redis中
    cart_dict = pickle.loads(base64.b64decode(cookie_str.encode()))

    # 连接redis 遍历cookie字典  把sku_id 和count往hash字典存储, 把selected存储到set中
    redis_conn = get_redis_connection("cart")
    pl = redis_conn.pipeline()

    for sku_id in cart_dict:
        count = cart_dict[sku_id]["count"]
        pl.hset("cart_%d" % user.id, sku_id, count)
        # 判断当前cookie中商品是否勾选  如果勾选 直接把勾选商品的sku_id加到set中
        if cart_dict[sku_id]["selected"]:
            pl.sadd("selected_%d" % user.id, sku_id)

    pl.execute()
    # 删除cookie
    response.delete_cookie("cart")
