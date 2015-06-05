from mozci.sources.buildjson import _fetch_data, BUILDS_DAY_FILE
from mozci.utils.tzone import pacific_time as pt
from mozci.utils.tzone import utc_time as ut

builds = _fetch_data(BUILDS_DAY_FILE % "2015-02-23")

endtimes_list = []
for job in builds:
    endtimes_list.append(job["endtime"])

endtimes_list.sort()
print "%s %s %s" % (endtimes_list[0], ut(endtimes_list[0]), pt(endtimes_list[0]))
print "%s %s %s" % (endtimes_list[-1], ut(endtimes_list[-1]), pt(endtimes_list[-1]))
