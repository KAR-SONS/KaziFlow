from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=15, unique=False, default='0712345678')  # Assuming phone numbers are unique
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
    customer_name = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    order_date = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Order by {self.user.username} on {self.order_date.strftime('%Y-%m-%d')}"


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
