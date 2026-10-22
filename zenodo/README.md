# Script for extracting wind energy relevant metadata from Zenodo 

Requirements:
* Zenodo token 
* metadata dump in the same folder
* Windlab token

Instructions:
* `python3 -m venv .`
* `source bin/activate`
* `pip install -r requirements.txt`
* `python zenodo_wind_energy.py`

Hosting: 
* the created `zenodo_wind_energy_records_update.jsonl` should be then hosted and harvested by ckan's ckanext-harvest module
