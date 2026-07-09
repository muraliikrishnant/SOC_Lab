from . import elastic, splunk

# Wazuh adapter intentionally deferred — see project notes. Add a "wazuh"
# entry here (mirroring splunk.py/elastic.py: normalize/writeback/poll)
# when that's back in scope.
ADAPTERS = {
    "splunk": splunk,
    "elastic": elastic,
}
