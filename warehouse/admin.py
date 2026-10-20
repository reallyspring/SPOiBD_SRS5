from django.contrib import admin

from .models import Category, Product, StockMovement, Supplier


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email')
    search_fields = ('name',)


class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    fields = ('created_at', 'movement_type', 'quantity', 'comment')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'name', 'category', 'quantity', 
        'min_quantity', 'price', 'is_archived',
    )
    list_filter = ('category', 'is_archived')
    search_fields = ('sku', 'name')
    inlines = [StockMovementInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'product', 'movement_type', 
        'quantity', 'comment',
    )
    list_filter = ('movement_type',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False