from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone


class Category(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    color = models.CharField(
        'Цвет метки', 
        max_length=20, 
        default='blue',
        help_text='Цвет из палитры Tabler: blue, green, red, orange, purple, cyan',
    )

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField('Название', max_length=150)
    contact_person = models.CharField('Контактное лицо', max_length=100, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    email = models.EmailField('E-mail', blank=True)

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):    
    def active(self):
        return self.filter(is_archived=False)

    def low_stock(self):
        return self.active().filter(quantity__lte=F('min_quantity'))


class Product(models.Model): 
    UNIT_CHOICES = [
        ('pcs', 'шт.'),
        ('pack', 'упак.'),
        ('kg', 'кг'),
        ('l', 'л'),
        ('m', 'м'),
    ]

    sku = models.CharField('Артикул', max_length=30, unique=True)
    name = models.CharField('Наименование', max_length=200)
    category = models.ForeignKey(
        Category, 
        on_delete=models.PROTECT,
        related_name='products', 
        verbose_name='Категория',
    )
    supplier = models.ForeignKey(
        Supplier, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='products', 
        verbose_name='Поставщик',
    )
    unit = models.CharField('Ед. изм.', max_length=10, choices=UNIT_CHOICES, default='pcs')
    price = models.DecimalField('Цена, ₽', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Остаток', default=0)
    min_quantity = models.PositiveIntegerField('Минимальный остаток', default=5)
    is_archived = models.BooleanField('В архиве', default=False)
    
    search_text = models.CharField(max_length=300, blank=True, editable=False)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Изменён', auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return f'{self.sku} — {self.name}'

    def save(self, *args, **kwargs):
        self.search_text = f'{self.sku} {self.name}'.lower()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('warehouse:product_detail', args=[self.pk])

    @property
    def is_low_stock(self):
        return self.quantity <= self.min_quantity

    @property
    def stock_value(self):
        return self.price * self.quantity

    @property
    def status_label(self):
        if self.quantity == 0:
            return 'Нет в наличии'
        if self.is_low_stock:
            return 'Заканчивается'
        return 'В наличии'

    @property
    def status_color(self):
        if self.quantity == 0:
            return 'red'
        if self.is_low_stock:
            return 'orange'
        return 'green'


class StockMovement(models.Model):    
    IN = 'in'
    OUT = 'out'
    TYPE_CHOICES = [(IN, 'Приход'), (OUT, 'Расход')]

    product = models.ForeignKey(
        Product, 
        on_delete=models.CASCADE,
        related_name='movements', 
        verbose_name='Товар',
    )
    movement_type = models.CharField('Тип', max_length=3, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField('Количество')
    comment = models.CharField('Комментарий', max_length=255, blank=True)
    created_at = models.DateTimeField('Дата', default=timezone.now)

    class Meta:
        verbose_name = 'Движение товара'
        verbose_name_plural = 'Движения товаров'
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.movement_type == self.IN else '-'
        return f'{self.product.name}: {sign}{self.quantity}'