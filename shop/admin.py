from django.contrib import admin
from .models import Category, Product
from .models import Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'stock')

admin.site.register(Order)
admin.site.register(OrderItem)