from django.conf.urls import url
from . import views

urlpatterns = [
    url(r"^categories/(?P<category_id>\d+)/skus/", views.SKUListView.as_view()),
    # 评论展示
    url(r'^skus/(?P<sku_id>\d+)/comments/$', views.SKUCommentViewSet.as_view()),
]
