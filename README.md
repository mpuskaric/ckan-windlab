# ckan-windlab

This repository contains ckan extensions and other components used in WindLab Knowledge and Data Hub.

Developed by [MERIDIONAL](https://cordis.europa.eu/project/id/101084216) together with [FLOW](https://cordis.europa.eu/project/id/101084205) and [AIRE](https://cordis.europa.eu/project/id/101083716), [WindLab](https://windlab.hlrs.de) makes wind-sector datasets and knowledge easier to find, share and reuse [Link](https://meridional.eu/news/unlocking-wind-energy-data-new-video-presents-windlab-europes-knowledge-hub-for-the-wind-sector/). 


## Components
* ckan v2.10
Some extensions need to be cloned from other repositories
* ckanext-dcat - exposes and consume metadata as serialized RDF documents using DCAT [Link](https://github.com/ckan/ckanext-dcat); modified to include wind energy specific metadata
* ckanext-googleanalytics - needs to be cloned from https://github.com/ckan/ckanext-googleanalytics ; Repo contains further instructions
* ckanext-oaipmh-server  - exposes metadata in OAI-PMH format; available under https://github.com/mpuskaric/ckanext-oaipmh-server
* ckanext-spatial  - provides spatial context to the metadata template provided by 'ckanext-scheming'
* pyoai - part of the OAI-PMH module, modified for WindLab
* ckanext-facets - enables custom search facets for wind energy metadata
* ckanext-harvest - needs to be cloned from https://github.com/ckan/ckanext-harvest ; enables metadata harvesting in Ckan
* ckanext-scheming - enables custom metadata template for wind energy 
* ckanext-theme - custom theme for Windlab
* tag-vocabularies - enable adding metadata from the list of predefined tags
* zenodo - semantic harvesting module for extracting wind energy relevant metadata from Zenodo
* windlab_chat - a chatbot for WindLab (experimental) 



## /etc/ckan/default/ckan.ini configuration
```
ckan.plugins = activity stats text_view image_view recline_view scheming_datasets facets spatial_metadata spatial_query harvest ckan_harvester dcat dcat_rdf_harvester structured_data theme googleanalytics

```

