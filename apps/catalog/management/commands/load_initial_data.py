from django.core.management.base import BaseCommand
from apps.catalog.models import Category, Product, Size, Color
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Loads initial synthetic data for the catalog'

    def handle(self, *args, **kwargs):
        self.stdout.write('Creating Categories...')
        categories_data = ['tshirts', 'long sleeves', 'hoodies', 'accessories']
        categories = {}
        for cat_name in categories_data:
            cat, created = Category.objects.get_or_create(name=cat_name)
            categories[cat_name] = cat
            if created:
                self.stdout.write(f' - Created Category: {cat_name}')
            else:
                self.stdout.write(f' - Category already exists: {cat_name}')

        self.stdout.write('\nCreating Sizes...')
        sizes_data = ['S', 'M', 'L', 'XL']
        sizes = []
        for size_name in sizes_data:
            size, _ = Size.objects.get_or_create(name=size_name)
            sizes.append(size)

        self.stdout.write('\nCreating Colors...')
        colors_data = [
            {'name': 'Black', 'hex': '#000000'},
            {'name': 'White', 'hex': '#FFFFFF'},
            {'name': 'Grey', 'hex': '#808080'},
            {'name': 'Dark Grey', 'hex': '#A9A9A9'},
        ]
        colors = {}
        for color_data in colors_data:
            color, _ = Color.objects.get_or_create(name=color_data['name'], defaults={'hex_code': color_data['hex']})
            colors[color_data['name']] = color

        self.stdout.write('\nCreating Products...')
        
        products_data = [
            {
                'name': 'Hunting club grey zip hoodie',
                'category': 'hoodies',
                'price': 5000,
                'description': 'Premium heavyweight cotton zip hoodie with custom print. Perfect for everyday wear.',
                'material': '100% Cotton',
                'density': '400 g/m2',
                'colors': ['Grey'],
            },
            {
                'name': 'Hunting prohibited area white tee',
                'category': 'tshirts',
                'price': 2500,
                'description': 'Classic fit white t-shirt featuring exclusive graphic design.',
                'material': '100% Cotton',
                'density': '240 g/m2',
                'colors': ['White'],
            },
            {
                'name': 'Juventud oscuridad hoodie',
                'category': 'hoodies',
                'price': 4500,
                'description': 'Oversized black hoodie with unique "Oscuridad" print.',
                'material': 'Cotton Blend',
                'density': '380 g/m2',
                'colors': ['Black'],
            },
            {
                'name': 'Juventud woe blade black tee',
                'category': 'tshirts',
                'price': 2000,
                'description': 'Streetwear style black tee with sharp blade graphic.',
                'material': '100% Cotton',
                'density': '220 g/m2',
                'colors': ['Black'],
            },
            {
                'name': 'National park dark grey distressed cap',
                'category': 'accessories',
                'price': 3000,
                'description': 'Vintage style distressed cap with embroidered logo.',
                'material': 'Canvas',
                'density': None,
                'colors': ['Dark Grey'],
            },
            {
                'name': 'Public hunting land white long sleeve',
                'category': 'long sleeves',
                'price': 3000,
                'description': 'Long sleeve shirt with "Public Hunting Land" print. Comfortable fit.',
                'material': '100% Cotton',
                'density': '260 g/m2',
                'colors': ['White'],
            }
        ]

        for prod_data in products_data:
            cat = categories.get(prod_data['category'])
            if not cat:
                self.stdout.write(self.style.WARNING(f"Category {prod_data['category']} not found for {prod_data['name']}"))
                continue

            product, created = Product.objects.get_or_create(
                name=prod_data['name'],
                defaults={
                    'category': cat,
                    'price': prod_data['price'],
                    'description': prod_data['description'],
                    'material': prod_data['material'],
                    'density': prod_data['density'],
                }
            )
            
            if created:
                self.stdout.write(f' - Created Product: {prod_data["name"]}')
                product.sizes.set(sizes) # Add all sizes by default for clothes
                
                # Add specific colors
                for color_name in prod_data.get('colors', []):
                    if color_name in colors:
                        product.colors.add(colors[color_name])
                
                product.save()
            else:
                self.stdout.write(f' - Product already exists: {prod_data["name"]}')

        self.stdout.write(self.style.SUCCESS('\nSuccessfully loaded initial data'))
