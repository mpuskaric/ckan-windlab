import logging

import collections

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

import json

log = logging.getLogger(__name__)

class FacetsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IFacets)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer
    '''
    def before_index(self, data_dict):
        data_dict['subject'] = json.loads(data_dict.get('subject', '[]'))
        data_dict['variable'] = json.loads(data_dict.get('variable', '[]'))
        return data_dict
    '''
    def dataset_facets(self,facets_dict,package_type):
        lang_code = toolkit.request.environ['CKAN_LANG']
        #facets_dict = collections.OrderedDict()
        facets_dict.clear() # removes existing default facets
        facets_dict['organization'] = plugins.toolkit._('Organizations')
        facets_dict['subject'] = plugins.toolkit._('Topics')
        facets_dict['conditions'] = plugins.toolkit._('External Conditions')
        facets_dict['variable'] = plugins.toolkit._('Variables')
        #facets_dict['tags'] = plugins.toolkit._('Tags')
        return facets_dict
    
    def organization_facets(self, facets_dict, organization_type, package_type):
        facets_dict.clear() # removes existing default facets
        facets_dict['organization'] = plugins.toolkit._('Organizations')
        facets_dict['subject'] = plugins.toolkit._('Topics')
        facets_dict['conditions'] = plugins.toolkit._('External Conditions')
        facets_dict['variable'] = plugins.toolkit._('Variables')
        return facets_dict

    def group_facets(self, facets_dict, group_type, package_type):
        return facets_dict
    
    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'facets')
