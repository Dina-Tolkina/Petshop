import random
from django.shortcuts import render, get_object_or_404
from petapp.models import Customer
from petapp.forms import *
from django.db import IntegrityError
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .authentication import EmailAuthBackend
from django.core.files.base import ContentFile
from django.db.models import Avg
from django.utils import timezone
from django.http import JsonResponse


# Main navigation pages
def index(request):
    top_rated_products = Product.objects.annotate(avg_rating=Avg('rating__rating')).order_by('-avg_rating')[:3]
        
    return render(request, 'petapp/main.html', {'top_rated_products': top_rated_products})

def catalog(request):
    products = Product.objects.filter(availability=True)
    category = Product.objects.all()
    animal_type = Product.objects.all()
    rating = Rating.objects.all()

    if not products.exists(): 
        message = "Товаров временно нет"
        return render(request, 'petapp/catalog.html', {'message': message})

    return render(request, 'petapp/catalog.html', {'products': products, 'category' : category, 'animal_type' : animal_type, 'rating' : rating})

def contact(request):
    return render(request, 'petapp/contact.html')

def about(request):
    return render(request, 'petapp/about.html')


# Auth and Reg pages
def reg(request):
    if request.method == 'POST':
        auth_form = createUserForm(request.POST)
        reg_form = RegForm(request.POST)
        form = CombinedRegForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data.get('email')
            password = form.cleaned_data.get('password')
            phone = form.cleaned_data.get('phone')

            
            if not User.objects.filter(email=email).exists() and not Customer.objects.filter(phone=phone).exists():
                if 'last_name' in form.cleaned_data and 'first_name' in form.cleaned_data and 'patronymic' in form.cleaned_data:
                    if len(form.cleaned_data['last_name']) >= 2 and len(form.cleaned_data['first_name']) >= 2 and len(form.cleaned_data['patronymic']) >= 2:
                        auth_form.instance.username = f'{random.randrange(10000000)}'
                        user = auth_form.save()
                        user.set_password(user.password)
                        user = auth_form.save()
                        customer = reg_form.save(commit=False)
                        customer.user = user
                
                        try:
                            customer.save()
                            user = EmailAuthBackend().authenticate(request=request, email=email, password=password)
                            if user is not None:
                                login(request, user)
                                return redirect('home')

                        except IntegrityError:
                            form.add_error('phone', 'Пользователь с таким номером телефона уже существует.')
                    else:
                        form.add_error(None, 'Фамилия, имя и отчество должны содержать не менее 2 символов.')
                else:
                    form.add_error(None, 'Фамилия, имя и отчество являются обязательными полями.')
            else:
                form.add_error(None, 'Пользователь с такой электронной почтой или номером телефона уже существует.')
    
    else:
        form = CombinedRegForm()

    return render(request, 'petapp/reg.html', {'form': form})


