from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^categories/(?P<category_id>\d+)/skus/", views.SKUListView.as_view()),
    # 用户订单列表获取
    # url(r'^orders/$', views.UserOrderView.as_view(), ),
]
