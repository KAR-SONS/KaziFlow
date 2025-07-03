from django.db import models
from django.utils import timezone

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, unique=True)  
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # You might use Django's default auth system instead
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class Order(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('debt', 'Debt'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=255, blank=True, null=True)  
    product_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order by {self.user.username} on {self.order_date.strftime('%Y-%m-%d')}"

# models.py
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        return self.quantity * self.price

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)

    def __str__(self):
        return f"Subscription for {self.user.username} ({self.status})"

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tracking_id = models.CharField(max_length=255, unique=True)
    reference = models.CharField(max_length=255)  # phone
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.tracking_id} for {self.user.username} - {self.status}"

class PendingPayment(models.Model):
    user = models.ForeignKey('User', on_delete=models.CASCADE)
    order_id = models.CharField(max_length=255, unique=True)  # This is the Pesapal order UUID
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.order_id}"


def normalize_phone(phone):
    phone = phone.strip().replace("+", "").replace(" ", "")
    if phone.startswith("07") and len(phone) == 10:
        return "254" + phone[1:]
    elif phone.startswith("01") and len(phone) == 10:
        return "254" + phone[1:]
    return phone