def email_login(request):
    if request.user.is_authenticated:
        return redirect('user')
    
    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = EmailAuthBackend().authenticate(request=request, email=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                form.add_error(None, "Ошибка аутентификации")
    else:
        form = EmailLoginForm()
    return render(request, 'petapp/auth.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    return redirect('home')


# Bakset page 
@login_required
def basket(request):
    customer = Customer.objects.get(user=request.user)

    if not Basket.objects.filter(user=customer).exists():
        basket = Basket.objects.create(user=customer)

    basket = Basket.objects.get(user=customer)
    basket_items = BasketProduct.objects.filter(basket=basket).order_by('product_id')

    basket_total = 0
    unavailable_products = []

    for basket_product in basket_items:
        quantity = basket_product.quantity
        product = basket_product.product

        if product.stock < quantity:
            unavailable_products.append(product.product_name)

        basket_total += int(quantity) * int(product.price)

    if unavailable_products:
        messages.error(request, f"Товар(ы) временно отсутствуют: {', '.join(unavailable_products)}")

    return render(request, 'petapp/basket.html', {
        "basket_items": basket_items,
        "basket_total": basket_total,
        "basket": basket,
    })


@login_required
def add_basket(request, pk):
    customer = Customer.objects.get(user=request.user)
    if Basket.objects.filter(user=customer).exists():
        basket = Basket.objects.get(user=customer)
        product = get_object_or_404(Product, pk=pk)
        if BasketProduct.objects.filter(product=product, basket=basket).exists():
            basket_product = BasketProduct.objects.get(product=product, basket=basket)
            if int(basket_product.quantity) >= basket_product.product.stock:
                messages.error(request, "Ошибка, товаров на складе больше нет.")
            else:
                basket_items = BasketProduct.objects.filter(pk=basket_product.pk, basket=basket).update(quantity=int(basket_product.quantity) + 1)
        else:
            basket_items = BasketProduct.objects.create(product=product, basket=basket, quantity=1)
    else:
        basket = Basket.objects.create(user=customer)
        product = get_object_or_404(Product, pk=pk)
        basket_items = BasketProduct.objects.create(product=product, basket=basket, quantity=1)
    return redirect('catalog')


def addition_basket(request, product, basket):
    basket_product = BasketProduct.objects.get(pk=product)
    product = basket_product.product
    if int(basket_product.quantity) >= basket_product.product.stock:
        messages.error(request, "Ошибка, товаров на складе больше нет.")
    else:
        basket_items = BasketProduct.objects.filter(pk=basket_product.pk, basket=basket).update(quantity=int(basket_product.quantity) + 1)
    return redirect("basket")

def subtraction_basket(request, product, basket):
    basket_product = BasketProduct.objects.get(pk=product)
    if basket_product.quantity == 1:
        basket_product.delete()
    else:
        basket_items = BasketProduct.objects.filter(pk=product, basket_id=basket).update(quantity = int(basket_product.quantity) - 1)
    return redirect("basket")


#User page
def user(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user)
        user = customer.user

    if not Basket.objects.filter(user=customer).exists():
        basket = Basket.objects.create(user=customer)
    basket = Basket.objects.get(user=customer)
    basket_items = BasketProduct.objects.filter(basket=basket).order_by('product_id')
    total_items = 0
    basket_total = 0
    for a in basket_items:
        basket_total += int(a.quantity) * int(a.product.price)
        total_items += a.quantity 

    total_items_order = Order.objects.filter(customer=customer).count()
    return render(request, 'petapp/user.html', {'user': user, 'customer': customer,"basket_total": basket_total, 'total_items': total_items, 'total_items_order': total_items_order})

def user_edit(request):
    if request.user.is_authenticated:
        customer = Customer.objects.get(user=request.user)
        user = customer.user
    
    if request.method == 'POST':
        user.last_name = request.POST.get('surname')
        user.first_name = request.POST.get('name')
        user.email = request.POST.get('email')

        if User.objects.filter(email=user.email).exclude(pk=user.pk).exists():
            messages.error(request, "Пользователь с такой электронной почтой или номером телефона уже существует.")
            return render(request, 'petapp/user_edit.html', {'user': user, 'customer': customer})
        
        if Customer.objects.filter(phone=customer.phone).exclude(pk=customer.pk).exists():
            messages.error(request, "Phone number must be unique.")
            return render(request, 'petapp/user_edit.html', {'user': user, 'customer': customer})
        
        name_validator = RegexValidator(regex=r'^[a-zA-Zа-яА-Я]{2,}$', message="ФИО должно содержать только русские или английские буквы и быть длиной не менее 2 символов.")
        
        try:
            name_validator(user.last_name)
        except ValidationError as e:
            messages.error(request, e.message)
        
        try:
            name_validator(user.first_name)
        except ValidationError as e:
            messages.error(request, e.message)
        
        patronymic = request.POST.get('patronymic')
        if patronymic:
            try:
                name_validator(patronymic)
                customer.patronymic = patronymic
            except ValidationError as e:
                messages.error(request, e.message)
        
        phone = request.POST.get('phone')
        if phone:
            if Customer.objects.filter(phone=phone).exclude(pk=customer.pk).exists():
                messages.error(request, "Пользователь с таким номером телефона уже существует.")
                return render(request, 'petapp/user_edit.html', {'user': user, 'customer': customer})
            customer.phone = phone
        
        address = request.POST.get('address')
        if address:
            customer.address = address

        if 'photo_avatar' in request.FILES:
            photo = request.FILES['photo_avatar']
            if not photo.name.endswith(('.jpg', '.jpeg', '.png')):
                messages.error(request, "Допустимы только файлы формата JPG или PNG.") 

            else:
                if customer.photo_avatar:
                    old_photo_path = customer.photo_avatar.path
                    customer.photo_avatar.delete(save=False)

                new_photo_name = f"user_{user.id}_avatar"
                customer.photo_avatar.save(f"{new_photo_name}.jpg", ContentFile(photo.read()))

        if not messages.get_messages(request):
            user.save()
            customer.save()
            return redirect('user')

    return render(request, 'petapp/user_edit.html', {'user': user, 'customer': customer})


#Payment, orders  page 
def calculate_total_price(basket_items):
    """
    Функция для расчета общей суммы на основе списка товаров в корзине.
    """
    total = 0
    for item in basket_items:  
        quantity = item.quantity 
        price = item.product.price  
        total += quantity * price
    return total


@login_required
def create_payment(request, basket_id):
    basket = get_object_or_404(Basket, id=basket_id)
    form = PaymentForm()

    available_basket_items = []
    unavailable_products = []

    for basket_product in basket.basketproduct_set.all():
        quantity = basket_product.quantity
        product = basket_product.product

        if product.stock < quantity:
            unavailable_products.append(product.product_name)
            basket_product.delete() 
        else:
            available_basket_items.append(basket_product)

    if unavailable_products:
        error_message = f"Следующие товары временно отсутствуют и были удалены из корзины: {', '.join(unavailable_products)}."
        messages.error(request, error_message)
        return render(request, 'petapp/basket.html', {
            'basket': basket, 
            'unavailable_products': unavailable_products
        })

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            order = Order.objects.create(
                customer=basket.user,
                order_date=timezone.now().date(),
                shipping_address=form.cleaned_data['shipping_address']
            )

            basket_items_data = [
                {
                    'product_id': item.product.id,
                    'product_name': item.product.product_name,
                    'quantity': item.quantity,
                    'price': item.product.price,
                    'photo_url': item.product.photo_product.url,  
                }
                for item in available_basket_items
            ]

            order_detail = OrderDetail.objects.create(
                order=order,
                order_number=uuid.uuid4(),
                status='created',
                basket_items={'products': basket_items_data},  
                total_price=calculate_total_price(available_basket_items)  
            )

            order_detail.status = 'paid'
            order_detail.payment_id = "TEST_PAYMENT_12345"  
            order_detail.save()

            BasketProduct.objects.filter(basket=basket, product__in=[item.product for item in available_basket_items]).delete()

            for basket_product in available_basket_items:
                basket_product.product.reduce_stock(basket_product.quantity)

            PurchaseHistory.objects.create(
                user=request.user.customer,
                order_detail=order_detail
            )

            return redirect('payment_confirmation', order_detail_id=order_detail.id)

    return render(request, 'petapp/payment_page.html', {'form': form, 'basket': basket})


def payment_confirmation(request, order_detail_id):
    order_detail = get_object_or_404(OrderDetail, id=order_detail_id)

    return render(request, 'petapp/payment_confirmation.html', {'order_detail': order_detail})


@login_required
def user_orders(request):
    customer = request.user.customer
    orders = Order.objects.filter(customer=customer).order_by('-order_date', '-id')
    total_items = orders.count()

    rated_products = Rating.objects.filter(user=customer).select_related('product')
    rated_products_dict = {rating.product.id: rating.rating for rating in rated_products}

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        rating_value = request.POST.get('rating_value')

        if product_id and rating_value:
            try:
                product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Этот продукт больше не доступен в магазине.'
                }, status=400)

            rating, created = Rating.objects.get_or_create(
                user=customer,
                product=product,
                purchase_history=PurchaseHistory.objects.filter(user=customer).first()
            )
            rating.rating = rating_value
            rating.save()

            return JsonResponse({
                'success': True,
                'product_name': product.product_name,
                'message': f'Рейтинг для продукта {product.product_name} обновлен!'
            })

        return JsonResponse({
            'success': False,
            'message': 'Недопустимые данные.'
        }, status=400)

    for order in orders:
        basket_items = order.details.basket_items
        if 'products' in basket_items:
            for item in basket_items['products']:
                item['total_price'] = item['quantity'] * item['price']
                item['photo_url'] = item.get('photo_url', '')
                item['is_rated'] = item['product_id'] in rated_products_dict
                item['rating'] = rated_products_dict.get(item['product_id'], None)
                product_exists = Product.objects.filter(id=item['product_id']).exists()
                item['is_exist'] = product_exists

    return render(request, 'petapp/user_orders.html', {'orders': orders, 'total_items': total_items})
