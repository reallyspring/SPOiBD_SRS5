import random
from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from warehouse.models import Category, Product, StockMovement, Supplier

CATEGORIES = [
    ('Канцелярия', 'blue'),
    ('Бумага и бланки', 'cyan'),
    ('Оргтехника', 'purple'),
    ('Расходники для печати', 'orange'),
    ('Хозтовары', 'green'),
]

SUPPLIERS = [
    ('ООО «Канц-Опт»', 'Ирина Смирнова', '+7 (495) 000-11-22', 'opt@kanc.example'),
    ('ООО «ТехноСнаб»', 'Алексей Петров', '+7 (495) 000-33-44', 'sales@tehnosnab.example'),
    ('ИП Кузнецов А. В.', 'Андрей Кузнецов', '+7 (916) 000-55-66', 'kuznetsov@mail.example'),
    ('АО «БумТорг»', 'Мария Волкова', '+7 (812) 000-77-88', 'info@bumtorg.example'),
]

PRODUCTS = [
    ('KC-001', 'Ручка шариковая синяя, 0,7 мм', 'Канцелярия', 0, 'pcs', '25.00', 100),
    ('KC-002', 'Ручка гелевая чёрная', 'Канцелярия', 0, 'pcs', '45.00', 80),
    ('KC-003', 'Карандаш чернографитный HB', 'Канцелярия', 0, 'pcs', '18.00', 100),
    ('KC-004', 'Маркер-текстовыделитель жёлтый', 'Канцелярия', 2, 'pcs', '65.00', 40),
    ('KC-005', 'Степлер №24/6, до 25 листов', 'Канцелярия', 0, 'pcs', '390.00', 10),
    ('KC-006', 'Скобы для степлера №24/6, 1000 шт.', 'Канцелярия', 0, 'pack', '55.00', 30),
    ('KC-007', 'Скрепки металлические 28 мм, 100 шт.', 'Канцелярия', 2, 'pack', '40.00', 30),
    ('KC-008', 'Папка-регистратор А4, 75 мм', 'Канцелярия', 0, 'pcs', '210.00', 20),
    ('KC-009', 'Клей-карандаш 21 г', 'Канцелярия', 2, 'pcs', '70.00', 40),
    ('KC-010', 'Блок для записей с липким краем 76×76', 'Канцелярия', 0, 'pack', '95.00', 30),
    ('BM-001', 'Бумага офисная А4, 80 г/м², 500 л.', 'Бумага и бланки', 3, 'pack', '420.00', 50),
    ('BM-002', 'Бумага офисная А3, 80 г/м², 500 л.', 'Бумага и бланки', 3, 'pack', '890.00', 10),
    ('BM-003', 'Тетрадь общая А5, 96 л., клетка', 'Бумага и бланки', 3, 'pcs', '120.00', 30),
    ('BM-004', 'Блок бумаги для заметок 9×9 см', 'Бумага и бланки', 0, 'pcs', '150.00', 20),
    ('BM-005', 'Конверт С4 с отрывной лентой', 'Бумага и бланки', 3, 'pcs', '12.00', 200),
    ('BM-006', 'Журнал учёта посетителей, 96 л.', 'Бумага и бланки', 3, 'pcs', '260.00', 5),
    ('OT-001', 'Калькулятор настольный 12-разрядный', 'Оргтехника', 1, 'pcs', '850.00', 5),
    ('OT-002', 'Мышь беспроводная', 'Оргтехника', 1, 'pcs', '990.00', 8),
    ('OT-003', 'Клавиатура проводная USB', 'Оргтехника', 1, 'pcs', '1290.00', 5),
    ('OT-004', 'Флеш-накопитель USB 3.0, 64 ГБ', 'Оргтехника', 1, 'pcs', '690.00', 10),
    ('OT-005', 'Уничтожитель документов на 8 листов', 'Оргтехника', 1, 'pcs', '6490.00', 2),
    ('OT-006', 'Кабель витая пара UTP кат. 5e', 'Оргтехника', 1, 'm', '28.00', 100),
    ('RP-001', 'Картридж лазерный чёрный, ресурс 3000 стр.', 'Расходники для печати', 1, 'pcs', '2490.00', 5),
    ('RP-002', 'Тонер для лазерного принтера', 'Расходники для печати', 1, 'kg', '1850.00', 3),
    ('RP-003', 'Фотобарабан (драм-картридж)', 'Расходники для печати', 1, 'pcs', '3290.00', 2),
    ('RP-004', 'Чернила для струйного принтера, чёрные, 100 мл', 'Расходники для печати', 1, 'pcs', '390.00', 10),
    ('RP-005', 'Плёнка для ламинирования А4, 100 шт.', 'Расходники для печати', 2, 'pack', '780.00', 5),
    ('HT-001', 'Бумажные полотенца, 2 рулона', 'Хозтовары', 2, 'pack', '160.00', 20),
    ('HT-002', 'Мешки для мусора 60 л, 20 шт.', 'Хозтовары', 2, 'pack', '110.00', 20),
    ('HT-003', 'Средство для мытья стёкол, 500 мл', 'Хозтовары', 2, 'pcs', '180.00', 10),
    ('HT-004', 'Салфетки чистящие для оргтехники, 100 шт.', 'Хозтовары', 1, 'pack', '350.00', 10),
    ('HT-005', 'Жидкое мыло (на разлив)', 'Хозтовары', 2, 'l', '95.00', 20),
]

