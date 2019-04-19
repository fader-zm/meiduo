from rest_framework.routers import DefaultRouter
from . import views
from django.conf.urls import url

urlpatterns = [
    # 用户注册
    # url(r"^areas/$", views.AreaListView.as_view()),
    # url(r"^areas/(?P<pk>\d+)/$", views.AreaDetailView.as_view()),
]

router = DefaultRouter()
# 如果视图集中没有给queryset类属性指定查询集,就必须给base_name传参数,如果不传默认取queryset中指定的查询集模型名小写作为路由别名前缀
router.register(r"areas", views.AreaViewSet, base_name="area")
urlpatterns += router.urls
