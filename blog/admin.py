from django.contrib import admin

# Register your models here.
from .models import User
from .models import Order
from .models import Subscription
from .models import Payment

admin.site.register(User)
admin.site.register(Order)
admin.site.register(Subscription)
admin.site.register(Payment)

