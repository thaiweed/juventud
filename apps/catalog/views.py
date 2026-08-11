from django.views.generic import ListView, DetailView
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from .models import Product, Category
import json


class ProductListView(ListView):
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 100

    def get_queryset(self):
        queryset = super().get_queryset().exclude(status='hidden').prefetch_related(
            'categories', 
            'variants__images'
        )
        category_slug = self.kwargs.get('slug')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(categories=category)
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


@method_decorator(never_cache, name='dispatch')
class ProductDetailView(DetailView):
    model = Product
    template_name = 'catalog/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return (
            super().get_queryset()
            .exclude(status='hidden')
            .prefetch_related(
                'categories',
                'variants__images',
                'variants__sizes__size',
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object

        variants = list(product.variants.all())
        variants_data = []
        for v in variants:
            variants_data.append({
                'id': v.id,
                'name': v.name or product.name,
                'description': v.description or '',
                'preview_url': v.preview_image.url if v.preview_image else '',
                'price': str(v.price or 0),
                'images': [
                    {'url': img.image.url, 'alt': img.alt_text or v.name or product.name}
                    for img in v.images.all()
                ],
                'sizes': [
                    {'id': vs.size_id, 'name': vs.size.name, 'available': vs.available}
                    for vs in v.sizes.all()
                ],
            })

        context['product_variants_json'] = json.dumps(variants_data)
        context['has_multiple_colors'] = len(variants) > 1
        context['default_price'] = str(variants[0].price) if variants and variants[0].price else '0'
        return context

    def get_template_names(self):
        if self.request.headers.get('HX-Request'):
            return ['catalog/partials/product_detail_content.html']
        return super().get_template_names()

def about_us(request):
    """
    Renders the About Us page with brand history, project members, and photo gallery.
    """
    return render(request, 'catalog/about.html')
