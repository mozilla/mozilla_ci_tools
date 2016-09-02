from mozci.platforms import get_SETA_interval_dict
import json
print json.dumps(get_SETA_interval_dict(), indent=4, sort_keys=True)
