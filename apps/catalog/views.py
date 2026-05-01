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
        return super().get_queryset().filter(available=True).select_related('category').prefetch_related('images__color', 'sizes', 'colors__images')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        # Build JSON data for Alpine.js gallery
        images_data = []
        for img in product.images.all():
            images_data.append({
                'url': img.image.url,
                'alt': img.alt_text or product.name,
                'color_id': img.color_id,
            })

        colors_data = []
        for color in product.colors.all():
            colors_data.append({
                'id': color.id,
                'name': color.name,
            })

        context['product_images_json'] = json.dumps(images_data)
        context['product_colors_json'] = json.dumps(colors_data)
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['catalog/partials/product_detail_content.html']
        return super().get_template_names()
