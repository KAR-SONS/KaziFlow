from django.urls import path
from . import views

urlpatterns = [
   path('', views.home, name='home'),
   path('join', views.join, name='join'),
   path('order', views.order, name='order'),
   path('order_list', views.order_list, name='order_list'),
   path('subscription', views.subscription, name='subscription'),
   path('whatsapp/', views.whatsapp_webhook),
]
