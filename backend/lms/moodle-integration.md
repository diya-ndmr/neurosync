# Local Moodle integration

NeuroSync's Moodle connection is optional. NeuroSync's CSV and local LMS features continue to work when Moodle is unavailable.

## Current local setup

- Local Moodle runs at `http://localhost` under WSL.
- Moodle Web Services and the REST protocol are enabled.
- The dedicated `neurosync_integration` account is authorized for the restricted `neurosync_local_readonly` service.
- The service exposes only `core_webservice_get_site_info`; it does not allow file upload or download.
- The REST-use permission is scoped to the hidden NeuroSync course context.
- The token is stored in the ignored `backend/.env` file. It is not part of frontend configuration or source control.

The Admin Settings page's **Test connection** action calls Moodle's `core_webservice_get_site_info` from the backend. The token is sent in a server-to-server POST body and is never returned by NeuroSync.

## Academic archive import

The hidden Moodle Database activity **NeuroSync academic core datasets (58,238 records)** contains the 16 selected academic dataset types from NeuroSync's local LMS database, stored as `dataset` and `record_json` fields. Import verification confirmed 58,238 entries and 116,476 field values. The separate 500-record synthetic risk activity remains intact.

This activity is an archive of JSON records, not native Moodle courses, enrolments, assignments, submissions, or gradebook items. The current REST connection check does not synchronize data in either direction, and the one-time archive import does not run automatically.

## Reconfiguring the local connection

If Moodle or NeuroSync is reinstalled:

1. In Moodle, enable web services and the REST protocol.
2. Create a dedicated local integration user and a restricted external service containing only the functions the integration needs. Keep file upload/download disabled.
3. Generate the service token in Moodle and store it as `MOODLE_TOKEN` in `backend/.env`; set `MOODLE_BASE_URL` to the local Moodle URL. Never put the token in frontend configuration, source control, or chat.
4. Grant only the capabilities needed by the service account, scoped to the relevant Moodle context.
5. Restart the NeuroSync backend and use **Admin → Settings → Moodle integration → Test connection**.

Before adding course, enrolment, assignment, or grade synchronization, add only the required Moodle functions and context-scoped capabilities, then implement and test explicit data mappings and duplicate/update rules.
