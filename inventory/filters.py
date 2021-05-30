import django_filters
from django_filters import DateFilter, CharFilter, ModelChoiceFilter
from .models import *


class OrderFilter(django_filters.FilterSet):
    #start_date = DateFilter(field_name="date_created", lookup_expr='gte')
    #end_date = DateFilter(field_name="date_created", lookup_expr='lte')
    
    order_id = CharFilter(field_name='order_id', lookup_expr='icontains')
    

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            # data.setdefault("status", "Pending")  
        super(OrderFilter, self).__init__(data, *args, **kwargs)

    class Meta:
        model = Order
        fields = ['order_id','status']
    

class ProductFilter(django_filters.FilterSet):
    sku_code = CharFilter(field_name='sku_code', lookup_expr='icontains')
    product_name = CharFilter(field_name='product_name', lookup_expr='icontains')
    
    class Meta:
        model = Product
        fields = ['sku_code','product_name','seller']

class LogFilter(django_filters.FilterSet):
    action = CharFilter(field_name='action', lookup_expr='icontains')
    record_product = CharFilter(field_name='record_product', lookup_expr='icontains')

    class Meta:
        model = TransactionProductQty
        fields = ['action','record_product']

class SellerFilter(django_filters.FilterSet):
    name = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model = Seller
        fields = ['name']

class InboundFilter(django_filters.FilterSet):
    product_name = CharFilter(field_name='product_name', lookup_expr='icontains')

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            # data.setdefault("status", "Pending")  
        super(InboundFilter, self).__init__(data, *args, **kwargs)

    class Meta:
        model = Inbound
        fields = ['product_name', 'seller', 'status']

class OutboundFilter(django_filters.FilterSet):
    

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
          #  data.setdefault("status", "Pending")  
        super(OutboundFilter, self).__init__(data, *args, **kwargs)

    class Meta:
        model = Outbound
        fields = ['seller', 'status']