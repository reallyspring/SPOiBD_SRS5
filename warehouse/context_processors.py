from .models import Product
def warehouse_sidebar(request):
    return {'low_stock_count': Product.objects.low_stock().count()}
