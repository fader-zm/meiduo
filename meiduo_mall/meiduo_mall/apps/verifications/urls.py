from django.conf.urls import url

from . import views

urlpatterns = [
    url(r"^sms_codes/(?P<mobile>1[3-9]\d{9})/$", views.SMSCodeView.as_view()),
    # 图形验证码接口
    url(r'^image_codes/(.+)/$', views.ImageCodeView.as_view()),

]
