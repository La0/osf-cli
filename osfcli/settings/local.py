LOG_LEVEL = 'DEBUG'

SENTRY_DSN = None

## Base URL for API server; used to fetch data
OSF_URL = 'https://osf.io'
API_BASE = 'https://api.osf.io'
FILE_BASE = 'https://files.osf.io'

# Interval (in seconds) to poll the OSF for server-side file changes
REMOTE_CHECK_INTERVAL = 60 * 5  # Every 5 minutes