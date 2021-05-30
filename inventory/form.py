from django.forms import ModelForm
from django import forms
from .models import *
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction

class CreateSellerForm(UserCreationForm):
    name = forms.CharField(label='Name', max_length=200)
    phone = forms.CharField(label='Phone', max_length=11)
    email = forms.CharField(label='Email', max_length=200)
    
    class Meta(UserCreationForm.Meta):
        model = User
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(CreateSellerForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
    
    @transaction.atomic
    def save(self):
        user = super().save(commit=False)
        user.is_seller = True
        user.email = self.cleaned_data['email']
        user.save()
        seller = Seller.objects.create(user=user)
        # seller.user = user
        # print(seller.name)
        # print("========================================================")
        seller.name = self.cleaned_data['name']
        seller.phone = self.cleaned_data['phone']
        seller.email = self.cleaned_data['email']
        # print(self.cleaned_data['name'])
        # print(seller.name)
        # print("========================================================")
        # print(seller)
        # print("========================================================")
        # print(self.cleaned_data)
        # print("========================================================")
        seller.save()
        return user

class OrderForm(ModelForm):
    class Meta:
        model = Order
        fields = '__all__'
        exclude = ('seller',)
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(OrderForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class UpdateOrderForm(ModelForm):
    class Meta:
        model = Order
        fields = ['status']

class SellerForm(ModelForm):
    class Meta:
        model = Seller
        fields = '__all__'
        exclude = ('user',)
    
    @transaction.atomic
    def save(self):
        self.instance.save()
        user = User.objects.get(id=self.instance.user_id)
        user.email = self.instance.email
        user.save()
        return user
    
class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
    
    def __init__(self, *args,**kwargs):
        kwargs.setdefault('label_suffix', '')
        super(ProductForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
        
class EditProductQtyForm(ModelForm):
    class Meta:
        #model = Product
        #fields = ['product_quantity']
        model = TransactionProductQty
        fields = ['qty', 'reason',]

class UpdateProductForm(ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        exclude = ('sku_code',)     

class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs) 

class InboundForm(ModelForm):
    class Meta:
        model = Inbound
        fields = ['product_quantity', 'remarks',]
    
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    
    field_order = ['product', 'product_quantity']

    def __init__(self, *args, sellerId, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(InboundForm, self).__init__(*args, **kwargs)
        self.fields['product'] = forms.ModelChoiceField(queryset=Product.objects.filter(seller_id=sellerId))
        self.fields['product'].label_from_instance = lambda obj: "%s" % obj.product_name
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class NpInboundForm(ModelForm):
    class Meta:
        model = Inbound
        fields = '__all__'
        exclude = ('date_created', 'sku_code', 'status', 'seller',)
    
    def __init__(self, *args,**kwargs):
        kwargs.setdefault('label_suffix', '')
        super(NpInboundForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class UpdateNpInboundForm(ModelForm):
    class Meta:
        model = Product
        fields = ['sku_code', 'location', 'rack', 'pallet', 'remarks']
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(UpdateNpInboundForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class OutboundForm(ModelForm):
    class Meta:
        model = Outbound
        fields = ['order_quantity', 'platform', 'remarks',]
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    field_order = ['product', 'order_quantity']

    def __init__(self, *args, sellerId, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(OutboundForm, self).__init__(*args, **kwargs)
        self.fields['product'] = forms.ModelChoiceField(queryset=Product.objects.filter(seller_id=sellerId))
        self.fields['product'].label_from_instance = lambda obj: "%s" % obj.product_name
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

class ApproveOutboundForm(ModelForm):
    class Meta:
        model =  Order
        fields = ['order_id', 'awb', 'courier', 'remarks']
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')  
        super(ApproveOutboundForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'