"""Use the signed-in gcloud identity.

Credentials are passed explicitly to clients. Tokens never enter logs/files.
"""
import datetime
import subprocess
import threading

from google.auth.credentials import Credentials


class GcloudCredentials(Credentials):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    def refresh(self, request):
        with self._lock:
            result = subprocess.run(
                ['gcloud', 'auth', 'print-access-token'],
                check=True, capture_output=True, text=True, timeout=30,
            )
            self.token = result.stdout.strip()
            if not self.token:
                raise RuntimeError('gcloud returned no access token')
            self.expiry = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + datetime.timedelta(minutes=40)

