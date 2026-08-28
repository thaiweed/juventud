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

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('catalog:product_list_by_category', kwargs={'slug': self.slug})

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

    material = models.CharField(max_length=100, blank=True, null=True)
    density = models.CharField(max_length=50, blank=True, null=True) # e.g. 300 g/m2

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('catalog:product_detail', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name


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
    name = models.CharField(
        max_length=200, null=True, blank=True,
        verbose_name='Название расцветки'
    )
    description = models.TextField(
        null=True, blank=True,
        verbose_name='Описание расцветки'
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Цена'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Цветовой вариант'
        verbose_name_plural = 'Цветовые варианты'

    @property
    def effective_price(self):
        return self.price if self.price is not None else getattr(self.product, 'price', 0)

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
        ordering = ['order', 'id']
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
