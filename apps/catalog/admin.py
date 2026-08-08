from django.contrib import admin
import nested_admin

from .models import (
    Category, Product, ProductImage, Size, Color,
    ProductVariant, VariantImage, VariantSize,
)


# ──────────────────────────────────────────────
#  Старые инлайны (оставлены для обратной совместимости)
# ──────────────────────────────────────────────

class ProductImageInline(nested_admin.NestedTabularInline):
    model = ProductImage
    extra = 0
    fields = ['image', 'alt_text']


# ──────────────────────────────────────────────
#  Вложенные инлайны для цветовых вариантов
# ──────────────────────────────────────────────

class VariantImageInline(nested_admin.NestedTabularInline):
    model = VariantImage
    extra = 1
    fields = ['image', 'alt_text', 'order']


class VariantSizeInline(nested_admin.NestedTabularInline):
    model = VariantSize
    extra = 0
    fields = ['size', 'available']


class ProductVariantInline(nested_admin.NestedStackedInline):
    model = ProductVariant
    extra = 0
    fields = ['color', 'preview_image', 'price_override', 'order']
    inlines = [VariantImageInline, VariantSizeInline]
    show_change_link = False


# ──────────────────────────────────────────────
#  Основные регистрации
# ──────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


from django.utils.html import format_html

@admin.register(Product)
class ProductAdmin(nested_admin.NestedModelAdmin):
    list_display = ['image_preview', 'name', 'order', 'price', 'category', 'status', 'created_at']
    list_display_links = ['image_preview', 'name']
    list_filter = ['status', 'created_at', 'category']
    list_editable = ['order', 'price', 'status']
    ordering = ['order', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['sizes', 'colors']

    def image_preview(self, obj):
        image = obj.images.first()
        if image and image.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover; border-radius: 4px;" />',
                image.image.url
            )
        return format_html('<div style="width: 50px; height: 50px; background-color: #eee; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: #999; font-size: 10px;">Нет фото</div>')
    image_preview.short_description = 'Фото'
    fieldsets = (
        (None, {
            'fields': (
                'category', 'name', 'slug', 'description',
                'price', 'status', 'order', 'material', 'density',
                'sizes', 'colors',
            )
        }),
    )
    inlines = [ProductImageInline, ProductVariantInline]

    class Media:
        css = {
            'all': ('admin/css/variants.css',)
        }


@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    pass


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex_code']
