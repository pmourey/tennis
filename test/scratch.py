import re

from common import check_license

# ranking_value = '15/4 (ex 15)'
# ranking_value = 'N20 (ex N40)'
# ranking_value = '-4/6 (ex N40)'
# ranking_value = 'N20'
# match = re.match(r'(\d+/\d+)\s*\(ex\s*(\d+)\)', ranking_value)
# a, b, c = ranking_value.split(' ')
# print(a, c[:-1])

# current_ranking_value = match.group(1)  # Récupère "15/4"
# best_ranking = match.group(2)  # Récupère "15"
#
# print(current_ranking_value)
# print(best_ranking)

license = '123 456 456 L'

license_ok = check_license(license)

print(license_ok)