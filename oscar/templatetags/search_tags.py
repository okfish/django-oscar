from django import template
from django.template.loader import render_to_string

from oscar.core.loading import get_class

from settings import OSCAR_SEARCH_FACETS

register = template.Library()

DEFAULT_FACET_WIDGET = 'search.widgets.SimpleLink'

@register.tag
def render_facet(parser, token):
    """
    Renders facet field using widget class defined in settings
    Takes two args: field name and field data
    """
    args = token.split_contents()
    if len(args) < 3:
        raise template.TemplateSyntaxError(
            "render_facet tag requires a facet field and its data to be passed")
    return FacetFieldNode(args[1], args[2])


class FacetFieldNode(template.Node):
    """
    Renders facet field defined in settings using widget class. 
    If no widget found use default template.
    """
    def __init__(self, field, data):
        self.field = template.Variable(field)
        self.data = template.Variable(data)
        #self.form = template.Variable(form)
    def render(self, context):
        field = self.field.resolve(context)
        data = self.data.resolve(context)
        #search_form = self.form.resolve(context)
        
        FacetWidgetClass = get_widget_class(field)
        # Widget class should be retrived anyway but
        # if not - silently die
        
        if FacetWidgetClass:
            return FacetWidgetClass(field, data).render()
        else:
            return '' 
            
def get_widget_class(field):
    widget_module, widget_class = DEFAULT_FACET_WIDGET.rsplit('.',1)
    for facets in OSCAR_SEARCH_FACETS.values():
        for key, facet in facets.items():
            if key == field:
                if facet.get('widget'):
                    widget_module, widget_class = facet['widget'].rsplit('.',1)
                return get_class(widget_module, widget_class)
