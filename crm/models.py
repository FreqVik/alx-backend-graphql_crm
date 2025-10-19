from django.db import models
from django.utils import timezone


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.email})"


class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} - ₦{self.price} (Stock: {self.stock})"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    products = models.ManyToManyField(Product, related_name="orders")
    order_date = models.DateTimeField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        """
        Automatically calculate total_amount before saving.
        """
        if self.pk:  # Only if order already exists and products set
            self.total_amount = sum(p.price for p in self.products.all())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} by {self.customer.name} - Total: ₦{self.total_amount}"
