from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.db.models import Sum
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import SetPasswordForm

#for create multiple form within one form
from django.forms import inlineformset_factory,formset_factory 
# for PDF
from io import BytesIO
from django.template.loader import get_template
from django.views import View
from xhtml2pdf import pisa
# Create your views here.
from .models import *
from .form import *
from .filters import *
from .helper import *
from .decorators import *

@custom_login_required
def home(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            page = request.GET.get('page', 1)

            orders = Order.objects.all()

            # paginate results
            products = paginate(Product.objects.all(), page);

            sum_stock = Product.objects.aggregate(Sum('product_quantity'))
            total_stock = sum_stock['product_quantity__sum']
            delivered = orders.filter(status='Out of Delivery').count()
            pending = orders.filter(status='Pending').count()

            context = {'stock': total_stock, 'delivered': delivered, 'pending': pending, 'products': products, 'nbar': 'home'}
        else:
            page = request.GET.get('page', 1)

            orders = Order.objects.filter(seller_id=request.user.id)

            # paginate results
            products = paginate(Product.objects.filter(seller_id=request.user.id), page)

            sum_stock = Product.objects.filter(seller_id=request.user.id).aggregate(Sum('product_quantity'))
            total_stock = sum_stock['product_quantity__sum']
            delivered = orders.filter(status='Out of Delivery').count()
            pending = orders.filter(status='Pending').count()

            context = {'stock': total_stock, 'delivered': delivered, 'pending': pending, 'products': products, 'nbar': 'home'}
        return render(request, 'inventory/home.html', context)
    else:
        return redirect('login/')

@custom_login_required
@admin_required
def products(request):
    products = Product.objects.all()
    orders = Order.objects.all()

    myFilter = ProductFilter(request.GET, queryset=products)
    products = myFilter.qs
    
    #check if the get attributes exist, if yes, assign it to be passed to the hidden form
    sku_code = request.GET['sku_code'] if (request.method == 'GET' and 'sku_code' in request.GET) else ''
    product_name = request.GET['product_name'] if (request.method == 'GET' and 'product_name' in request.GET) else ''
    seller = request.GET['seller'] if (request.method == 'GET' and 'seller' in request.GET) else ''

    # paginate results
    page = request.GET.get('page', 1)
    products = paginate(products, page);

    context = {
                'products': products, 
                'myFilter': myFilter,
                'orders': orders, 
                'nbar': 'products', 
                'sku_code': sku_code,
                'product_name': product_name,
                'seller': seller
                }

    return render(request, 'inventory/products.html', context)

@custom_login_required
@admin_required
def orders(request):
    orders = Order.objects.all()

    myFilter = OrderFilter(request.GET, queryset=orders)
    orders = myFilter.qs
    
    #check if the get attributes exist, if yes, assign it to be passed to the hidden form
    order_id = request.GET['order_id'] if (request.method == 'GET' and 'order_id' in request.GET) else ''
    status = request.GET['status'] if (request.method == 'GET' and 'status' in request.GET) else ''

    # paginate results
    page = request.GET.get('page', 1)
    orders = paginate(orders, page);

    context = {
                'orders': orders, 
                'myFilter': myFilter, 
                'nbar': 'orders', 
                'order_id': order_id,
                'status': status
                }
    return render(request, 'inventory/orders.html', context)

@custom_login_required
@admin_required
def seller_order(request, pk):
    seller = Seller.objects.get(user_id=pk)
    orders = seller.order_set.all()
    order_count = orders.count()

    myFilter = OrderFilter(request.GET, queryset=orders)
    orders = myFilter.qs

    context = {'seller': seller, 'orders': orders,
               'order_count': order_count, 'myFilter': myFilter, 'nbar': 'seller'}
    return render(request, 'inventory/seller_order.html', context)

@custom_login_required
@admin_required
def seller(request):
    sellers = Seller.objects.all()

    myFilter = SellerFilter(request.GET, queryset=sellers)
    sellers = myFilter.qs

    #check if the get attributes exist, if yes, assign it to be passed to the hidden form
    name = request.GET['name'] if (request.method == 'GET' and 'name' in request.GET) else ''

    # paginate results
    page = request.GET.get('page', 1)
    sellers = paginate(sellers, page);

    context = {
        'sellers': sellers,
        'myFilter': myFilter,
        'nbar': 'seller',
        'name': name,
        }
    return render(request, 'inventory/seller.html', context)

@custom_login_required
@admin_required
def createOrder(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    OrderFormSet = formset_factory(OrderForm,extra=form_num,can_delete=True)
    formset = OrderFormSet()

    order = Order.objects.all()
    if request.method == "POST":
        formset = OrderFormSet(request.POST)

        if formset.is_valid():
            order_exist = False
            qty_accept = True
            products_dict = {}

            # ignore deleted, check order exist, check quantity more than stock
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_order = form.cleaned_data.get("order_id")
                    if input_order is not None:
                        order = Order.objects.filter(order_id=input_order).count()

                        #if order_id is found in db, give error
                        if order > 0:
                            messages.warning(request, f"This ID already exists. Please use a different Order ID.", extra_tags="Error for Order ID: "+input_order)
                            order_exist = True
                        else:
                            input_quantity = form.cleaned_data.get("order_quantity")
                            input_code = form.cleaned_data.get("product")
                            
                            if input_code in products_dict:
                                temp_qty = products_dict[input_code] + input_quantity
                                products_dict.update({input_code:temp_qty})
                            
                            else:
                                products_dict[input_code] = input_quantity

                        # if order_id is not found in db and there are products information in the dict
                        if not order_exist and bool(products_dict):
                            for code,qty in products_dict.items():
                                product = Product.objects.get(sku_code=code)

                                if qty <= product.product_quantity:
                                    print("Valid!!!!")
                                
                                else:
                                    print("Invalid!!!!!!!")
                                    messages.warning(request, f"The quantity specified in the order for product {code}, is more than the existing stock in the inventory. Make sure the quantity specified is correct or update the stock info for the product {code}.", extra_tags="Error for Order ID: "+input_order)
                                    qty_accept = False
                        
            #if no errors, save order information into db, update product stock information, log results, then redirect to orders
            if not order_exist and qty_accept:
                for form in formset:
                    input_order = form.cleaned_data.get("order_id")
                    if input_order is not None:
                        input_code = form.cleaned_data.get("product")
                        input_quantity = form.cleaned_data.get("order_quantity")
                        input_platform = form.cleaned_data.get("platform")
                        print(input_code)
                        print(input_order)
                        products = Product.objects.get(sku_code=input_code)
                        products.product_quantity -= input_quantity
                        products.save()
                        form = form.save(commit=False)
                        form.seller = products.seller
                        form.save()
                        
                        new_outbound = Outbound(
                            order_id = input_order,
                            order_quantity = input_quantity,
                            platform = input_platform,
                            remarks = f'Admin create new order, Order Id: {input_order}',
                            status = "Approved",
                            seller = form.seller,
                            product = input_code,
                        )
                        new_outbound.save()

                        new_log = TransactionProductQty(
                            user=request.user,
                            action="Create",
                            qty=input_quantity,
                            current_qty=products.product_quantity,
                            record_product=input_code,
                            reason="Auto-Generate: New Order Created"
                        )
                        new_log.save()
                        TransactionProductQty.objects.filter(id=new_log.id).update(product=input_code)
                    
                return redirect('/orders')

        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset, 
        'nbar': 'orders'}
    return render(request, 'inventory/create_form.html', context)

@custom_login_required
@admin_required
def updateOrder(request, pk):
    order = Order.objects.get(order_id=pk)
    form = UpdateOrderForm(instance=order)

    if request.method == "POST":
        form = UpdateOrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            status = form.cleaned_data["status"]
            if status == "Pending":
                Outbound.objects.filter(order_id=order.order_id).update(status="Approved")
            else:
                Outbound.objects.filter(order_id=order.order_id).update(status=form.cleaned_data["status"])
            return redirect('/orders')

    context = {'form': form, 'nbar': 'orders'}
    return render(request, 'inventory/form.html', context)

@custom_login_required
@admin_required
def deleteOrder(request, pk):
    order = Order.objects.get(order_id=pk)
    products = order.product

    if request.method == "POST":
        products.product_quantity += order.order_quantity
        products.save()
        order.delete()
        new_log = TransactionProductQty(user=request.user,
                                        action="Order",
                                        qty=order.order_quantity,
                                        current_qty=products.product_quantity,
                                        record_product=products.sku_code,
                                        reason="Auto-Generate: Delete Order")

        new_log.save()
        TransactionProductQty.objects.filter(
            id=new_log.id).update(product=products.sku_code)

        return redirect('/orders')

    context = {'order': order, 'nbar': 'orders'}
    return render(request, 'inventory/delete_order.html', context)

@custom_login_required
@admin_required
def createSeller(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    CreateSellerFormSet = formset_factory(CreateSellerForm,extra=form_num,can_delete=True)
    formset = CreateSellerFormSet()

    seller = Seller.objects.all()
    if request.method == "POST":
        formset = CreateSellerFormSet(request.POST)

        if formset.is_valid():
            seller_exist = False

            # ignore deleted, check seller exist
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_seller = form.cleaned_data.get("username")
                    if input_seller is not None:
                        seller = User.objects.filter(username=input_seller).count()

                        #if username is found in db, give error
                        if seller > 0:
                            messages.warning(request, "This username already taken. Please use a different username.", extra_tags="Error for Username: "+input_seller)
                            seller_exist = True
                        
            #if no errors, save seller information into db, then redirect to sellers
            if not seller_exist:
                for form in formset:
                    input_seller = form.cleaned_data.get("username")
                    if input_seller is not None:
                        form.save()
                return redirect('/seller')

        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset,
        'nbar': 'seller'}
    return render(request, 'inventory/create_form.html', context)

@custom_login_required
@admin_required
def deleteSeller(request, pk):
    seller = Seller.objects.get(user_id=pk)
    user = User.objects.get(id=pk)

    if request.method == "POST":
        seller.delete()
        user.delete()
        return redirect('/seller')

    context = {'seller': seller, 'nbar': 'seller'}
    return render(request, 'inventory/delete_seller.html', context)

@custom_login_required
@admin_required
def updateSeller(request, pk):
    seller = Seller.objects.get(user_id=pk)
    form = SellerForm(instance=seller)

    if request.method == "POST":
        form = SellerForm(request.POST, instance=seller)
        if form.is_valid():
            form.save()
            return redirect(f'/seller_order/{seller.user_id}')

    context = {'form': form, 'nbar': 'seller'}
    return render(request, 'inventory/form.html', context)

@custom_login_required
@admin_required
def resetPw(request, pk):
    user = User.objects.get(id=pk)
    form = SetPasswordForm(pk)
    print(f"form -> {form}")
    if request.method == "POST":
        form = SetPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            _user = form.save()
            print(f"User -> {_user}")
            
            messages.success(request, 'Your password was successfully updated!')
            return redirect(f'/seller_order/{_user.id}')

    context = {'form': form, 'nbar': 'seller'}
    return render(request, 'inventory/form.html', context)

@custom_login_required
@admin_required
def createProduct(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    ProductFormSet = formset_factory(ProductForm,extra=form_num,can_delete=True)
    formset = ProductFormSet()

    product = Product.objects.all()
    if request.method == "POST":
        formset = ProductFormSet(request.POST)

        if formset.is_valid():
            product_exist = False
            price_valid = True

            # ignore deleted, check product exist, validate price
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_product = form.cleaned_data.get("sku_code")
                    product_price = form.cleaned_data.get("product_price")
                    if input_product is not None:
                        product = Product.objects.filter(sku_code=input_product).count()
                        #if sku_code is found in db, give error
                        if product > 0:
                            messages.warning(request, f"This SKU code already exists. Please use a different SKU code.", extra_tags="Error for SKU code: "+input_product)
                            product_exist = True
                        else:
                            if(float(product_price) < 0):
                                messages.warning(request, "Price cannot be negative")
                                price_valid = False
                        
            #if no errors, save product information into db, log results, then redirect to products
            if not product_exist and price_valid:
                for form in formset:
                    input_product = form.cleaned_data.get("sku_code")
                    if input_product is not None:
                        input_code = form.save()

                        new_inbound = Inbound(
                            product_name = form.cleaned_data["product_name"],
                            sku_code = form.cleaned_data["sku_code"],
                            unit = form.cleaned_data["unit"],
                            product_quantity = form.cleaned_data["product_quantity"],
                            product_price = form.cleaned_data["product_price"],
                            remarks = f'Admin add new product: {form.cleaned_data.get("remarks")}',
                            status = "Approved",
                            seller = form.cleaned_data["seller"]
                        )
                        new_inbound.save()

                        new_log = TransactionProductQty(
                            user=request.user,
                            action="Create",
                            qty=form.cleaned_data["product_quantity"],
                            current_qty=form.cleaned_data["product_quantity"],
                            record_product=form.cleaned_data["sku_code"],
                            reason="Auto-Generate: New Product Created"
                        )

                        new_log.save()
                        print(f"form.cleaned_data => {input_code}")
                        something_X = new_log.id
                        print(f"new_log.id = {something_X}")
                        TransactionProductQty.objects.filter(id=new_log.id).update(product=input_code)
                        print("Post complex filter:")

                return redirect('/products')
            
        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset,
        'nbar': 'products'}
    return render(request, 'inventory/create_form.html', context)

@custom_login_required
@admin_required
def updateProduct(request, pk):
    product = Product.objects.get(sku_code=pk)
    initial_seller = product.seller
    initial_qty = product.product_quantity

    form = UpdateProductForm(instance=product)

    if request.method == "POST":
        form = UpdateProductForm(request.POST, instance=product)
        if form.is_valid():

            seller = form.cleaned_data["seller"]
            Order.objects.filter(product=pk).update(seller=seller)

            form.save()

            new_log = TransactionProductQty(user=request.user,
                                            action="Update",
                                            qty=form.cleaned_data["product_quantity"],
                                            current_qty=form.cleaned_data["product_quantity"],
                                            record_product=pk,
                                            reason=f"Auto-Generate: Quantity change from {initial_qty} to {form.cleaned_data['product_quantity']}")

            new_log.save()
            TransactionProductQty.objects.filter(
                id=new_log.id).update(product=pk)

            return redirect('/products')

        else:
            price = request.POST.get('product_price')
            if(float(price) < 0):
                messages.warning(request, "Price cannot be negative")

    context = {'form': form, 'nbar': 'products'}
    return render(request, 'inventory/form.html', context)

@custom_login_required
@admin_required
def deleteProduct(request, pk):
    product = Product.objects.get(sku_code=pk)

    if request.method == "POST":
        new_inbound = Inbound(
                    product_name = product.product_name,
                    sku_code = product.sku_code,
                    unit = product.unit,
                    product_quantity = product.product_quantity,
                    product_price = product.product_price,
                    remarks = f'Admin deleted the product',
                    status = "Approved",
                    seller = product.seller
        )
        new_inbound.save()

        product.delete()

        new_log = TransactionProductQty(user=request.user,
                                        action="Delete",
                                        qty=None,
                                        current_qty=None,
                                        record_product=pk,
                                        reason=f"Auto-Generate: Product Deleted- {pk}")

        new_log.save()

        return redirect('/products')

    context = {'product': product, 'nbar': 'products'}
    return render(request, 'inventory/delete_product.html', context)

@custom_login_required
@admin_required
def editProductQty(request, pk):
    product = Product.objects.get(sku_code=pk)

    form = EditProductQtyForm()

    if request.method == "POST":
        form = EditProductQtyForm(request.POST)
        if form.is_valid():
            input_quantity = form.cleaned_data["qty"]
            input_reason = form.cleaned_data["reason"]
            product.product_quantity += input_quantity

            if product.product_quantity < 0:
                messages.warning(request, "Invalid Quantity")

            else:
                product.save()

                new_inbound = Inbound(
                            product_name = product.product_name,
                            sku_code = product.sku_code,
                            unit = product.unit,
                            product_quantity = input_quantity,
                            product_price = product.product_price,
                            remarks = f'Admin add/deduct: {input_reason}',
                            status = "Approved",
                            seller = product.seller
                )
                new_inbound.save()

                form = form.save(commit=False)
                form.user = request.user
                form.action = "Add/Deduct"
                form.current_qty = product.product_quantity
                form.record_product = pk
                form.save()
                TransactionProductQty.objects.filter(
                    id=form.id).update(product=pk)

                return redirect('/products')

    context = {'form': form, 'nbar': 'products'}
    return render(request, 'inventory/form.html', context)

@custom_login_required
@admin_required
def listLog(request):
    logs = TransactionProductQty.objects.all()

    myFilter = LogFilter(request.GET, queryset=logs)
    logs = myFilter.qs

    #check if the get attributes exist, if yes, assign it to be passed to the hidden form
    action = request.GET['action'] if (request.method == 'GET' and 'action' in request.GET) else ''
    record_product = request.GET['record_product'] if (request.method == 'GET' and 'record_product' in request.GET) else ''

    # paginate results
    page = request.GET.get('page', 1)
    logs = paginate(logs, page);

    context = {
        'logs': logs,
        'myFilter': myFilter,
        'nbar': 'list_log',
        'action': action,
        'record_product': record_product
        }

    return render(request, 'inventory/log.html', context)

@custom_login_required
def inbound(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            inbounds = Inbound.objects.all()

            myFilter = InboundFilter(request.GET, queryset=inbounds)
            inbounds = myFilter.qs

            #check if the get attributes exist, if yes, assign it to be passed to the hidden form
            product_name = request.GET['product_name'] if (request.method == 'GET' and 'product_name' in request.GET) else ''
            status = request.GET['status'] if (request.method == 'GET' and 'status' in request.GET) else ''

            # paginate results
            page = request.GET.get('page', 1)
            inbounds = paginate(inbounds, page);

            context = {
                'inbounds': inbounds,
                'myFilter': myFilter,
                'nbar': 'inbound',
                'product_name': product_name,
                'status': status
            }
            print(type(inbounds))
        else:
            inbounds = Inbound.objects.filter(seller_id=request.user.id)

            myFilter = InboundFilter(request.GET, queryset=inbounds)
            inbounds = myFilter.qs

            #check if the get attributes exist, if yes, assign it to be passed to the hidden form
            product_name = request.GET['product_name'] if (request.method == 'GET' and 'product_name' in request.GET) else ''
            status = request.GET['status'] if (request.method == 'GET' and 'status' in request.GET) else ''

            # paginate results
            page = request.GET.get('page', 1)
            inbounds = paginate(inbounds, page);
            context = {
                'inbounds': inbounds,
                'myFilter': myFilter,
                'nbar': 'inbound',
                'product_name': product_name,
                'status': status
            }

    return render(request, 'inventory/inbound.html', context)

@custom_login_required
@seller_required
def createInbound(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    InboundFormSet = formset_factory(InboundForm,extra=form_num,can_delete=True)
    formset = InboundFormSet(form_kwargs={'sellerId' : request.user.id})

    if request.method == "POST":
        formset = InboundFormSet(request.POST, form_kwargs={'sellerId' : request.user.id})

        if formset.is_valid():
            quantity_valid = True

            # ignore deleted, check product quantity
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_inbound = form.cleaned_data.get("product")
                    product_quantity = form.cleaned_data.get("product_quantity")
                    if input_inbound is not None:
                        #if sku_code is found in db, give error
                        if product_quantity <= 0:
                            messages.warning(request, f"Please enter a valid quantity.", extra_tags="Error for product: "+input_product)
                            quantity_valid = False
                        
            #if no errors, save inbound information into db, then redirect to inbound
            if quantity_valid:
                for form in formset:
                    input_inbound = form.cleaned_data.get("product")
                    product_quantity = form.cleaned_data.get("product_quantity")
                    remarks = form.cleaned_data.get("remarks")
                    if input_inbound is not None:
                        print(f"input_inbound => {input_inbound}")
                        product = Product.objects.get(sku_code=input_inbound)
                        print(f"product sku => {product}")

                        new_inbound = Inbound(
                            product_name = product.product_name,
                            sku_code = input_inbound,
                            unit = product.unit,
                            product_quantity = product_quantity,
                            product_price = product.product_price,
                            remarks = remarks,
                            seller_id = request.user.id,
                        )
                        new_inbound.save()

                return redirect('/inbound')
            
        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset,
        'nbar': 'inbound'}
    return render(request, 'inventory/create_inbound_form.html', context)

@custom_login_required
@seller_required
def createNpInbound(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    NpInboundFormSet = formset_factory(NpInboundForm,extra=form_num,can_delete=True)
    formset = NpInboundFormSet()

    if request.method == "POST":
        formset = NpInboundFormSet(request.POST)

        if formset.is_valid():
            quantity_valid = True
            price_valid = True

            # ignore deleted, check product exist, validate price
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_npinbound = form.cleaned_data.get("product_name")
                    product_quantity = form.cleaned_data.get("product_quantity")
                    product_price = form.cleaned_data.get("product_price")
                    if input_npinbound is not None:
                        #if sku_code is found in db, give error
                        if product_quantity <= 0:
                            messages.warning(request, f"Please enter a valid quantity.", extra_tags="Error for product: "+input_product)
                            quantity_valid = False
                        else:
                            if(float(product_price) < 0):
                                messages.warning(request, "Price cannot be negative")
                                price_valid = False
                        
            #if no errors, save product information into db, log results, then redirect to products
            if quantity_valid and price_valid:
                for form in formset:
                    input_npinbound = form.cleaned_data.get("product_name")
                    unit = form.cleaned_data.get("unit")
                    product_quantity = form.cleaned_data.get("product_quantity")
                    product_price = form.cleaned_data.get("product_price")
                    remarks = form.cleaned_data.get("remarks")
                    if input_npinbound is not None:
                        
                        new_inbound = Inbound(
                            product_name = input_npinbound,
                            unit = unit,
                            product_quantity = product_quantity,
                            product_price = product_price,
                            remarks = remarks,
                            seller_id = request.user.id,
                        )
                        new_inbound.save()

                return redirect('/inbound')
            
        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset,
        'nbar': 'inbound'}
    return render(request, 'inventory/create_np_inbound_form.html', context)

@custom_login_required
@admin_required
def approveInbound(request, pk):
    inbound = Inbound.objects.get(id=pk)
    
    context = {
        'nbar': 'inbound',
        'type': 'approve',
        'inbound':inbound,
    }

    if request.method == "POST":
        if(inbound.sku_code is not None):
            product = Product.objects.get(sku_code = inbound.sku_code)
            total_quantity = product.product_quantity + inbound.product_quantity

            Inbound.objects.filter(id = pk).update(status="Approved")
            Product.objects.filter(sku_code = inbound.sku_code).update(product_quantity=total_quantity)
            
            new_log = TransactionProductQty(
                    user=request.user,
                    action="Add/Deduct",
                    qty=inbound.product_quantity,
                    current_qty=total_quantity,
                    record_product=inbound.sku_code,
                    reason="Auto-Generate: New Customer Inbound Approved"
                    )

            new_log.save()

            return redirect('/inbound')

        else:
            form = UpdateNpInboundForm(request.POST)
            if form.is_valid():
                new_product = form.save(commit=False)
                new_product.product_name = inbound.product_name
                new_product.unit = inbound.unit
                new_product.product_quantity = inbound.product_quantity
                new_product.product_price = inbound.product_price
                new_product.seller_id = inbound.seller_id
                new_product.save()

                Inbound.objects.filter(id=pk).update(status = "Approved", sku_code = form.cleaned_data['sku_code'])
                
                new_log = TransactionProductQty(
                    user=request.user,
                    action="Create",
                    qty=inbound.product_quantity,
                    current_qty=inbound.product_quantity,
                    record_product=new_product,
                    reason="Auto-Generate: New Customer Inbound (New Product) Approved"
                    )

                new_log.save()

                return redirect('/inbound')

            context['form'] = form
            return render(request, "inventory/inbound_confirmation.html", context)
        
    else :
        if(inbound.sku_code is None):
            context['form'] = UpdateNpInboundForm()
        return render(request, "inventory/inbound_confirmation.html", context)

@custom_login_required
@admin_required
def rejectInbound(request, pk):
    inbound = Inbound.objects.get(id=pk)

    context = {
        'nbar': 'inbound',
        'type': 'reject',
        'inbound':inbound,
    }

    if request.method == "POST":
        Inbound.objects.filter(id = pk).update(status="Rejected")
        return redirect('/inbound')

    else:
        return render(request, "inventory/inbound_confirmation.html", context)

    return render(request, 'inventory/inbound_confirmation.html', context)

@custom_login_required
def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

@custom_login_required
def outbound(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            outbounds = Outbound.objects.all()

            myFilter = OutboundFilter(request.GET, queryset=outbounds)
            outbounds = myFilter.qs

            #check if the get attributes exist, if yes, assign it to be passed to the hidden form
            seller = request.GET['seller'] if (request.method == 'GET' and 'seller' in request.GET) else ''
            status = request.GET['status'] if (request.method == 'GET' and 'status' in request.GET) else ''

             # paginate results
            page = request.GET.get('page', 1)
            outbounds = paginate(outbounds, page);

            context = {'outbounds':outbounds,
                        'myFilter': myFilter,
                        'nbar':'outbound',
                        'seller': seller,
                        'status' : status
            }

            print(type(outbounds))
        else:
            outbounds = Outbound.objects.filter(seller_id=request.user.id)

            myFilter = OutboundFilter(request.GET, queryset=outbounds)
            outbounds = myFilter.qs

            #check if the get attributes exist, if yes, assign it to be passed to the hidden form
            seller = request.GET['seller'] if (request.method == 'GET' and 'seller' in request.GET) else ''
            status = request.GET['status'] if (request.method == 'GET' and 'status' in request.GET) else ''
    
            # paginate results
            page = request.GET.get('page', 1)
            outbounds = paginate(outbounds, page);

            context = {'outbounds':outbounds,
                        'myFilter': myFilter,
                        'nbar':'outbound',
                        'seller': seller,
                        'status' : status
            }    
    
    return render(request, 'inventory/outbound.html', context)

@custom_login_required
@seller_required
def createOutbound(request):
    form_num = int(request.GET['form_num']) if (request.method == 'GET' and 'form_num' in request.GET) else 10
    OutboundFormSet = formset_factory(OutboundForm,extra=form_num,can_delete=True)
    formset = OutboundFormSet(form_kwargs={'sellerId' : request.user.id})
    if request.method == "POST":
        formset = OutboundFormSet(request.POST, form_kwargs={'sellerId' : request.user.id})

        if formset.is_valid():
            qty_ok = True
            products_dict = {}

            # ignore deleted, check order exist, check quantity more than stock
            for form in formset:
                #check if input form is marked to be deleted, if not marked, proceed with checking     
                if not form.cleaned_data.get('DELETE'):
                    input_outbound = form.cleaned_data.get("product")
                    outbound_quantity = form.cleaned_data.get("order_quantity")
                    if input_outbound is not None:
                        outbound_quantity = form.cleaned_data.get("order_quantity")
                        input_outbound = form.cleaned_data.get("product")
                            
                        if input_outbound in products_dict:
                            temp_qty = products_dict[input_outbound] + outbound_quantity
                            products_dict.update({input_outbound:temp_qty})
                            
                        else:
                            products_dict[input_outbound] = outbound_quantity

                        
                    if bool(products_dict):
                        for code,qty in products_dict.items():
                            product = Product.objects.get(sku_code=code)

                            if qty <= product.product_quantity:
                                    print("Valid!!!!")
                                
                            else:
                                    print("Invalid!!!!!!!")
                                    messages.warning(request, f"The quantity specified in the outbound for product {code}, is more than the existing stock in the inventory. Make sure the quantity specified is correct or update the stock info for the product {code}.")
                                    qty_ok = False
                        
            #if no errors, save order information into db, update product stock information, log results, then redirect to orders
            if qty_ok:
                for form in formset:
                    input_outbound = form.cleaned_data.get("product")
                    outbound_quantity = form.cleaned_data.get("order_quantity")
                    outbound_platform = form.cleaned_data.get("platform")
                    outbound_remarks = form.cleaned_data.get("remarks")
                    if input_outbound is not None:
                        outbound_quantity = form.cleaned_data.get("order_quantity")
                        print(f"input_outbound => {input_outbound}")
                        product = Product.objects.get(sku_code=input_outbound)
                        
                        new_outbound = Outbound(
                            order_quantity =  outbound_quantity,
                            platform = outbound_platform,
                            remarks = outbound_remarks,
                
                            seller_id = request.user.id,
                            product = input_outbound,
                        )
                        new_outbound.save()
                return redirect('/outbound')

        else:
            for form in formset:
                messages.error(request, form.errors)
    
    context={
        'formset': formset,
        'nbar':'outbound'}
    return render(request, 'inventory/createOutbound_form.html', context)

@custom_login_required
@admin_required
def approveOutbound(request, pk):
    outbound = Outbound.objects.get(id=pk)

    context = {
        'nbar': 'outbound',
        'type': 'approve',
        'inbound':outbound,
    }

    if request.method == "POST":
        form = ApproveOutboundForm(request.POST)
        if form.is_valid():

            new_order = form.save(commit=False)
            new_order.order_quantity = outbound.order_quantity
            new_order.platform = outbound.platform
            new_order.seller_id = outbound.seller_id
            new_order.product = outbound.product
            new_order.status = "Pending"
            new_order.save()

            product = Product.objects.get(sku_code = outbound.product.sku_code)
            total_qty = product.product_quantity - outbound.order_quantity
            Outbound.objects.filter(id=pk).update(status = "Approved", order_id = form.cleaned_data['order_id'])
            Product.objects.filter(sku_code=outbound.product.sku_code).update(product_quantity=total_qty)

            new_log = TransactionProductQty(
                    user=request.user,
                    action="Deduct",
                    qty=outbound.order_quantity,
                    current_qty=total_qty,
                    record_product=outbound.product.sku_code,
                    reason="Auto-Generate: New Customer Outbound Approved"
                    )

            new_log.save()

            return redirect('/outbound')

        context['form'] = form
        return render(request, "inventory/outbound_confirmation.html", context)
    else:
        if(outbound.order_id is None):
            context['form'] = ApproveOutboundForm()
        return render(request, "inventory/outbound_confirmation.html", context)

@custom_login_required
@admin_required
def rejectOutbound(request, pk):
    outbound = Outbound.objects.get(id=pk)

    context = {
        'nbar': 'outbound',
        'type': 'reject',
        'outbound':outbound,
    }

    if request.method == "POST":
        Outbound.objects.filter(id = pk).update(status="Rejected")
        return redirect('/outbound')

    else:
        return render(request, "inventory/outbound_confirmation.html", context)

    return render(request, 'inventory/outbound_confirmation.html', context)

# Opens up page as PDF
class PDFProduct(View):
    def post(self, request):
        # apply filters from the hidden form
        myFilter = ProductFilter(request.POST, queryset=Product.objects.all())
        data = {
            "products": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_products.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class PDFOrder(View):
    def post(self, request):
        myFilter = OrderFilter(request.POST, queryset=Order.objects.all())
        data = {
            "orders": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_orders.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class PDFSeller(View):
    def post(self, request):
        myFilter = SellerFilter(request.POST, queryset=Seller.objects.all())
        data = {
            "sellers": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_sellers.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class PDFLog(View):
    def post(self, request):
        myFilter = LogFilter(request.POST, queryset=TransactionProductQty.objects.all())
        data = {
            "logs": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_logs.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class PDFInbound(View):
    def post(self, request):
        myFilter = InboundFilter(request.POST, queryset=Inbound.objects.all())
        data = {
            "inbounds": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_inbounds.html', data)
        return HttpResponse(pdf, content_type='application/pdf')

class PDFOutbound(View):
    def post(self, request):
        myFilter = OutboundFilter(request.POST, queryset=Outbound.objects.all())
        data = {
            "outbounds": myFilter.qs
            }

        pdf = render_to_pdf('inventory/pdf_template_outbounds.html', data)
        return HttpResponse(pdf, content_type='application/pdf')