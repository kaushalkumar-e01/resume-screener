"""Unit and integration tests for Candidate Portal email OTP verification."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from streamlit.testing.v1 import AppTest

import email_verification as ev
from candidate_portal import (
    TECHNICAL_ROLES,
    _validate_full_name,
    format_phone_for_region,
    validate_phone_number,
)


class TestEmailVerification(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-session-123"
        ev.clear_session_otps(self.session_id)

    def tearDown(self):
        ev.clear_session_otps(self.session_id)

    def test_otp_generation_and_hashed_storage(self):
        sent = []

        def fake_sender(to_email, otp):
            sent.append((to_email, otp))

        ok, _ = ev.issue_otp(self.session_id, "Jane.Doe@Example.com", sender=fake_sender, now=1000.0)
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

        # Even the real OTP is rejected once locked
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

        # Previous OTP must be invalidated if different from new OTP
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

    def test_phone_formatting_and_country_validation(self):
        # libphonenumber country-specific formatting
        self.assertEqual(format_phone_for_region("9876543210", "IN"), "98765 43210")
        self.assertEqual(format_phone_for_region("98765abc43210", "IN"), "98765 43210")
        self.assertEqual(format_phone_for_region("4155550123", "US"), "(415) 555-0123")

        # IN (+91): valid vs invalid leading digit / letters
        self.assertEqual(validate_phone_number("IN", "98765 43210"), (True, "+919876543210", ""))
        self.assertFalse(validate_phone_number("IN", "12345 67890")[0])
        self.assertFalse(validate_phone_number("IN", "98765abc10")[0])

        # US (+1): libphonenumber NANP validation
        self.assertEqual(validate_phone_number("US", "(415) 555-0123"), (True, "+14155550123", ""))
        self.assertFalse(validate_phone_number("US", "1155550123")[0])

        # SG (+65): 8-digit Singapore validation
        self.assertEqual(validate_phone_number("SG", "9123 4567"), (True, "+6591234567", ""))
        self.assertFalse(validate_phone_number("SG", "1123 4567")[0])

    def test_candidate_portal_ui_and_submission_restriction(self):
        # Also verify full name validator and role list
        self.assertFalse(_validate_full_name("   ")[0])
        self.assertTrue(_validate_full_name("Jane Doe")[0])
        self.assertIn("AI Engineer", TECHNICAL_ROLES)

        sent_otps = []
        with patch("email_verification.send_otp_email_smtp", side_effect=lambda e, o: sent_otps.append((e, o))):
            app_path = str(Path(__file__).resolve().parents[1] / "app.py")
            at = AppTest.from_file(app_path).run()
            at.button[0].click().run()  # Enter Candidate Portal
            self.assertFalse(at.exception)

            # Experience input: min 0.0, step 0.5
            exp_input = at.number_input[0]
            self.assertEqual(exp_input.min, 0.0)
            self.assertEqual(exp_input.step, 0.5)
            exp_input.increment().run()
            self.assertEqual(at.number_input[0].value, 0.5)
            at.number_input[0].increment().run()
            self.assertEqual(at.number_input[0].value, 1.0)

            # Try submitting without verifying email or entering phone
            at.text_input[0].input("Jane Doe").run()
            at.text_input[1].input("jane@example.com").run()
            at.selectbox[0].select("AI Engineer").run()
            at.button(key="submit_application_btn").click().run()
            errs = [e.value for e in at.error]
            self.assertTrue(any("verify your email address" in m.lower() for m in errs), errs)
            self.assertTrue(any("phone number is required" in m.lower() for m in errs), errs)

            # Click Verify Email -> sends OTP and reveals OTP input
            at.button(key="verify_email_btn").click().run()
            self.assertEqual(len(sent_otps), 1)
            otp_code = sent_otps[0][1]

            # Enter OTP and click Verify OTP
            at.text_input(key="candidate_otp_input").input(otp_code).run()
            at.button(key="verify_otp_btn").click().run()
            self.assertTrue(any("email verified" in s.value.lower() for s in at.success))

            # Change email -> invalidates verification
            at.text_input[1].input("other@example.com").run()
            at.button(key="submit_application_btn").click().run()
            errs_changed = [e.value for e in at.error]
            self.assertTrue(any("verify your email address" in m.lower() for m in errs_changed), errs_changed)


if __name__ == "__main__":
    unittest.main()
