from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator

# Create your models here.

class User(AbstractUser):
    is_seller = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)

class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    name = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=11, null=True)
    email = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    UNIT = (
        ('PCS','PCS'),
        ('BOX','BOX'),
        ('PACK','PACK'),
        ('BOTTLE','BOTTLE'),
        ('OTHER','OTHER'),
    )

    date_created = models.DateTimeField(auto_now_add=True, null=True)
    sku_code = models.CharField(max_length=200, primary_key=True)
    product_name = models.CharField(max_length=200, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, null=True)
    product_quantity = models.PositiveIntegerField(null=True)
    product_price = models.FloatField(validators=[MinValueValidator(0.0)])
    location = models.CharField(max_length=200, null=True)
    rack = models.CharField(max_length=200, null=True)  
    pallet = models.CharField(max_length=200, null=True)
    remarks = models.CharField(max_length=200, null=True, blank=True)


    seller = models.ForeignKey(Seller, to_field='user_id', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.sku_code

class Order(models.Model):
    STATUS = (
        ('Pending','Pending'),
        ('Out of Delivery','Out of Delivery'),
        ('Completed','Completed'),
        ('Rejected','Rejected'),
    )

    order_id = models.CharField(max_length=200, primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    order_quantity = models.PositiveIntegerField(null=True, validators=[MinValueValidator(1)])
    platform = models.CharField(max_length=200, null=True)
    awb = models.CharField(max_length=200, null=True)
    courier = models.CharField(max_length=200, null=True)
    remarks = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=200, choices=STATUS, null=True)

    seller = models.ForeignKey(Seller, null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.order_id

class TransactionProductQty(models.Model):
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    user = models.CharField(max_length=200, null=True)
    action = models.CharField(max_length=200, null=True)
    qty = models.IntegerField(null=True)
    current_qty = models.PositiveIntegerField(null=True)
    reason = models.CharField(max_length=200, null=True)
    record_product = models.CharField(max_length=200, null=True)
    
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)

class Inbound(models.Model):
    STATUS = (
        ('Pending','Pending'),
        ('Approved','Approved'),
        ('Rejected','Rejected'),
    )

    UNIT = (
        ('PCS','PCS'),
        ('BOX','BOX'),
        ('PACK','PACK'),
        ('BOTTLE','BOTTLE'),
        ('OTHER','OTHER'),
    )

    date_created = models.DateTimeField(auto_now_add=True, null=True)
    product_name = models.CharField(max_length=200, null=True)
    sku_code = models.CharField(max_length=200, null=True)
    unit = models.CharField(max_length=200, choices=UNIT, null=True)
    product_quantity = models.IntegerField(null=True)
    product_price = models.FloatField(validators=[MinValueValidator(0.0)])
    remarks = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=200, choices=STATUS, default='Pending')

    seller = models.ForeignKey(Seller, to_field='user_id', null=True, on_delete=models.SET_NULL)

class Outbound(models.Model):
    
    STATUS = (
       ('Pending','Pending'),
       ('Approved', 'Approved'),
        ('Out of Delivery','Out of Delivery'),
        ('Completed','Completed'),
        ('Rejected','Rejected'),
    )

    PLATFORM = (('Shopee', 'Shopee'),
    ('Lazada', 'Lazada'),
    ('Other', 'Other'),
    )

    order_id = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)
    order_quantity = models.PositiveIntegerField(null=True, validators=[MinValueValidator(1)])
    platform = models.CharField(max_length=200, choices=PLATFORM, null=True)
    
    remarks = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=200, choices=STATUS, default='Pending')
    seller = models.ForeignKey(Seller, to_field='user_id', null=True, on_delete=models.SET_NULL)
    product = models.ForeignKey(Product, to_field='sku_code', null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return str(self.product)