from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from .models import Product, Category
import json


class ProductListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset().filter(available=True).select_related('category').prefetch_related('images')
        category_slug = self.kwargs.get('slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=category)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        if self.kwargs.get('slug'):
            context['current_category'] = get_object_or_404(Category, slug=self.kwargs.get('slug'))
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['catalog/partials/product_list_full.html']
        return super().get_template_names()


class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return (
            super().get_queryset()
            .filter(available=True)
            .select_related('category')
            .prefetch_related(
                'images',
                'sizes',
                'variants__images',
                'variants__sizes__size',
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        variants = list(product.variants.all())
        has_variants = product.has_multiple_colors and len(variants) > 0

        # ── Данные для Alpine.js ──────────────────────────
        if has_variants:
            variants_data = []
            for v in variants:
                variants_data.append({
                    'id': v.id,
                    'preview_url': v.preview_image.url if v.preview_image else '',
                    'price': str(v.effective_price),
                    'images': [
                        {'url': img.image.url, 'alt': img.alt_text or product.name}
                        for img in v.images.all()
                    ],
                    'sizes': [
                        {'id': vs.size_id, 'name': vs.size.name, 'available': vs.available}
                        for vs in v.sizes.all()
                    ],
                })

            context['product_variants_json'] = json.dumps(variants_data)
            context['has_variants'] = True
            context['default_price'] = str(product.price)

        else:
            # Режим без вариантов — старая логика
            images_data = [
                {'url': img.image.url, 'alt': img.alt_text or product.name}
                for img in product.images.all()
            ]
            sizes_data = [
                {'id': s.id, 'name': s.name, 'available': True}
                for s in product.sizes.all()
            ]
            context['product_images_json'] = json.dumps(images_data)
            context['product_sizes_json'] = json.dumps(sizes_data)
            context['has_variants'] = False
            context['default_price'] = str(product.price)

        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['catalog/partials/product_detail_content.html']
        return super().get_template_names()
