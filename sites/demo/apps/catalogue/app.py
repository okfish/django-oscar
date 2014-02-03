from oscar.apps.catalogue import app

from oscar.apps.catalogue import views


class CatalogueApplication(app.CatalogueApplication):
    # Replace the category view with faceted category view
    category_view = views.ProductFacetedCategoryView
    # Replace the index view with faceted list view
    index_view = views.ProductFacetedListView


application = CatalogueApplication()
