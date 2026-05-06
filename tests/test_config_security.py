import unittest

from cryptography.fernet import Fernet

from app.config import Config


class ConfigSecurityTest(unittest.TestCase):
    def setUp(self):
        self.original = {
            "ENV": Config.ENV,
            "TESTING": Config.TESTING,
            "SECRET_KEY": Config.SECRET_KEY,
            "JWT_SECRET": Config.JWT_SECRET,
            "ENCRYPTION_KEY": Config.ENCRYPTION_KEY,
            "SECRET_KEY_CONFIGURED": Config.SECRET_KEY_CONFIGURED,
            "JWT_SECRET_CONFIGURED": Config.JWT_SECRET_CONFIGURED,
            "ENCRYPTION_KEY_CONFIGURED": Config.ENCRYPTION_KEY_CONFIGURED,
        }

    def tearDown(self):
        for name, value in self.original.items():
            setattr(Config, name, value)

    def configure_production(self, secret, jwt_secret, encryption_key, configured=True):
        Config.ENV = "production"
        Config.TESTING = False
        Config.SECRET_KEY = secret
        Config.JWT_SECRET = jwt_secret
        Config.ENCRYPTION_KEY = encryption_key
        Config.SECRET_KEY_CONFIGURED = configured
        Config.JWT_SECRET_CONFIGURED = configured
        Config.ENCRYPTION_KEY_CONFIGURED = configured

    def test_production_rejects_generated_or_missing_secret_sources(self):
        self.configure_production(
            secret="generated-secret-that-is-long-enough",
            jwt_secret="generated-jwt-secret-that-is-long-enough",
            encryption_key=Fernet.generate_key().decode(),
            configured=False,
        )

        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY, JWT_SECRET, ENCRYPTION_KEY"):
            Config.validate()

    def test_production_rejects_placeholder_values(self):
        self.configure_production(
            secret="replace-with-a-long-random-secret",
            jwt_secret="replace-with-a-different-long-random-secret",
            encryption_key="",
        )

        with self.assertRaisesRegex(RuntimeError, "SECRET_KEY, JWT_SECRET, ENCRYPTION_KEY"):
            Config.validate()

    def test_production_rejects_invalid_fernet_key(self):
        self.configure_production(
            secret="a-realistic-production-secret-value",
            jwt_secret="a-different-production-jwt-secret-value",
            encryption_key="not-a-fernet-key",
        )

        with self.assertRaisesRegex(RuntimeError, "valid Fernet key"):
            Config.validate()

    def test_production_accepts_explicit_strong_values(self):
        self.configure_production(
            secret="a-realistic-production-secret-value",
            jwt_secret="a-different-production-jwt-secret-value",
            encryption_key=Fernet.generate_key().decode(),
        )

        Config.validate()


if __name__ == "__main__":
    unittest.main()
