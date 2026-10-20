import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST
from . import services
from .models import Product, StockMovement


def _error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _json_body(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _product_payload(product):
    return {
        'id': product.pk,
        'quantity': product.quantity,
        'price': str(product.price),
        'stock_value': str(product.stock_value),
        'status_label': product.status_label,
        'status_color': product.status_color,
    }


@require_POST
def product_move(request, pk):
    data = _json_body(request)    
    try:
        quantity = int(data.get('quantity'))
    except (TypeError, ValueError):
        return _error('Укажите количество целым числом')
    
    comment = str(data.get('comment', '')).strip()[:255]
    try:
        product, movement = services.register_movement(
            pk, data.get('movement_type'), quantity, comment
        )
    except Product.DoesNotExist:
        return _error('Товар не найден', status=404)
    except services.StockError as exc:
        return _error(str(exc))
    
    verb = 'Приход' if movement.movement_type == StockMovement.IN else 'Расход'
    return JsonResponse({
        'ok': True,
        'message': (
            f'{verb}: {movement.quantity} {product.get_unit_display()} '
            f'«{product.name}»'
        ),
        'product': _product_payload(product),
        'movement_html': render_to_string(
            'warehouse/partials/_movement_row.html', 
            {'m': movement},
        ),
    })


@require_POST
def product_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    raw = str(_json_body(request).get('price', '')).replace(',', '.').strip()
    
    try:
        price = Decimal(raw)
    except InvalidOperation:
        return _error('Введите цену числом')
    
    if not price.is_finite() or price < 0 or price >= Decimal('100000000'):
        return _error('Цена должна быть от 0 до 99 999 999.99')
    
    product.price = price.quantize(Decimal('0.01'))
    product.save(update_fields=['price', 'updated_at'])
    
    return JsonResponse({'ok': True, 'product': _product_payload(product)})


@require_POST
def product_archive(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    product.is_archived = not product.is_archived
    product.save(update_fields=['is_archived', 'updated_at'])
    
    return JsonResponse({
        'ok': True, 
        'id': product.pk, 
        'is_archived': product.is_archived,
    })


@require_GET
def product_search(request):
    context = services.build_product_list_context(request.GET)
    
    html = render_to_string(
        'warehouse/partials/_product_list.html', 
        context, 
        request=request,
    )
    
    return JsonResponse({
        'ok': True, 
        'html': html, 
        'count': context['page_obj'].paginator.count,
    })


@require_GET
def product_movements(request, pk):
    product = get_object_or_404(Product, pk=pk)
    
    offset = request.GET.get('offset', '0')
    offset = int(offset) if offset.isdigit() else 0
    
    size = services.HISTORY_PAGE_SIZE
    items = list(product.movements.all()[offset:offset + size + 1])
    
    has_more = len(items) > size
    items = items[:size]
    
    html = ''.join(
        render_to_string(
            'warehouse/partials/_movement_row.html', 
            {'m': m},
        ) 
        for m in items
    )
    
    return JsonResponse({
        'ok': True, 
        'html': html, 
        'has_more': has_more, 
        'next_offset': offset + len(items),
    })


@require_GET
def stats_movements(request):
    days = request.GET.get('days', '14')
    days = (
        int(days) 
        if days.isdigit() and int(days) in services.CHART_PERIODS 
        else 14
    )
    
    return JsonResponse({
        'ok': True, 
        'days': days, 
        **services.movement_chart_data(days),
    })