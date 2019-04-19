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
    
    # 验证用户和图片验证码
    # http://api.meiduo.site:8000/accounts/18791920371/sms/token/?text=thby&image_code_id=2b1281c2-1555-4b28-b029-cab24ea62fcf
    url(r'^accounts/(?P<username>\w{5,20})/sms/token/$', views.VerifyImageCode.as_view()),
    # 发送短信验证码
    url(r'^sms_codes/$', views.SendSmsCode.as_view()),
    # 验证短信验证码
    url(r'^accounts/(?P<username>\w{5,20})/password/token/$', views.VrerifySmsCode.as_view()),
    # 忘记密码
    url(r'^users/(?P<user_id>\d+)/password/$', views.ModifyPassword.as_view()),
    # 修改密码
    url(r'^users/(?P<user_id>\d+)/new_password/$', views.ChangePassword.as_view())
]

router = DefaultRouter()
router.register(r'addresses', views.AddressViewSet, base_name='addresses')
urlpatterns += router.urls
