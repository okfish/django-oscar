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
            # settings show_zeros in OSCAR_SEARCH_FACETS
            try: 
                if count == 0 and not facet['mincount'] == 0:
                    continue
            except KeyError:
                continue
            else:
                pass
            
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
            field_filter = '%s_exact' % facet['field']
            match = '%s_exact:%s' % (facet['field'], query)
            if match not in facet_counts['queries']:
                datum = {
                    'name': name,
                    'count': 0,
                }
            else:
                datum = {
                    'name': name,
                    'count': facet_counts['queries'][match],
                }
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

def append_to_sqs(sqs):
    """
    Takes facet fields and queries from settings.OSCAR_SEARCH_FACETS 
    and appends to SearchQuerySet 
    """
    for facet in settings.OSCAR_SEARCH_FACETS['fields'].values():
        mincount = 0 # Defaults for
        limit = 100  # Solr backend
        try:
            mincount, limit = facet['mincount'], facet['limit'] 
        except KeyError:
            pass
        sqs = sqs.facet(facet['field'], mincount=mincount, limit=limit)
    for facet in settings.OSCAR_SEARCH_FACETS['queries'].values():
        for query in facet['queries']:
            sqs = sqs.query_facet(facet['field'], query[1])
    return sqs