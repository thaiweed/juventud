from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок', db_index=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Size(models.Model):
    name = models.CharField(max_length=20) # e.g. S, M, L, XL
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок', db_index=True)
    
    class Meta:
        ordering = ['order', 'id']
        
    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50) # e.g. Red, Blue
    hex_code = models.CharField(max_length=7, blank=True, null=True) # e.g. #FF0000
    
    def __str__(self):
        return self.name

class Product(models.Model):
    categories = models.ManyToManyField(Category, related_name='products', blank=True, verbose_name='Категории')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    STATUS_CHOICES = (
        ('available', 'В наличии'),
        ('sold_out', 'Распродано (Sold Out)'),
        ('hidden', 'Скрыто (Не отображать на сайте)'),
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='available', 
        verbose_name='Статус'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    sizes = models.ManyToManyField(Size, blank=True)
    colors = models.ManyToManyField(Color, blank=True)

    material = models.CharField(max_length=100, blank=True, null=True)
    density = models.CharField(max_length=50, blank=True, null=True) # e.g. 300 g/m2

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    color = models.ForeignKey(Color, related_name='images', on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d')
    alt_text = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Image for {self.product.name}"


# ──────────────────────────────────────────────
#  Цветовые варианты
# ──────────────────────────────────────────────

class ProductVariant(models.Model):
    """Цветовой вариант товара."""
    product = models.ForeignKey(
        Product, related_name='variants', on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    color = models.ForeignKey(
        Color, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='Цвет',
        related_name='variants'
    )
    preview_image = models.ImageField(
        upload_to='variants/previews/%Y/%m/',
        verbose_name='Превью цвета',
        help_text='Маленькое изображение, используемое как кнопка выбора цвета'
    )
    name_override = models.CharField(
        max_length=200, null=True, blank=True,
        verbose_name='Название (переопределить)',
        help_text='Оставьте пустым, чтобы использовать основное название товара'
    )
    description_override = models.TextField(
        null=True, blank=True,
        verbose_name='Описание (переопределить)',
        help_text='Оставьте пустым, чтобы использовать основное описание товара'
    )
    price_override = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Цена (переопределить)',
        help_text='Оставьте пустым, чтобы использовать основную цену товара'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order']
        verbose_name = 'Цветовой вариант'
        verbose_name_plural = 'Цветовые варианты'

    @property
    def effective_price(self):
        return self.price_override if self.price_override is not None else self.product.price

    def __str__(self):
        return f"Вариант #{self.pk} — {self.product.name}"


class VariantImage(models.Model):
    """Фотография галереи конкретного цветового варианта."""
    variant = models.ForeignKey(
        ProductVariant, related_name='images', on_delete=models.CASCADE,
        verbose_name='Вариант'
    )
    image = models.ImageField(upload_to='variants/gallery/%Y/%m/', verbose_name='Изображение')
    alt_text = models.CharField(max_length=255, blank=True, verbose_name='Alt-текст')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order']
        verbose_name = 'Фото варианта'
        verbose_name_plural = 'Фото варианта'

    def __str__(self):
        return f"Фото для {self.variant}"


class VariantSize(models.Model):
    """Размер, доступный для конкретного цветового варианта."""
    variant = models.ForeignKey(
        ProductVariant, related_name='sizes', on_delete=models.CASCADE,
        verbose_name='Вариант'
    )
    size = models.ForeignKey(
        Size, on_delete=models.CASCADE,
        verbose_name='Размер'
    )
    available = models.BooleanField(default=True, verbose_name='В наличии')

    class Meta:
        ordering = ['size__order', 'size__id']
        unique_together = ('variant', 'size')
        verbose_name = 'Размер варианта'
        verbose_name_plural = 'Размеры варианта'

    def __str__(self):
        status = '✓' if self.available else '✗'
        return f"{self.size.name} {status}"
