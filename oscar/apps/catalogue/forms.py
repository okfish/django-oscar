from oscar.apps.search.forms import SearchForm


class CategoryFacetForm(SearchForm):

    def no_query_found(self):
        """
        By default the category view should return all items in a category
        """
        return self.searchqueryset.all()
