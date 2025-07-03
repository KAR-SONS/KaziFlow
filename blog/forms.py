from django import forms
from .models import User, Order, OrderItem
from django.forms import modelformset_factory

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'phone', 'email', 'password']

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order  # ✅ Correct model
        fields = ['customer_name']
OrderItemFormSet = modelformset_factory(OrderItem, fields=('product_name', 'quantity', 'price'), extra=1, can_delete=True)