import json

json_string = '{"tagcommander_click":"\\n    tc_events_19(this,\\u0027clic\\u0027,{\\n    \\u0027event_type\\u0027:\\u0027navigation\\u0027,\\n    \\u0027level2\\u0027:\\u002722\\u0027,\\n    \\u0027event_chapter1\\u0027:\\u0027recherche_Club\\u0027,\\n    \\u0027event_chapter2\\u0027:\\u0027infrastructure\\u0027,\\n    \\u0027event_name\\u0027:\\u0027fiche_club\\u0027}"}'

json_string = '"tagcommander_click":"\n    tc_events_19(this,\u0027clic\u0027,{\n    \u0027event_type\u0027:\u0027navigation\u0027,\n    \u0027level2\u0027:\u002722\u0027,\n    \u0027event_chapter1\u0027:\u0027recherche_Club\u0027,\n    \u0027event_chapter2\u0027:\u0027infrastructure\u0027,\n    \u0027event_name\u0027:\u0027fiche_club\u0027"}'
# Décoder la chaîne JSON
decoded_data = json.loads(json_string)

# Accéder aux valeurs dans le dictionnaire résultant
tagcommander_click_value = decoded_data["tagcommander_click"]

print(tagcommander_click_value)
