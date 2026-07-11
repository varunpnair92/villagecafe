from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, name, phone, role, password=None):
        if not email:
            raise ValueError("Users must have an email address")
        user = self.model(
            email=self.normalize_email(email),
            name=name,
            phone=phone,
            role=role,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, phone, role, password=None):
        user = self.create_user(
            email,
            name=name,
            phone=phone,
            role=role,
            password=password,
        )
        user.is_admin = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=15)
    role = models.CharField(max_length=50)
    
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'phone', 'role']

    def __str__(self):
        return self.email


class Table(models.Model):
    tableNo = models.IntegerField(unique=True)
    status = models.CharField(max_length=50, default="Available")
    seats = models.IntegerField()
    currentOrder = models.ForeignKey(
        'Order', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='current_for_tables'
    )

    def __str__(self):
        return f"Table {self.tableNo} ({self.status})"


class Order(models.Model):
    customerDetails = models.JSONField()  # Store name, phone, guests
    orderStatus = models.CharField(max_length=50)
    orderDate = models.DateTimeField(default=timezone.now)
    bills = models.JSONField()            # Store total, tax, totalWithTax
    items = models.JSONField(default=list) # Array of items
    table = models.ForeignKey(
        'Table', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='orders'
    )
    paymentMethod = models.CharField(max_length=50, null=True, blank=True)
    paymentData = models.JSONField(null=True, blank=True) # razorpay_order_id, razorpay_payment_id

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.orderStatus}"


class Payment(models.Model):
    paymentId = models.CharField(max_length=255, null=True, blank=True)
    orderId = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField()
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=50)
    method = models.CharField(max_length=50, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    contact = models.CharField(max_length=15, null=True, blank=True)
    createdAt = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment {self.paymentId} ({self.status})"


class MenuItem(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    category = models.CharField(max_length=100) # Starters, Main Course, etc.
    icon = models.CharField(max_length=10, default="🍛")
    bgColor = models.CharField(max_length=10, default="#5b45b0")

    def __str__(self):
        return f"{self.name} - ₹{self.price} ({self.category})"
