from . import views
from django.conf.urls import url

urlpatterns = [
    url(r"^qq/authorization/$", views.QQOauthURLView.as_view()),
    url(r"^qq/user/$", views.QQAuthUserView.as_view()),
    
    # 新浪微博第三方登录
    # http://api.meiduo.site:8000/oauth/sina/authorization/?state=/
    url(r'^sina/authorization/$', views.SinaOauthURLView.as_view()),
    # http://api.meiduo.site:8000/oauth/sina/user/?code=e04a1ab5e7bd749e4789aaa538e9b6fc
    url(r'^sina/user/', views.SinaAuthUserView.as_view()),
]
