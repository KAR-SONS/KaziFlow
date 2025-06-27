from django import forms
from .models import User, Order

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'phone', 'email', 'password']

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order  # ✅ Correct model
        fields = ['customer_name', 'product_name', 'status', 'total_amount']
