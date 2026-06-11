from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Product, Category, ProductImage


def clear_product_list_cache():
    """Очищает весь кэш при изменении каталога."""
    cache.clear()


@receiver([post_save, post_delete], sender=Product)
def invalidate_on_product_change(sender, **kwargs):
    clear_product_list_cache()


@receiver([post_save, post_delete], sender=Category)
def invalidate_on_category_change(sender, **kwargs):
    clear_product_list_cache()


@receiver([post_save, post_delete], sender=ProductImage)
def invalidate_on_image_change(sender, **kwargs):
    clear_product_list_cache()
