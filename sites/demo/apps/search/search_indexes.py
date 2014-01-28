from haystack import indexes 
from django.db.models import get_model
from oscar.core.loading import get_class
from django.core.exceptions import ImproperlyConfigured

from oscar.apps.search.search_indexes import ProductIndex as CoreProductIndex 
from settings import OSCAR_SEARCH_FACETS

# Load default strategy (without a user/request)
Selector = get_class('partner.strategy', 'Selector')
strategy = Selector().strategy()

ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')
ProductAttribute = get_model('catalogue', 'ProductAttribute')


# Foreign keys for m2m relations of each attribute to extract values. Ugly but works :) 
# Fill array with IDs of faceted attributes from ProductAttribute model depending
# on settings 
FACET_ATTR_IDS = {}

for key, facet in OSCAR_SEARCH_FACETS['fields'].items():
    try:
        FACET_ATTR_IDS[facet['field']] = ProductAttribute.objects.get(code = facet['field']).id
    except ProductAttribute.DoesNotExist: # If field is not attribute - pass it
        pass    

class ProductIndex(CoreProductIndex): 
    #Add Publisher and Binding attributes to index for faceting
    author = indexes.CharField(null=True, faceted=True)
    publisher = indexes.CharField(null=True, faceted=True)
    binding = indexes.CharField(null=True, faceted=True)
    size = indexes.MultiValueField(null=True, faceted=True)
    
    # Size, color etc can be assigned only to variant product  
    def prepare_size(self, obj):
        if obj.is_group:
            return [ self.get_attribute(v, 'size') for v in obj.variants.all() ]
        else:
            return self.get_attribute(obj, 'size')
        
    def prepare_binding(self, obj):
        if obj.is_group:
             # Don't return a binding attr for group products
             return None
        else:        
            return self.get_attribute(obj, 'binding')
    
    def prepare_author(self, obj):
        if obj.is_group:
             # Don't return a binding attr for group products
             return None
        else:        
            return self.get_attribute(obj, 'author')
    
    def prepare_publisher(self, obj):
        if obj.is_group: # Don't return a publisher attr for group products
            return None
        else:
            return self.get_attribute(obj, 'publisher')

    def get_attribute(self, obj, attr_name):
        value = None
        try:
            value = obj.attribute_values.get(attribute=FACET_ATTR_IDS[attr_name]).value
        except ProductAttributeValue.DoesNotExist:
            pass
        except KeyError:
            raise ImproperlyConfigured(("Attribute field '%s' not defined in settings"
                                        " or in database. Add attribute via admin UI"
                                        "or define it in settings.OSCAR_SEARCH_FACETS.") % attr_name)
        return value