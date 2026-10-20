from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, render

from . import services
from .models import Category, Product, StockMovement


def dashboard(request):
    context = {
        'stats': services.dashboard_stats(),
        'low_stock': Product.objects.low_stock()
            .select_related('category')
            .order_by('quantity')[:6],
        'recent_movements': StockMovement.objects
            .select_related('product')[:8],
    }
    return render(request, 'warehouse/dashboard.html', context)


def product_list(request):
    context = services.build_product_list_context(request.GET)
    context['categories'] = Category.objects.all()
    context['per_page_options'] = services.PER_PAGE_OPTIONS
    return render(request, 'warehouse/product_list.html', context)


def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('category', 'supplier'), pk=pk
    )
    size = services.HISTORY_PAGE_SIZE
    movements = list(product.movements.all()[:size + 1])
    totals = product.movements.aggregate(
        total_in=Sum('quantity', filter=Q(movement_type=StockMovement.IN)),
        total_out=Sum('quantity', filter=Q(movement_type=StockMovement.OUT)),
    )
    context = {
        'product': product,
        'movements': movements[:size],
        'has_more': len(movements) > size,
        'totals': totals,
    }
    return render(request, 'warehouse/product_detail.html', context)


def movement_list(request):
    qs = StockMovement.objects.select_related('product')
    current_type = request.GET.get('type', '')
    
    if current_type in (StockMovement.IN, StockMovement.OUT):
        qs = qs.filter(movement_type=current_type)
        
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'page_obj': page_obj,
        'movements': page_obj.object_list,
        'page_range': paginator.get_elided_page_range(
            page_obj.number, on_each_side=1, on_ends=1
        ),
        'current_type': current_type,
    }
    return render(request, 'warehouse/movement_list.html', context)