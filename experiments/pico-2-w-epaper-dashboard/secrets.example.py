# Copy this file to secrets.py and fill in the password.
# secrets.py is gitignored and must never be committed or printed.
WIFI_PASSWORD = "CHANGE_ME"
# HMAC-SHA256 key (hex) that signs OTA manifests; the same file feeds
# tools/ota_publish.py. Generate: python3 -c "import secrets; print(secrets.token_hex(32))"
OTA_KEY = ""
