import pprint
from mozci.mozci import query_builders
builders = query_builders()
pprint.pprint(sorted(builders))
