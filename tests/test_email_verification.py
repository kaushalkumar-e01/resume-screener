"""Unit and API integration tests for email OTP verification, validation, and FastAPI endpoints."""

import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import email_verification as ev
from api_server import app
from validation import (
    TECHNICAL_ROLES,
    format_phone_for_region,
    validate_full_name,
    validate_phone_number,
)


class TestEmailVerificationAndApi(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-session-123"
        ev.clear_session_otps(self.session_id)
        self.client = TestClient(app)

    def tearDown(self):
        ev.clear_session_otps(self.session_id)

    def test_otp_generation_and_hashed_storage(self):
        sent = []
        ok, _ = ev.issue_otp(
            self.session_id,
            "Jane.Doe@Example.com",
            sender=lambda e, o: sent.append((e, o)),
            now=1000.0,
        )
        self.assertTrue(ok)
        self.assertEqual(len(sent), 1)
        to_email, otp = sent[0]
        self.assertEqual(to_email, "jane.doe@example.com")
        self.assertEqual(len(otp), 4)
        self.assertTrue(otp.isdigit())

        record = ev._OTP_STORE[self.session_id]
        self.assertNotIn(otp.encode("utf-8"), record.otp_hash)
        self.assertFalse(record.verified)

    def test_smtp_email_template_and_sending(self):
        mock_server = MagicMock()
        mock_smtp_cls = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        env_values = {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "sender@gmail.com",
            "SMTP_PASSWORD": "app-password-1234",
            "SMTP_FROM_EMAIL": "sender@gmail.com",
            "SMTP_USE_TLS": "true",
        }
        with patch("email_verification.get_setting", side_effect=lambda k, d="": env_values.get(k, d)):
            with patch("email_verification.smtplib.SMTP", mock_smtp_cls):
                ev.send_otp_email_smtp("candidate@example.com", "4829")

        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@gmail.com", "app-password-1234")
        mock_server.send_message.assert_called_once()
        msg = mock_server.send_message.call_args[0][0]
        self.assertEqual(msg["Subject"], "Email Verification – AI Resume Screening Portal")
        self.assertEqual(msg["To"], "candidate@example.com")
        body = msg.get_content()
        self.assertIn("4829", body)
        self.assertIn("5 minutes", body)
        self.assertIn("do not share", body.lower())

    def test_otp_expiration_after_5_minutes(self):
        sent = []
        ev.issue_otp(self.session_id, "a@b.com", sender=lambda e, o: sent.append(o), now=1000.0)
        ok, msg = ev.verify_otp(self.session_id, "a@b.com", sent[0], now=1301.0)
        self.assertFalse(ok)
        self.assertIn("expired", msg.lower())
        self.assertFalse(ev.is_email_verified(self.session_id, "a@b.com"))

    def test_max_5_incorrect_attempts(self):
        sent = []
        ev.issue_otp(self.session_id, "a@b.com", sender=lambda e, o: sent.append(o), now=1000.0)
        wrong = "0000" if sent[0] != "0000" else "9999"

        for i in range(4):
            ok, msg = ev.verify_otp(self.session_id, "a@b.com", wrong, now=1010.0 + i)
            self.assertFalse(ok)
            self.assertIn("remaining", msg.lower())

        ok, msg = ev.verify_otp(self.session_id, "a@b.com", wrong, now=1020.0)
        self.assertFalse(ok)
        self.assertIn("too many incorrect attempts", msg.lower())

        ok_after, _ = ev.verify_otp(self.session_id, "a@b.com", sent[0], now=1021.0)
        self.assertFalse(ok_after)
        self.assertFalse(ev.is_email_verified(self.session_id, "a@b.com"))

    def test_resend_cooldown_and_previous_otp_invalidation(self):
        sent = []
        ok1, _ = ev.issue_otp(self.session_id, "a@b.com", sender=lambda e, o: sent.append(o), now=1000.0)
        self.assertTrue(ok1)

        ok_early, msg_early = ev.issue_otp(self.session_id, "a@b.com", sender=lambda e, o: sent.append(o), now=1030.0)
        self.assertFalse(ok_early)
        self.assertIn("wait", msg_early.lower())

        ok2, _ = ev.issue_otp(self.session_id, "a@b.com", sender=lambda e, o: sent.append(o), now=1061.0)
        self.assertTrue(ok2)
        self.assertEqual(len(sent), 2)

        if sent[0] != sent[1]:
            ok_old, _ = ev.verify_otp(self.session_id, "a@b.com", sent[0], now=1062.0)
            self.assertFalse(ok_old)

        ok_new, _ = ev.verify_otp(self.session_id, "a@b.com", sent[1], now=1063.0)
        self.assertTrue(ok_new)
        self.assertTrue(ev.is_email_verified(self.session_id, "a@b.com"))

    def test_email_change_invalidates_verification(self):
        sent = []
        ev.issue_otp(self.session_id, "first@example.com", sender=lambda e, o: sent.append(o), now=1000.0)
        ok, _ = ev.verify_otp(self.session_id, "first@example.com", sent[0], now=1010.0)
        self.assertTrue(ok)
        self.assertTrue(ev.is_email_verified(self.session_id, "first@example.com"))

        ev.sync_email_change(self.session_id, "second@example.com")
        self.assertFalse(ev.is_email_verified(self.session_id, "first@example.com"))
        self.assertFalse(ev.is_email_verified(self.session_id, "second@example.com"))

    def test_phone_and_name_validation(self):
        self.assertFalse(validate_full_name("   ")[0])
        self.assertTrue(validate_full_name("Jane Doe")[0])
        self.assertIn("AI Engineer", TECHNICAL_ROLES)

        self.assertEqual(format_phone_for_region("9876543210", "IN"), "98765 43210")
        self.assertEqual(format_phone_for_region("4155550123", "US"), "(415) 555-0123")
        self.assertEqual(validate_phone_number("IN", "98765 43210"), (True, "+919876543210", ""))
        self.assertFalse(validate_phone_number("IN", "12345 67890")[0])
        self.assertEqual(validate_phone_number("US", "(415) 555-0123"), (True, "+14155550123", ""))

    def test_api_otp_and_submission_restriction(self):
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertEqual(r_health.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(r_health.headers.get("x-frame-options"), "DENY")
        self.assertEqual(r_health.headers.get("cache-control"), "no-store")

        # Recruiter endpoints must reject unauthenticated requests
        self.assertEqual(self.client.get("/api/recruiter/dashboard").status_code, 401)
        self.assertEqual(self.client.delete("/api/recruiter/candidates").status_code, 401)

        r_cfg = self.client.get("/api/candidate/config")
        self.assertEqual(r_cfg.status_code, 200)
        self.assertIn("AI Engineer", r_cfg.json()["technical_roles"])

        sent_otps = []
        with patch("email_verification.send_otp_email_smtp", side_effect=lambda e, o: sent_otps.append((e, o))):
            # Cannot submit without 18+ consent
            r_no_consent = self.client.post(
                "/api/candidate/submit",
                data={
                    "session_id": self.session_id,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "region_code": "IN",
                    "phone": "98765 43210",
                    "target_role": "AI Engineer",
                    "years_exp": "2.5",
                    "confirm_adult": "false",
                },
                files={"resume": ("resume.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            )
            self.assertEqual(r_no_consent.status_code, 400)

            # Cannot submit without OTP verification
            r_unverified = self.client.post(
                "/api/candidate/submit",
                data={
                    "session_id": self.session_id,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "region_code": "IN",
                    "phone": "98765 43210",
                    "target_role": "AI Engineer",
                    "years_exp": "2.5",
                    "confirm_adult": "true",
                },
                files={"resume": ("resume.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            )
            self.assertEqual(r_unverified.status_code, 403)

            # Send OTP
            r_send = self.client.post(
                "/api/candidate/send-otp",
                json={"session_id": self.session_id, "email": "jane@example.com"},
            )
            self.assertEqual(r_send.status_code, 200)
            self.assertEqual(len(sent_otps), 1)

            # Verify OTP
            r_verify = self.client.post(
                "/api/candidate/verify-otp",
                json={"session_id": self.session_id, "email": "jane@example.com", "otp": sent_otps[0][1]},
            )
            self.assertEqual(r_verify.status_code, 200)
            self.assertTrue(r_verify.json()["verified"])

            # Non-.pdf extension rejected even when verified
            r_bad_ext = self.client.post(
                "/api/candidate/submit",
                data={
                    "session_id": self.session_id,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "region_code": "IN",
                    "phone": "98765 43210",
                    "target_role": "AI Engineer",
                    "years_exp": "2.5",
                    "confirm_adult": "true",
                },
                files={"resume": ("script.exe", b"%PDF-1.4 dummy", "application/pdf")},
            )
            self.assertEqual(r_bad_ext.status_code, 400)

            # Email change invalidates verification
            self.client.post(
                "/api/candidate/sync-email",
                json={"session_id": self.session_id, "email": "other@example.com"},
            )
            r_after_change = self.client.post(
                "/api/candidate/submit",
                data={
                    "session_id": self.session_id,
                    "name": "Jane Doe",
                    "email": "jane@example.com",
                    "region_code": "IN",
                    "phone": "98765 43210",
                    "target_role": "AI Engineer",
                    "years_exp": "2.5",
                    "confirm_adult": "true",
                },
                files={"resume": ("resume.pdf", b"%PDF-1.4 dummy", "application/pdf")},
            )
            self.assertEqual(r_after_change.status_code, 403)


if __name__ == "__main__":
    unittest.main()
