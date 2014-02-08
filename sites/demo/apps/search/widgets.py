from django.forms.widgets import HiddenInput
from django.template.loader import render_to_string

class AbstractFacetWidget(HiddenInput):
    attrs = {'name' : '',
             'items': '',
             }
    def __init__(self, field, data):
        self.attrs['name'] = data['name']
        self.attrs['items'] = data['results']
    
    def render(self, attrs=None):
        if not attrs:
            attrs = self.attrs
        return render_to_string(self.template_name, attrs)
    
    class Meta:
        abstract = True
    
class AlphabetList(AbstractFacetWidget):
    """
    Widget providing an alphabeted list of given facet data. 
    There is a problem with SearchForm fields handling, so subclassing of HiddenInput
    is not necessary at the moment but it should be proper way, i think :) 
    """
    template_name = 'search/partials/facet_abc.html'


class SimpleLink(AbstractFacetWidget):
    """
    Default widget. Renders select/deselect link on each facet
    As it implemented in Demo-site
    """
    template_name = 'search/partials/facet.html'
       