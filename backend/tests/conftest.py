"""Set isolated test secrets before importing the application."""

import os


os.environ["JWT_SECRET_KEY"] = "gridwatch-test-secret-only-01234567890123456789"
os.environ["POSTGRES_PASSWORD"] = "gridwatch-test-database-password"
os.environ["MQTT_ENABLED"] = "false"
os.environ["TRUSTED_HOSTS"] = "testserver,127.0.0.1,localhost"
