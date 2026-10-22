# Tag vocabularies to enable entering metadata as predefined tags

Vocabularies:
* NEAT  https://data.windenergy.dtu.dk/ontologies/view/neat/en/
* EXTRACT https://data.windenergy.dtu.dk/ontologies/view/extract/en/
* ASPECT https://data.windenergy.dtu.dk/ontologies/view/aspect/en/

Instructions:

* create an admin API key
* create a vocabulary `curl -H "Authorization: <TOKEN>" -d '{"name": "aspect"}' http://<ckan>/api/3/action/vocabulary_create`
* populate vocabulary from a list `IFS=$'\n'
for i in `cat neat.list` ; do curl -H "Authorization: <TOKEN>" -d '{"name": "'"$i"'", "vocabulary_id": "<Vocabulary_ID>"}' http://<ckan>/api/3/action/tag_create ; done `
* repeat points 2 and 3 for `aspect` and `extract`
