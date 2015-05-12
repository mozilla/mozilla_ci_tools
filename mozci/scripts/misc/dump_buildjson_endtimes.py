from mozci.sources.buildjson import _fetch_buildjson_day_file
from mozci.utils.tzone import pacific_time as pt
from mozci.utils.tzone import utc_time as ut

builds = _fetch_buildjson_day_file("2015-02-23")

list = []
for job in builds:
    list.append(job["endtime"])

list.sort()
print "%s %s %s" % (list[0], ut(list[0]), pt(list[0]))
print "%s %s %s" % (list[-1], ut(list[-1]), pt(list[-1]))
