from datetime import timedelta
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from .models import Product, StockMovement


PER_PAGE_OPTIONS = (9, 15, 21)
HISTORY_PAGE_SIZE = 9
CHART_PERIODS = (7, 14, 30)


class StockError(Exception):
    pass


@transaction.atomic
def register_movement(product_id, movement_type, quantity, comment=''):
    product = Product.objects.get(pk=product_id)

    if movement_type not in (StockMovement.IN, StockMovement.OUT):
        raise StockError('Неизвестный тип операции')
    
    if quantity <= 0:
        raise StockError('Количество должно быть больше нуля')
    
    if product.is_archived:
        raise StockError('Товар в архиве, операции с ним недоступны')
    
    if movement_type == StockMovement.OUT and quantity > product.quantity:
        raise StockError(
            f'Недостаточно товара: на складе {product.quantity} {product.get_unit_display()}'
        )

    if movement_type == StockMovement.IN:
        product.quantity += quantity
    else:
        product.quantity -= quantity

    product.save(update_fields=['quantity', 'updated_at'])

    movement = StockMovement.objects.create(
        product=product,
        movement_type=movement_type,
        quantity=quantity,
        comment=comment,
    )
    
    return product, movement


def filter_products(params):
    qs = Product.objects.active().select_related('category', 'supplier')

    q = params.get('q', '').strip().lower()
    if q:
        qs = qs.filter(search_text__contains=q)

    category = params.get('category', '')
    if category.isdigit():
        qs = qs.filter(category_id=int(category))

    if params.get('low') == '1':
        qs = qs.filter(quantity__lte=F('min_quantity'))

    return qs


def build_product_list_context(params):
    per_page_str = params.get('per_page', '')
    
    per_page = (
        int(per_page_str)
        if per_page_str.isdigit() and int(per_page_str) in PER_PAGE_OPTIONS
        else PER_PAGE_OPTIONS[0]
    )

    paginator = Paginator(filter_products(params), per_page)
    page_obj = paginator.get_page(params.get('page'))

    return {
        'page_obj': page_obj,
        'products': page_obj.object_list,
        'page_range': paginator.get_elided_page_range(
            page_obj.number, on_each_side=1, on_ends=1
        ),
        'per_page': per_page,
    }


def dashboard_stats():
    active = Product.objects.active()
    
    value_expr = ExpressionWrapper(
        F('price') * F('quantity'),
        output_field=DecimalField(max_digits=14, decimal_places=2)
    )
    week_ago = timezone.now() - timedelta(days=7)

    return {
        'products_count': active.count(),
        'total_value': active.aggregate(total=Sum(value_expr))['total'] or 0,
        'low_stock_count': Product.objects.low_stock().count(),
        'movements_week': StockMovement.objects.filter(created_at__gte=week_ago).count(),
    }


def movement_chart_data(days):
    start = timezone.localdate() - timedelta(days=days - 1)
    dates = [start + timedelta(days=i) for i in range(days)]

    income = {d: 0 for d in dates}
    outcome = {d: 0 for d in dates}

    rows = (
        StockMovement.objects
        .filter(created_at__date__gte=start)
        .annotate(day=TruncDate('created_at'))
        .values('day', 'movement_type')
        .annotate(total=Sum('quantity'))
    )

    for row in rows:
        target = income if row['movement_type'] == StockMovement.IN else outcome
        target[row['day']] = row['total']

    return {
        'labels': [d.strftime('%d.%m') for d in dates],
        'income': [income[d] for d in dates],
        'outcome': [outcome[d] for d in dates],
    }

CATALOG_PAGE_SIZE = 8

CATALOG_ORDERING = {
    'name': 'name',
    '-name': '-name',
    'price': 'price',
    '-price': '-price',
    'quantity': 'quantity',
    '-quantity': '-quantity',
    '-updated_at': '-updated_at',
}

CATALOG_STATUSES = ('in_stock', 'low', 'out')


def catalog_queryset(params):
    qs = Product.objects.active().select_related('category')

    search = params.get('search', '').strip().lower()
    if search:
        qs = qs.filter(search_text__contains=search)

    category = params.get('category', '')
    if category.isdigit():
        qs = qs.filter(category_id=int(category))

    status = params.get('status', '')
    if status == 'in_stock':
        qs = qs.filter(quantity__gt=F('min_quantity'))
    elif status == 'low':
        qs = qs.filter(quantity__gt=0, quantity__lte=F('min_quantity'))
    elif status == 'out':
        qs = qs.filter(quantity=0)

    ordering = CATALOG_ORDERING[params.get('ordering', 'name')]
    return qs.order_by(ordering, 'pk')
