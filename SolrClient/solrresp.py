import json
from collections import OrderedDict

from .exceptions import *

class SolrResponse:
    def __init__(self,data):
        self.data = data
        self.query_time = data['responseHeader']['QTime']
        self.header = data['responseHeader']
        
        if 'response' in data:
            self.grouped = False
            self.docs = data['response']['docs']
            if 'numFound' in data['response']:
                self.num_found = data['response']['numFound']
        elif 'grouped' in data:
            self.groups = {}
            self.grouped = True
            for field in data['grouped']:
                self.groups[field + '_ngroups'] = data['grouped'][field]['ngroups']
                self.groups[field + '_matches'] = data['grouped'][field]['matches']
                self.docs = data['grouped'][field]['groups']
        else:
            self.grouped = False
            self.docs = {}
        
        for doc in self.docs:
            for field in doc:
                if type(doc[field]) == str and doc[field].isdigit():
                    doc[field] = int(doc[field])
                    
    def get_num_found(self):
        '''
        Returns number of documents found on an ungrounded query. ::
        
            >>> res = solr.query('SolrClient_unittest',{
                    'q':'*:*',
                    'facet':True,
                    'facet.field':'facet_test',
            })
            >>> res.get_num_found()
            50
            
        '''
        return self.num_found
        
    def get_results_count(self):
        '''
        Returns the number of documents returned in current query. ::
            
            >>> res = solr.query('SolrClient_unittest',{
                'q':'*:*',
                'facet':True,
                'facet.field':'facet_test',
                })
            >>>
            >>> res.get_results_count()
            10
            >>> res.get_num_found()
            50
        
        '''
    
        return len(self.docs)
    
    def get_facets(self):
        '''
        Returns a dictionary of facets::
        
            >>> res = solr.query('SolrClient_unittest',{
                    'q':'product_name:Lorem',
                    'facet':True,
                    'facet.field':'facet_test',
            })... ... ... ...
            >>> res.get_results_count()
            4
            >>> res.get_facets()
            {'facet_test': {'ipsum': 0, 'sit': 0, 'dolor': 2, 'amet,': 1, 'Lorem': 1}}
            
        '''
        if not hasattr(self,'facets'):
            self.facets = OrderedDict()
            data = self.data
            if 'facet_counts' in data.keys() and type(data['facet_counts']) == dict:
                if 'facet_fields' in data['facet_counts'].keys() and type(data['facet_counts']['facet_fields']) == dict:
                    for facetfield in data['facet_counts']['facet_fields']:
                        if type(data['facet_counts']['facet_fields'][facetfield] == list):
                            l = data['facet_counts']['facet_fields'][facetfield]
                            self.facets[facetfield] = OrderedDict(zip(l[::2],l[1::2]))
                return self.facets
            else:
                raise SolrResponseError("No Facet Information in the Response")
        else:
            return self.facets
    
    def get_cursor(self):
        '''
        If you asked for the cursor in your query, this will return the next cursor mark. 
        '''
        if 'nextCursorMark' in self.data:
            return self.data['nextCursorMark']
        else:
            raise SolrResponseError("No Cursor Mark in the Response")
    
    def get_facets_ranges(self):
        '''
        Returns query facet ranges ::
        
            >>> res = solr.query('SolrClient_unittest',{
                'q':'*:*',
                'facet':True,
                'facet.range':'price',
                'facet.range.start':0,
                'facet.range.end':100,
                'facet.range.gap':10
                })
            >>> res.get_facets_ranges()
            {'price': {'80': 9, '10': 5, '50': 3, '20': 7, '90': 3, '70': 4, '60': 7, '0': 3, '40': 5, '30': 4}}

        '''
        if not hasattr(self,'facet_ranges'):
            self.facet_ranges = {}
            data = self.data
            if 'facet_counts' in data.keys() and type(data['facet_counts']) == dict:
                if 'facet_ranges' in data['facet_counts'].keys() and type(data['facet_counts']['facet_ranges']) == dict:
                    for facetfield in data['facet_counts']['facet_ranges']:
                        if type(data['facet_counts']['facet_ranges'][facetfield]['counts']) == list:
                            l = data['facet_counts']['facet_ranges'][facetfield]['counts']
                            self.facet_ranges[facetfield] = dict(zip(l[::2],l[1::2]))
                    return self.facet_ranges
            else:
                raise SolrResponseError("No Facet Ranges in the Response")
        else:
            return self.facet_ranges
    
    
    def get_facet_pivot(self):
        '''
        Parses facet pivot response. Example::
            >>> res = solr.query('SolrClient_unittest',{
            'q':'*:*',
            'fq':'price:[50 TO *]',
            'facet':True,
            'facet.pivot':'facet_test,price' #Note how there is no space between fields. They are just separated by commas
            })
            >>> res.get_facet_pivot()
            {'facet_test,price': {'Lorem': {89: 1, 75: 1}, 'ipsum': {53: 1, 70: 1, 55: 1, 89: 1, 74: 1, 93: 1, 79: 1}, 'dolor': {61: 1, 94: 1}, 'sit': {99: 1, 50: 1, 67: 1, 52: 1, 54: 1, 71: 1, 72: 1, 84: 1, 62: 1}, 'amet,': {68: 1}}}
        
        This method has built in recursion and can support indefinite number of facets. However, note that the output format is significantly massaged since Solr by default outputs a list of fields in each pivot field. 
        '''
        if not hasattr(self,'facet_pivot'):
            self.facet_pivot = {}
            if 'facet_counts' in self.data.keys():
                pivots = self.data['facet_counts']['facet_pivot']
                for fieldset in pivots:
                    self.facet_pivot[fieldset] = {}
                    for sub_field_set in pivots[fieldset]:
                        res = self._rec_subfield(sub_field_set)
                        self.facet_pivot[fieldset].update(res) 
                return self.facet_pivot
        else:
            return self.facet_pivot
        
    def _rec_subfield(self,sub_field_set):
        out = {}
        if type(sub_field_set) is list:
            for set in sub_field_set:
                if 'pivot' in set.keys():
                    out[sub_field_set['value']] = self._rec_subfield(set['pivot'])
                else:
                    out[set['value']] = set['count']
        elif type(sub_field_set) is dict:
            if 'pivot' in sub_field_set:
                out[sub_field_set['value']] = self._rec_subfield(sub_field_set['pivot'])
        return out
            
    def get_field_values_as_list(self,field):
        '''
        :param str field: The name of the field for which to pull in values. 
        Will parse the query results (must be ungrouped) and return all values of 'field' as a list. Note that these are not unique values.  Example::
        
            >>> r.get_field_values_as_list('product_name_exact')
            ['Mauris risus risus lacus. sit', 'dolor auctor Vivamus fringilla. vulputate', 'semper nisi lacus nulla sed', 'vel amet diam sed posuere', 'vitae neque ultricies, Phasellus ac', 'consectetur nisi orci, eu diam', 'sapien, nisi accumsan accumsan In', 'ligula. odio ipsum sit vel', 'tempus orci. elit, Ut nisl.', 'neque nisi Integer nisi Lorem']

        '''
        return [doc[field] for doc in self.docs if field in doc]
    
    #Not Sure what this one is doing or why I wrote it
    #Will find out later when migrating the rest of the code
    '''
    def get_fields_as_dict(self,field):
        out = {}
        for doc in self.docs:
            if field[0] in doc.keys() and field[1] in doc.keys():
                out[doc[field[0]]] = doc[field[1]]
        return out
        
    #Not Sure what this one is doing or why I wrote it   
    def get_fields_as_list(self,field):
        out = []
        for doc in self.docs:
            t = []
            for f in field:
                if f in doc.keys():
                    t.append(doc[f])
                else:
                    t.append("")
            if len(t)> 0:
                out.append(t)
        return out
    
    #Not Sure what this one is doing or why I wrote it
    def get_multi_fields_as_dict(self,fields):
        out = {}
        for doc in self.docs:
            if fields[0] in doc.keys():
                out[doc[fields[0]]] = {}
                for field in fields[1:]:
                    if field in doc.keys():
                        out[doc[fields[0]]][field] = doc[field]
        return out
    '''
    
    
    def get_first_field_values_as_list(self,field):
        '''
        :param str field: The name of the field for lookup. 
        
        Goes through all documents returned looking for specified field. At first encounter will return the field's value. 
        '''
        for doc in self.docs:
            if field in doc.keys():
                return doc[field]
        raise SolrResponseError("No field in result set")
        
    def get_facet_values_as_list(self,field):
        '''
        :param str field: Name of facet field to retrieve values from.
        
        Returns facet values as list for a given field. Example::
        
            >>> res = solr.query('SolrClient_unittest',{
                'q':'*:*',
                'facet':'true',
                'facet.field':'facet_test',
            })
            >>> res.get_facet_values_as_list('facet_test')
            [9, 6, 14, 10, 11]
            >>> res.get_facets()
            {'facet_test': {'Lorem': 9, 'ipsum': 6, 'amet,': 14, 'dolor': 10, 'sit': 11}}
            
        '''
        facets = self.get_facets()
        out = []
        if field in facets.keys():
            for facetfield in facets[field]:
                out.append(facets[field][facetfield])
            return out
        else:
            raise SolrResponseError("No field in facet output")
            
    def get_facet_keys_as_list(self,field):
        '''
        :param str field: Name of facet field to retrieve keys from.
        
        Similar to get_facet_values_as_list but returns the list of keys as a list instead. 
        Example::
        
            >>> r.get_facet_keys_as_list('facet_test')
            ['Lorem', 'ipsum', 'amet,', 'dolor', 'sit']

        '''
        facets = self.get_facets()
        if facets == -1:
            return facets
        if field in facets.keys():
            return facets[field].keys()
            
    def get_json(self):
        '''
        Returns json from the original response. 
        '''
        return json.dumps(self.data)