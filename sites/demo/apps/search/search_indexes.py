from haystack import indexes 
from django.db.models import get_model

from oscar.apps.search.search_indexes import ProductIndex as CoreProductIndex 

ProductAttributeValue = get_model('catalogue', 'ProductAttributeValue')

#Foreign keys for m2m relations of each attribute. Ugly but works :) 
#Maybe it makes sense to extend OSCAR_SEARCH_FACETS with that keys
#Hardcoded to ProductAttributeValues table content
ATTR_FKS = {
            'publisher': 5,
            'binding': 1,
            }

class ProductIndex(CoreProductIndex): 
    #Add Publisher and Binding attributes to index for faceting
    publisher = indexes.CharField(null=True, faceted=True)
    binding = indexes.CharField(null=True, faceted=True)
    
    def prepare_binding(self, obj):
        return self.prepare_attribute(obj, 'binding')
    
    def prepare_publisher(self, obj):
        return self.prepare_attribute(obj, 'publisher')

    def prepare_attribute(self, obj, attr_name):
        value = None
        try:
            value = obj.attribute_values.get(attribute=ATTR_FKS[attr_name]).value
        except ProductAttributeValue.DoesNotExist:
            pass
        return value