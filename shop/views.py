
from django.shortcuts import render
from .models import Category, Product
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from decimal import Decimal
from .models import Order, OrderItem, Product



def home(request):
    categories = Category.objects.all()
    products = Product.objects.all().order_by('-created_at')

    featured_products = products.filter(is_featured=True)

    return render(request, 'shop/home.html', {
        'categories': categories,
        'products': products,
        'featured_products': featured_products,
    })

def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category)

    return render(request, 'shop/category_products.html', {
        'category': category,
        'products': products,
    })


def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    return render(request, 'shop/product_detail.html', {
        'product': product,
    })

def add_to_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)

        if product.stock > 0:
            cart = request.session.get("cart", {})
            product_key = str(product_id)
            current_qty = cart.get(product_key, 0)

            if current_qty < product.stock:
                cart[product_key] = current_qty + 1
                request.session["cart"] = cart

    return redirect("cart")


def cart_view(request):
    cart = request.session.get("cart", {})
    cart_items = []
    total = 0

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=int(product_id))
        except (Product.DoesNotExist, ValueError):
            continue

        quantity = int(quantity)
        subtotal = product.price * quantity

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })
        total += subtotal

    return render(request, "shop/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })



def update_cart(request, product_id):
    if request.method == "POST":
        product = get_object_or_404(Product, id=product_id)
        cart = request.session.get("cart", {})
        key = str(product_id)

        try:
            quantity = int(request.POST.get("quantity", 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity <= 0:
            cart.pop(key, None)
        elif quantity <= product.stock:
            cart[key] = quantity
        else:
            cart[key] = product.stock

        request.session["cart"] = cart
        request.session.modified = True

    return redirect("cart")


def remove_from_cart(request, product_id):
    if request.method == "POST":
        cart = request.session.get("cart", {})
        cart.pop(str(product_id), None)
        request.session["cart"] = cart

    return redirect("cart")


def checkout_view(request):
    cart = request.session.get("cart", {})

    if not cart:
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    cart_items = []
    total = Decimal("0.00")

    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(id=int(product_id))
            quantity = int(quantity)

            if quantity <= 0:
                continue

        except (Product.DoesNotExist, ValueError, TypeError):
            continue

        subtotal = product.price * quantity

        cart_items.append({
            "product": product,
            "quantity": quantity,
            "subtotal": subtotal,
        })
        total += subtotal

    if not cart_items:
        request.session["cart"] = {}
        messages.warning(request, "Your cart is empty.")
        return redirect("cart")

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()

        if not all([
            customer_name, email, phone, address,
            city, state, postal_code
        ]):
            messages.error(request, "Please fill in all delivery details.")
            return render(request, "shop/checkout.html", {
                "cart_items": cart_items,
                "total": total,
            })

        try:
            with transaction.atomic():
                order_lines = []
                locked_products = {}

                # Lock products and verify stock before placing the order.
                for item in cart_items:
                    product_id = item["product"].id
                    product = Product.objects.select_for_update().get(
                        id=product_id
                    )
                    quantity = item["quantity"]

                    if quantity > product.stock:
                        raise ValueError(
                            f"Only {product.stock} unit(s) of "
                            f"{product.name} are available."
                        )

                    locked_products[product_id] = product
                    order_lines.append((product, quantity))

                # Calculate total using current database prices.
                total = sum(
                    (product.price * quantity
                     for product, quantity in order_lines),
                    Decimal("0.00")
                )

                order = Order.objects.create(
                    customer_name=customer_name,
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    payment_method="Cash on Delivery",
                    total_amount=total,
                )

                for product, quantity in order_lines:
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        product_name=product.name,
                        price=product.price,
                        quantity=quantity,
                    )

                    product.stock -= quantity
                    product.save(update_fields=["stock"])

        except ValueError as error:
            messages.error(request, str(error))
            return redirect("checkout")

        request.session["cart"] = {}
        messages.success(request, "Your order has been placed!")
        return redirect("order_success", order_id=order.id)

    return render(request, "shop/checkout.html", {
        "cart_items": cart_items,
        "total": total,
    })


def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    return render(request, "shop/order_success.html", {
        "order": order,
    })


