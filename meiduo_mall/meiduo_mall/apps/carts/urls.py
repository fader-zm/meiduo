from . import views
from django.conf.urls import url

urlpatterns = [
    url(r"carts/$",views.CartView.as_view()),
    url(r"carts/selection/$",views.CartSelectedAll.as_view()),
]