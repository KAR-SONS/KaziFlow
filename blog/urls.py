from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [
   path('', views.landing, name='landing'),
   path('home', views.home, name='home'),
   path('join', views.join, name='join'),
   path('order', views.order, name='order'),
   path('order_list', views.order_list, name='order_list'),
   path('start_subscription/', views.start_subscription, name='start_subscription'),
   path('pesapal-callback/', views.pesapal_callback, name='pesapal_callback'),
   path('whatsapp/', views.whatsapp_webhook),
   path('mark_as_paid/', views.mark_as_paid, name='mark_as_paid'),
   path('order_receipt/<int:order_id>/', views.order_receipt, name='order_receipt'),
   path('filter_orders/', views.filter_orders, name='filter_orders'),
   path('delete_order/', views.delete_order, name='delete_order'),
   path('admin/', admin.site.urls),
   path('referral_report/<int:referrer_id>/', views.referral_report, name='referral_report'),
   path('referrer_links/<int:referrer_id>/', views.referrer_links, name='referrer_links'),

]
