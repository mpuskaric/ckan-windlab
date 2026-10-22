# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    # If you are changing from the default layout of your extension, you may
    # have to change the message extractors, you can read more about babel
    # message extraction at
    # http://babel.pocoo.org/docs/messages/#extraction-method-mapping-and-configuration
    
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    package_data={},
    data_files=[],

    entry_points='''
        [ckan.plugins]
        theme=ckanext.theme.plugin:ThemePlugin
    ''',

    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
