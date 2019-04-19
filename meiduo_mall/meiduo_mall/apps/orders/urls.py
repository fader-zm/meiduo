from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^orders/settlement/$", views.OrderSettlementView.as_view()),
    url(r"^orders/$", views.CommitOrderView.as_view()),
    
    # 订单商品评论路由
    url(r'^orders/(?P<order_id>\d+)/comments/$', views.GoodsCommentView.as_view()),
    url(r'^orders/(?P<order_id>\d+)/uncommentgoods/$', views.UncommentGoodsView.as_view()),

]
