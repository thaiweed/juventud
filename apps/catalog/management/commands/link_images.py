import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.catalog.models import Product, ProductImage

class Command(BaseCommand):
    help = 'Links uploaded images in media/products to existing products'

    def handle(self, *args, **kwargs):
        media_products_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        if not os.path.exists(media_products_dir):
            self.stdout.write(self.style.ERROR(f'Directory not found: {media_products_dir}'))
            return

        files = os.listdir(media_products_dir)
        self.stdout.write(f'Found {len(files)} files in {media_products_dir}')

        for filename in files:
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue

            # Remove extension and _front/_back suffixes to find product name
            name_part = os.path.splitext(filename)[0]
            
            # Helper logic to match filenames like 'Hunting_club_grey_zip_hoodie_front' to 'Hunting club grey zip hoodie'
            # We try to match by replacing underscores with spaces and checking if product exists.
            
            clean_name = name_part.replace('_front', '').replace('_back', '').replace('_', ' ').strip()
            
            # Case insensitive search
            products = Product.objects.filter(name__iexact=clean_name)
            
            if not products.exists():
                # Try partial match or fuzzy logic if needed, but strict for now
                self.stdout.write(self.style.WARNING(f'No matching product found for file: {filename} (Tried: "{clean_name}")'))
                continue

            product = products.first()
            
            # Check if image already exists to avoid duplicates
            relative_path = f'products/{filename}'
            if ProductImage.objects.filter(product=product, image=relative_path).exists():
                self.stdout.write(f' - Image already linked: {filename} -> {product.name}')
                continue

            ProductImage.objects.create(product=product, image=relative_path)
            self.stdout.write(self.style.SUCCESS(f' + Linked: {filename} -> {product.name}'))
