from mozci.sources.buildjson import _fetch_buildjson_day_file
jobs = _fetch_buildjson_day_file("2015-03-03")

for job in jobs:
    req_id = sorted(job.get("request_ids", []))
    prop_req_id = sorted(job["properties"].get("request_ids", []))

    if prop_req_id == [] and req_id != []:
        print "It is very rare that this will happen - %s" % job

    if len(prop_req_id) < len(req_id):
        print "It is even more rare that this will happen - %s" % job

    if req_id == [] and prop_req_id == [] and "Nightly" not in job["reason"]:
        print "Both request ids are empty - %s" % job

    if req_id != prop_req_id:
        print "Different req_ids - %s" % job
