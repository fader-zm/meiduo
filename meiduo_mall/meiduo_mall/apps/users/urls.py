
from rest_framework_jwt.views import obtain_jwt_token
from rest_framework.routers import DefaultRouter
from . import views
from django.conf.urls import url

urlpatterns = [
    # 用户注册
    url(r"^users/$", views.UserView.as_view()),
    # 判断用户名是否注册
    url(r"^usernames/(?P<username>\w{5,20})/count/$", views.UserNameCountView.as_view()),
    # 判断手机号码是否注册
    url(r"^mobiles/(?P<mobile>1[3-9]\d{9})/count/$", views.UserMobileCountView.as_view()),
    # JWT登录  并且帮忙生成token
    # url(r'^authorizations/$', obtain_jwt_token),
    url(r'^authorizations/$', views.UserAuthorizeView.as_view()),
    # 获取个人信息
    url(r'^user/$', views.UserDetailVIew.as_view()),
    # 更新邮箱
    url(r'^email/$', views.EmailView.as_view()),
    # 邮箱激活
    url(r'^emails/verification/$', views.EmailVerifyView.as_view()),
    # 客户浏览记录
    url(r'^browse_histories/$', views.UserBrowserHistoryView.as_view()),
    

]


router = DefaultRouter()
router.register(r'addresses', views.AddressViewSet, base_name='addresses')
urlpatterns += router.urls
