from django.urls import path
from . import views

urlpatterns = [
   path('', views.home, name='home'),
   path('join', views.join, name='join'),
   path('order', views.order, name='order'),
   path('order_list', views.order_list, name='order_list'),
   path('start_subscription/', views.start_subscription, name='start_subscription'),
   path('pesapal-callback/', views.pesapal_callback, name='pesapal_callback'),
   path('whatsapp/', views.whatsapp_webhook),
   path('mark_as_paid/', views.mark_as_paid, name='mark_as_paid'),
   path('order_receipt/<int:order_id>/', views.order_receipt, name='order_receipt'),
   path('filter_orders/', views.filter_orders, name='filter_orders'),
]
