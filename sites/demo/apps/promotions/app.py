from oscar.apps.promotions import app

from apps.promotions import views


class PromotionsApplication(app.PromotionsApplication):
    # Replace the category view with faceted category view
    home_view = views.HomeView
    # Replace the index view with faceted list view 
    #### REMOVED due to deprecated ProductListView
    #index_view = views.ProductFacetedListView


application = PromotionsApplication()
