from django.conf import settings
from django.core.urlresolvers import reverse, reverse_lazy

from purl import URL
from six.moves import map


def facet_data(request, form, results):  # noqa (too complex (10))
    """
    Convert Haystack's facet data into a more useful datastructure that
    templates can use without having to manually construct URLs
    """
    facet_data = {}
    base_url = URL(request.get_full_path())
    # URL for 'global' facet selection, e.g. filter for brands over all products 
    base_all_url = URL(reverse_lazy('catalogue:index').decode()) 
    facet_counts = results.facet_counts()
    stats_results = results.stats_results()
    # Field facets
    valid_facets = [f for f in form.selected_facets if ':' in f]
    selected = dict(
        map(lambda x: x.split(':', 1), valid_facets))
    for key, facet in settings.OSCAR_SEARCH_FACETS['fields'].items():
        facet_data[key] = {
            'name': facet['name'],
            'results': []}
        for name, count in facet_counts['fields'][key]:
            # Ignore zero-count facets for field with appropriate 
            # settings 'mincount' in OSCAR_SEARCH_FACETS
            if count == 0 and not facet.get('mincount', 0):
                continue
            
            field_filter = '%s_exact' % facet['field']
            datum = {
                'name': name,
                'count': count}
            if selected.get(field_filter, None) == name:
                # This filter is selected - build the 'deselect' URL
                datum['selected'] = True
                url = base_url.remove_query_param(
                    'selected_facets', '%s:%s' % (
                        field_filter, name))
                # Don't carry through pagination params
                if url.has_query_param('page'):
                    url = url.remove_query_param('page')
                datum['deselect_url'] = url.as_string()
            else:
                # This filter is not selected - built the 'select' URL
                datum['selected'] = False
                if count > 0:
                    url = base_url.append_query_param('selected_facets', 
                                                      '%s:%s' % (field_filter, name))
                # Don't carry through pagination params
                if url.has_query_param('page'):
                    url = url.remove_query_param('page')
                datum['select_url'] = url.as_string()
            # Even if facet has 0 count - build the 'select all' URL
            # for using in templates   
            select_all_url = base_all_url.query_param('selected_facets', 
                                                      '%s:%s' % (field_filter, name))
            datum['select_all_url'] = select_all_url.as_string()    
            facet_data[key]['results'].append(datum)

    # Query facets
    for key, facet in settings.OSCAR_SEARCH_FACETS['queries'].items():
        facet_data[key] = {
            'name': facet['name'],
            'results': []}
            
        
        
        for name, query in facet['queries']:
            datum = {
                    'name': name,
            }
            field_filter = '%s_exact' % facet['field']
            # 'dynamic' field handling for templates
            # get query from request if given
            if facet.get('type', None) == 'dynamic' and selected.get(field_filter, None):
                query = selected.get(field_filter, None)
                 
            match = '%s_exact:%s' % (facet['field'], query)
            if match not in facet_counts['queries']:
                datum['count'] = 0
            else:
                datum['count'] = facet_counts['queries'][match]
                #datum['stats'] = stats_results
                # Try to get field stats
                datum['stats'] = stats_results.get(facet['field'], None)
                
                if selected.get(field_filter, None) == query:
                    # Selected
                    datum['selected'] = True
                    url = base_url.remove_query_param(
                        'selected_facets', match)
                    datum['deselect_url'] = url.as_string()
                else:
                    datum['selected'] = False
                    url = base_url.append_query_param(
                        'selected_facets', match)
                    datum['select_url'] = url.as_string()
                facet_data[key]['results'].append(datum)

    return facet_data

def append_to_sqs(sqs, form=None):
    """
    Takes facet fields and queries from settings.OSCAR_SEARCH_FACETS 
    and appends to SearchQuerySet 
    """
    kwargs = {}
    for facet in settings.OSCAR_SEARCH_FACETS['fields'].values():
        mincount, limit = facet.get('mincount', None), facet.get('limit', None)
        if mincount:
            kwargs['mincount'] = mincount
        if limit:
            kwargs['limit'] = limit                  
        sqs = sqs.facet(facet['field'], **kwargs)
    for facet in settings.OSCAR_SEARCH_FACETS['queries'].values():
        query_type = facet.get('type', None)
        if query_type == 'dynamic':
            # If query has 'dynamic' type - check request vars for selected facet
            # if no request given use default value from settings
            # Also add stats query for that fields, e.g. to select min and max values
            field_filter = '%s_exact' % facet['field']
            query = facet['queries'][0][1] # The only default query allowed for 'dynamic' fields
            if form.selected_facets:
                for selected_facet in form.selected_facets:
                    if ":" not in selected_facet:
                        continue
                    field, value = selected_facet.split(":", 1)
                    if field == field_filter:
                        query = value
                    sqs = sqs.query_facet(facet['field'], query)
            else:
                sqs = sqs.query_facet(facet['field'], query)       
            sqs = sqs.stats(facet['field']) 
                
        else:        
            for query in facet['queries']:
                sqs = sqs.query_facet(facet['field'], query[1])
    return sqs