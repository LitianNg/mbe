from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

# Register your models here.
from .models import *

admin.site.register(User, UserAdmin)
admin.site.register(Seller)
admin.site.register(Product)
admin.site.register(Order)
admin.site.register(TransactionProductQty)
admin.site.register(Inbound)
admin.site.register(Outbound)