OUT_COMMENTS = [
    'Выдача в бухгалтерию', 'Выдача в отдел продаж', 'Выдача в IT-отдел',
    'Выдача на ресепшен', 'Заявка отдела кадров', 'Списание: брак',
]
IN_COMMENTS = [
    'Поставка по счёту №{}', 'Пополнение запаса', 'Поставка по договору №{}'
]

OUT_OF_STOCK = {'OT-005', 'RP-003'}  


class Command(BaseCommand):
    help = 'Заполняет базу: категории, поставщики, товары и история операций'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear', 
            action='store_true', 
            help='Сначала удалить все данные склада'
        )
        parser.add_argument(
            '--days', 
            type=int, 
            default=45, 
            help='За сколько дней создать историю'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)  

        if options['clear']:
            StockMovement.objects.all().delete()
            Product.objects.all().delete()
            Supplier.objects.all().delete()
            Category.objects.all().delete()
            self.stdout.write('Старые данные удалены')

        if Product.objects.exists():
            self.stdout.write(
                self.style.WARNING('В базе уже есть товары. Запусти с --clear, чтобы пересоздать.')
            )
            return

        categories = {
            name: Category.objects.create(name=name, color=color)
            for name, color in CATEGORIES
        }

        suppliers = [
            Supplier.objects.create(name=n, contact_person=c, phone=p, email=e)
            for n, c, p, e in SUPPLIERS
        ]

        now = timezone.now()
        days = options['days']
        movements = []

        for sku, name, category_name, supplier_idx, unit, price, min_q in PRODUCTS:
            product = Product.objects.create(
                sku=sku, 
                name=name, 
                unit=unit, 
                price=Decimal(price), 
                min_quantity=min_q,
                category=categories[category_name], 
                supplier=suppliers[supplier_idx],
            )

            stock = min_q * random.randint(2, 5)
            movements.append(StockMovement(
                product=product, 
                movement_type=StockMovement.IN, 
                quantity=stock,
                comment='Первичная поставка', 
                created_at=now - timedelta(days=days),
            ))

            for day in range(days - 1, -1, -1):
                moment = now - timedelta(
                    days=day, 
                    hours=random.randint(1, 9), 
                    minutes=random.randint(0, 59)
                )
                
                if random.random() < 0.45:
                    amount = random.randint(1, max(1, min_q // 3))
                    if amount <= stock:
                        stock -= amount
                        movements.append(StockMovement(
                            product=product, 
                            movement_type=StockMovement.OUT, 
                            quantity=amount,
                            comment=random.choice(OUT_COMMENTS), 
                            created_at=moment,
                        ))

                if stock <= min_q and random.random() < 0.4:
                    amount = min_q * random.randint(1, 3)
                    stock += amount
                    movements.append(StockMovement(
                        product=product, 
                        movement_type=StockMovement.IN, 
                        quantity=amount,
                        comment=random.choice(IN_COMMENTS).format(random.randint(100, 999)),
                        created_at=moment + timedelta(minutes=30),
                    ))

            if sku in OUT_OF_STOCK and stock > 0:
                movements.append(StockMovement(
                    product=product, 
                    movement_type=StockMovement.OUT, 
                    quantity=stock,
                    comment='Выдача по заявке', 
                    created_at=now - timedelta(hours=2),
                ))
                stock = 0

            product.quantity = stock
            product.save()

        StockMovement.objects.bulk_create(movements)

        self.stdout.write(self.style.SUCCESS(
            f'Готово: {len(categories)} категорий, {len(suppliers)} поставщиков, '
            f'{len(PRODUCTS)} товаров, {len(movements)} операций'
        ))