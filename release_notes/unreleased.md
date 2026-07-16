* Migrated the connector to the Splunk SOAR SDK; the app is now Python 3.13 / 3.14 compatible, replacing the retired Python 3.9 runtime
* Re-implemented all existing actions on the SDK with identical action names, identifiers, parameters and output datapaths so existing playbooks keep working unchanged
* Added 38 new actions covering entity operations, per-entity maintenance windows, tenant and operations management, notes and labels, logical groups, blocklist and disruption tuning, Machine Learning Outliers, and asynchronous AI component-health advisors and routines
* Corrected legacy action endpoints that had drifted from the current TrackMe REST API (manage ack, request outlier models, run outliers monitor, add exclusion period, get tenants status)
* Added a per-request timeout asset option (default 300 seconds) and hardened response handling against unexpected payload shapes
* Removed the legacy beautifulsoup4 dependency; HTML error responses are now surfaced as plain text
* Refreshed the application logo and rewrote the in-app documentation
* Added logical group get, delete, and update members actions to round out logical group management
* Added event ingestion (on poll): TrackMe notable and stateful alert events are ingested as SOAR containers, deduplicated by event_id
