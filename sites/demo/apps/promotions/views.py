from django.views.generic import TemplateView, RedirectView
from django.core.urlresolvers import reverse

from oscar.apps.catalogue.views import ProductFacetedCategoryView

class HomeView(ProductFacetedCategoryView):
    """
    This is the home page and will typically live at /
    """
    template_name = 'promotions/home.html'

    def get(self, request, *args, **kwargs):
        self.get_object()
        self.get_searchqueryset()
        return super(
            ProductFacetedCategoryView, self).get(request, *args, **kwargs)