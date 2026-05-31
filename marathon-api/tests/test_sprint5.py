"""
Sprint 5 acceptance criteria tests.

AC1: With SMTP_* vars set → real email (tested via mock)
AC2: Without SMTP_* vars → [EMAIL STUB] log, no crash
AC3: POST /notifications/broadcast with filter_status=registered queues correct count
AC4: GET /notifications/history returns rows with recipient names
AC5: CSV upload with 3 valid rows → processed=3, certificate tasks fire for each
AC6: CSV upload with 1 invalid row (wrong status) → skipped=1, warning shown, others processed
AC7: Dashboard summary cards (30s refresh is frontend — tested via API returning correct counts)
AC8: Full demo flow (register → approve → confirm → scan → finish → cert)
AC9: .env.example documents every variable
"""
import io
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import (
    auth_headers,
    make_event,
    make_registration,
    make_user,
)
from app.models.registration import RegistrationStatus
from app.models.user import UserRole


# ===========================================================================
# AC2 — Email stub: no SMTP_HOST → logs [EMAIL STUB], no crash
# ===========================================================================
class TestAC2EmailStub:
    def test_send_email_stub_when_no_smtp_host(self, caplog):
        """notification_service.send_email logs stub and returns True when SMTP_HOST is None."""
        import logging
        from unittest.mock import patch

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SMTP_HOST = None
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASSWORD = None
            mock_settings.SMTP_FROM_EMAIL = None
            mock_settings.SMTP_FROM = None

            from app.services.notification_service import send_email

            with caplog.at_level(logging.INFO, logger="app.services.notification_service"):
                result = send_email("test@example.com", "Hello", "<p>Hi</p>")

        assert result is True
        assert "[EMAIL STUB]" in caplog.text
        assert "test@example.com" in caplog.text

    def test_send_email_stub_when_smtp_host_empty_string(self, caplog):
        """Empty string SMTP_HOST also triggers stub (falsy check)."""
        import logging
        from unittest.mock import patch

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.SMTP_HOST = ""

            from app.services.notification_service import send_email

            with caplog.at_level(logging.INFO, logger="app.services.notification_service"):
                result = send_email("a@b.com", "Subj", "body")

        assert result is True
        assert "[EMAIL STUB]" in caplog.text

    def test_send_whatsapp_stub_when_no_twilio(self, caplog):
        """notification_service.send_whatsapp logs stub when Twilio vars are unset."""
        import logging
        from unittest.mock import patch

        with patch("app.services.notification_service.settings") as mock_settings:
            mock_settings.TWILIO_ACCOUNT_SID = None
            mock_settings.TWILIO_AUTH_TOKEN = None
            mock_settings.TWILIO_WHATSAPP_FROM = None

            from app.services.notification_service import send_whatsapp

            with caplog.at_level(logging.INFO, logger="app.services.notification_service"):
                result = send_whatsapp("+1234567890", "Hello runner!")

        assert result is True
        assert "[WHATSAPP STUB]" in caplog.text


# ===========================================================================
# AC1 — Real SMTP: SMTP_HOST set → smtplib.SMTP is called
# ===========================================================================
class TestAC1RealEmail:
    def test_send_email_calls_smtplib_when_smtp_host_set(self):
        """When SMTP_HOST is set, send_email calls smtplib.SMTP (mocked)."""
        from unittest.mock import MagicMock, patch

        mock_smtp_instance = MagicMock()
        mock_smtp_instance.__enter__ = MagicMock(return_value=mock_smtp_instance)
        mock_smtp_instance.__exit__ = MagicMock(return_value=False)

        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch("app.services.notification_service.smtplib.SMTP", return_value=mock_smtp_instance),
        ):
            mock_settings.SMTP_HOST = "smtp.real.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USER = "user@real.com"
            mock_settings.SMTP_PASSWORD = "secret"
            mock_settings.SMTP_FROM_EMAIL = "noreply@real.com"
            mock_settings.SMTP_FROM = None

            from app.services import notification_service
            # Reload to pick up patched settings in the function body
            result = notification_service.send_email(
                "recipient@test.com", "Test Subject", "<p>Test</p>"
            )

        assert result is True
        mock_smtp_instance.sendmail.assert_called_once()

    def test_send_email_returns_false_on_smtp_error(self):
        """send_email returns False (does not raise) when SMTP throws."""
        import smtplib
        from unittest.mock import patch

        with (
            patch("app.services.notification_service.settings") as mock_settings,
            patch(
                "app.services.notification_service.smtplib.SMTP",
                side_effect=smtplib.SMTPException("connection refused"),
            ),
        ):
            mock_settings.SMTP_HOST = "smtp.broken.com"
            mock_settings.SMTP_PORT = 587
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASSWORD = None
            mock_settings.SMTP_FROM_EMAIL = None
            mock_settings.SMTP_FROM = None

            from app.services.notification_service import send_email
            result = send_email("x@y.com", "S", "B")

        assert result is False  # no exception raised


# ===========================================================================
# AC3 — POST /notifications/broadcast queues correct count
# ===========================================================================
@pytest.mark.asyncio
class TestAC3Broadcast:
    async def test_broadcast_all_registrations(self, client, db):
        organizer = await make_user(db, "org@test.com", UserRole.organizer, "Org")
        event = await make_event(db)
        p1 = await make_user(db, "p1@test.com", UserRole.participant, "P1")
        p2 = await make_user(db, "p2@test.com", UserRole.participant, "P2")
        p3 = await make_user(db, "p3@test.com", UserRole.participant, "P3")
        await make_registration(db, p1, event, RegistrationStatus.registered)
        await make_registration(db, p2, event, RegistrationStatus.approved)
        await make_registration(db, p3, event, RegistrationStatus.registered)

        with patch("app.routers.notifications.send_broadcast_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                "/notifications/broadcast",
                json={
                    "event_id": str(event.id),
                    "channel": "email",
                    "subject": "Hello all",
                    "message": "Race day is coming!",
                    "filter_status": None,
                },
                headers=auth_headers(organizer),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["queued"] == 3
        assert "3 recipients" in data["message"]

    async def test_broadcast_filtered_by_status(self, client, db):
        organizer = await make_user(db, "org2@test.com", UserRole.organizer, "Org2")
        event = await make_event(db)
        p1 = await make_user(db, "fp1@test.com", UserRole.participant, "FP1")
        p2 = await make_user(db, "fp2@test.com", UserRole.participant, "FP2")
        p3 = await make_user(db, "fp3@test.com", UserRole.participant, "FP3")
        await make_registration(db, p1, event, RegistrationStatus.registered)
        await make_registration(db, p2, event, RegistrationStatus.registered)
        await make_registration(db, p3, event, RegistrationStatus.approved)

        with patch("app.routers.notifications.send_broadcast_task") as mock_task:
            mock_task.delay = MagicMock()
            resp = await client.post(
                "/notifications/broadcast",
                json={
                    "event_id": str(event.id),
                    "channel": "email",
                    "subject": "Registered only",
                    "message": "Please confirm!",
                    "filter_status": "registered",
                },
                headers=auth_headers(organizer),
            )

        assert resp.status_code == 200
        assert resp.json()["queued"] == 2

    async def test_broadcast_requires_organizer_role(self, client, db):
        participant = await make_user(db, "notorg@test.com", UserRole.participant)
        event = await make_event(db)
        resp = await client.post(
            "/notifications/broadcast",
            json={"event_id": str(event.id), "channel": "email", "subject": "x", "message": "y"},
            headers=auth_headers(participant),
        )
        assert resp.status_code == 403

    async def test_broadcast_cap_exceeded(self, client, db):
        """Returns 400 when recipient count exceeds 500."""
        organizer = await make_user(db, "orgcap@test.com", UserRole.organizer, "OrgCap")
        event = await make_event(db)

        # Create 501 participants
        for i in range(501):
            u = await make_user(db, f"cap{i}@test.com", UserRole.participant, f"Cap{i}")
            await make_registration(db, u, event, RegistrationStatus.registered)

        resp = await client.post(
            "/notifications/broadcast",
            json={"event_id": str(event.id), "channel": "email", "subject": "x", "message": "y"},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 400
        assert "cap" in resp.json()["detail"].lower()


# ===========================================================================
# AC4 — GET /notifications/history returns rows with recipient names
# ===========================================================================
@pytest.mark.asyncio
class TestAC4NotificationHistory:
    async def test_history_returns_notifications_with_recipient_info(self, client, db):
        from app.models.notification import Notification, NotificationChannel, NotificationTriggerType

        organizer = await make_user(db, "historg@test.com", UserRole.organizer, "HistOrg")
        event = await make_event(db)
        participant = await make_user(db, "histpart@test.com", UserRole.participant, "HistPart")
        reg = await make_registration(db, participant, event, RegistrationStatus.registered)

        # Insert a notification row directly
        notif = Notification(
            registration_id=reg.id,
            channel=NotificationChannel.email,
            trigger_type=NotificationTriggerType.manual_broadcast,
            content="Test notification content",
            sent=True,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(notif)
        await db.commit()

        resp = await client.get(
            f"/notifications/history?event_id={event.id}",
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        item = next(i for i in data["items"] if str(i["registration_id"]) == str(reg.id))
        assert item["recipient_name"] == "HistPart"
        assert item["recipient_email"] == "histpart@test.com"
        assert item["channel"] == "email"
        assert item["sent"] is True

    async def test_history_pagination(self, client, db):
        from app.models.notification import Notification, NotificationChannel, NotificationTriggerType

        organizer = await make_user(db, "pagorg@test.com", UserRole.organizer, "PagOrg")
        event = await make_event(db)
        participant = await make_user(db, "pagpart@test.com", UserRole.participant, "PagPart")
        reg = await make_registration(db, participant, event, RegistrationStatus.registered)

        for _ in range(5):
            db.add(Notification(
                registration_id=reg.id,
                channel=NotificationChannel.email,
                trigger_type=NotificationTriggerType.status_change,
                content="msg",
                sent=True,
                sent_at=datetime.now(timezone.utc),
            ))
        await db.commit()

        resp = await client.get(
            f"/notifications/history?event_id={event.id}&page=1&page_size=3",
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 3

    async def test_history_channel_filter(self, client, db):
        from app.models.notification import Notification, NotificationChannel, NotificationTriggerType

        organizer = await make_user(db, "chforg@test.com", UserRole.organizer, "ChfOrg")
        event = await make_event(db)
        participant = await make_user(db, "chfpart@test.com", UserRole.participant, "ChfPart")
        reg = await make_registration(db, participant, event, RegistrationStatus.registered)

        db.add(Notification(
            registration_id=reg.id,
            channel=NotificationChannel.email,
            trigger_type=NotificationTriggerType.status_change,
            content="email msg",
            sent=True,
            sent_at=datetime.now(timezone.utc),
        ))
        db.add(Notification(
            registration_id=reg.id,
            channel=NotificationChannel.whatsapp,
            trigger_type=NotificationTriggerType.status_change,
            content="wa msg",
            sent=True,
            sent_at=datetime.now(timezone.utc),
        ))
        await db.commit()

        resp = await client.get(
            f"/notifications/history?event_id={event.id}&channel=email",
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["channel"] == "email" for i in items)


# ===========================================================================
# AC5 — CSV upload: 3 valid rows → processed=3, cert tasks fire
# ===========================================================================
@pytest.mark.asyncio
class TestAC5CsvUpload:
    async def test_three_valid_rows_processed(self, client, db):
        organizer = await make_user(db, "csvorg@test.com", UserRole.organizer, "CsvOrg")
        event = await make_event(db)

        bibs = ["A01", "A02", "A03"]
        for i, bib in enumerate(bibs):
            p = await make_user(db, f"csvp{i}@test.com", UserRole.participant, f"CsvP{i}")
            await make_registration(db, p, event, RegistrationStatus.bib_collected, bib_number=bib)

        csv_content = "bib_number,finish_time\nA01,01:23:45\nA02,01:30:00\nA03,01:45:10\n"

        with patch("app.routers.organizer.generate_certificate_task") as mock_cert:
            mock_cert.delay = MagicMock()
            resp = await client.post(
                "/organizer/registrations/upload-finish-times",
                data={"event_id": str(event.id)},
                files={"file": ("times.csv", csv_content.encode(), "text/csv")},
                headers=auth_headers(organizer),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 3
        assert data["skipped"] == 0
        assert data["warnings"] == []
        assert data["errors"] == []
        assert mock_cert.delay.call_count == 3

    async def test_csv_requires_header_row(self, client, db):
        organizer = await make_user(db, "csvhorg@test.com", UserRole.organizer, "CsvHOrg")
        event = await make_event(db)

        csv_content = "A01,01:23:45\n"  # no header
        resp = await client.post(
            "/organizer/registrations/upload-finish-times",
            data={"event_id": str(event.id)},
            files={"file": ("times.csv", csv_content.encode(), "text/csv")},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 400
        assert "header" in resp.json()["detail"].lower()

    async def test_csv_max_rows_exceeded(self, client, db):
        organizer = await make_user(db, "csvmaxorg@test.com", UserRole.organizer, "CsvMaxOrg")
        event = await make_event(db)

        rows = ["bib_number,finish_time"] + [f"B{i:04d},01:00:00" for i in range(1001)]
        csv_content = "\n".join(rows)
        resp = await client.post(
            "/organizer/registrations/upload-finish-times",
            data={"event_id": str(event.id)},
            files={"file": ("times.csv", csv_content.encode(), "text/csv")},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 400
        assert "1000" in resp.json()["detail"]


# ===========================================================================
# AC6 — CSV upload: 1 invalid row (wrong status) → skipped=1, warning, others ok
# ===========================================================================
@pytest.mark.asyncio
class TestAC6CsvSkipInvalidStatus:
    async def test_wrong_status_row_skipped_with_warning(self, client, db):
        organizer = await make_user(db, "skiporg@test.com", UserRole.organizer, "SkipOrg")
        event = await make_event(db)

        # Valid: bib_collected
        p_valid = await make_user(db, "skipv@test.com", UserRole.participant, "SkipV")
        await make_registration(db, p_valid, event, RegistrationStatus.bib_collected, bib_number="V01")

        # Invalid: still approved (not bib_collected)
        p_invalid = await make_user(db, "skipi@test.com", UserRole.participant, "SkipI")
        await make_registration(db, p_invalid, event, RegistrationStatus.approved, bib_number="I01")

        csv_content = "bib_number,finish_time\nV01,01:10:00\nI01,01:20:00\n"

        with patch("app.routers.organizer.generate_certificate_task") as mock_cert:
            mock_cert.delay = MagicMock()
            resp = await client.post(
                "/organizer/registrations/upload-finish-times",
                data={"event_id": str(event.id)},
                files={"file": ("times.csv", csv_content.encode(), "text/csv")},
                headers=auth_headers(organizer),
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 1
        assert data["skipped"] == 1
        assert len(data["warnings"]) == 1
        assert "I01" in data["warnings"][0]
        assert mock_cert.delay.call_count == 1

    async def test_unknown_bib_skipped_with_warning(self, client, db):
        organizer = await make_user(db, "unkorg@test.com", UserRole.organizer, "UnkOrg")
        event = await make_event(db)

        csv_content = "bib_number,finish_time\nZZZ99,01:00:00\n"
        resp = await client.post(
            "/organizer/registrations/upload-finish-times",
            data={"event_id": str(event.id)},
            files={"file": ("times.csv", csv_content.encode(), "text/csv")},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["processed"] == 0
        assert data["skipped"] == 1
        assert "ZZZ99" in data["warnings"][0]

    async def test_invalid_time_format_skipped(self, client, db):
        organizer = await make_user(db, "fmtorg@test.com", UserRole.organizer, "FmtOrg")
        event = await make_event(db)

        p = await make_user(db, "fmtp@test.com", UserRole.participant, "FmtP")
        await make_registration(db, p, event, RegistrationStatus.bib_collected, bib_number="FMT1")

        csv_content = "bib_number,finish_time\nFMT1,not-a-time\n"
        resp = await client.post(
            "/organizer/registrations/upload-finish-times",
            data={"event_id": str(event.id)},
            files={"file": ("times.csv", csv_content.encode(), "text/csv")},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skipped"] == 1
        assert "not-a-time" in data["warnings"][0]


# ===========================================================================
# AC7 — Summary endpoint returns correct counts (30s refresh is frontend)
# ===========================================================================
@pytest.mark.asyncio
class TestAC7SummaryEndpoint:
    async def test_summary_returns_correct_counts(self, client, db):
        organizer = await make_user(db, "sumorg@test.com", UserRole.organizer, "SumOrg")
        event = await make_event(db)

        p1 = await make_user(db, "sum1@test.com", UserRole.participant, "Sum1")
        p2 = await make_user(db, "sum2@test.com", UserRole.participant, "Sum2")
        p3 = await make_user(db, "sum3@test.com", UserRole.participant, "Sum3")
        await make_registration(db, p1, event, RegistrationStatus.registered)
        await make_registration(db, p2, event, RegistrationStatus.approved)
        await make_registration(db, p3, event, RegistrationStatus.finished_certified)

        resp = await client.get(
            f"/organizer/registrations/summary?event_id={event.id}",
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["registered"] == 1
        assert data["approved"] == 1
        assert data["finished_certified"] == 1
        assert data["total"] == 3


# ===========================================================================
# AC8 — Full demo flow: register → approve → confirm → scan → finish → cert
# ===========================================================================
@pytest.mark.asyncio
class TestAC8FullDemoFlow:
    async def test_complete_registration_lifecycle(self, client, db):
        """
        End-to-end flow without touching the DB directly after setup.
        Each step uses the API.
        """
        # Setup: organizer, volunteer, event
        organizer = await make_user(db, "flow_org@test.com", UserRole.organizer, "FlowOrg")
        # Volunteers are participants with a volunteer_assignment — not a separate role
        volunteer = await make_user(db, "flow_vol@test.com", UserRole.participant, "FlowVol")
        event = await make_event(db, "Flow Marathon")

        # Assign volunteer to event
        from app.models.volunteer_assignment import VolunteerAssignment, VolunteerRoleType
        va = VolunteerAssignment(
            user_id=volunteer.id,
            event_id=event.id,
            role_type=VolunteerRoleType.bib_collection,
        )
        db.add(va)
        await db.commit()

        # Step 1: Register participant via API
        resp = await client.post("/auth/register", json={
            "name": "Flow Runner",
            "email": "flow_runner@test.com",
            "password": "password123",
            "role": "participant",
        })
        assert resp.status_code == 201, resp.text
        runner_token = resp.json()["access_token"]
        runner_headers = {"Authorization": f"Bearer {runner_token}"}

        resp = await client.post("/registrations/", json={
            "event_id": str(event.id),
            "distance": "10K",
            "tshirt_size": "M",
            "emergency_contact": "Mom: 555-1234",
        }, headers=runner_headers)
        assert resp.status_code == 201
        reg_id = resp.json()["id"]

        # Step 2: Organizer approves + assigns BIB
        resp = await client.patch(
            f"/organizer/registrations/{reg_id}/approve",
            json={"bib_number": "FLOW001"},
            headers=auth_headers(organizer),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"
        assert resp.json()["bib_number"] == "FLOW001"

        # Step 3: Participant confirms participation
        resp = await client.post(
            "/registrations/me/confirm",
            json={"event_id": str(event.id)},
            headers=runner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "participation_confirmed"

        # Step 4: Volunteer scans QR → bib_collected
        resp = await client.post(
            "/volunteers/scan",
            json={"qr_code_data": reg_id},
            headers=auth_headers(volunteer),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "bib_collected"

        # Step 5: Organizer enters finish time → finished_certified + cert task fires
        with patch("app.services.registration_service.generate_certificate_task") as mock_cert:
            mock_cert.delay = MagicMock()
            resp = await client.patch(
                f"/organizer/registrations/{reg_id}/finish-time",
                json={"finish_time": "2026-06-01T10:30:00Z"},
                headers=auth_headers(organizer),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished_certified"
        mock_cert.delay.assert_called_once_with(reg_id)

        # Step 6: Certificate endpoint returns 202 (cert not yet generated)
        resp = await client.get(
            f"/certificates/{reg_id}",
            headers=runner_headers,
        )
        assert resp.status_code == 202
        assert "being generated" in resp.json()["message"]

        # Step 7: Participant status page shows finished_certified
        resp = await client.get(
            f"/registrations/me?event_id={event.id}",
            headers=runner_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "finished_certified"


# ===========================================================================
# AC9 — .env.example documents all required variables
# ===========================================================================
class TestAC9EnvExample:
    REQUIRED_VARS = [
        "DATABASE_URL",
        "REDIS_URL",
        "SECRET_KEY",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET_NAME",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_WHATSAPP_FROM",
        "VITE_API_URL",
        "VITE_EVENT_ID",
    ]

    def test_env_example_contains_all_required_vars(self):
        import os
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_path) as f:
            content = f.read()

        missing = [v for v in self.REQUIRED_VARS if v not in content]
        assert missing == [], f"Missing from .env.example: {missing}"

    def test_env_example_has_comments(self):
        """Each section should have at least some comment lines."""
        import os
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_path) as f:
            content = f.read()

        comment_lines = [l for l in content.splitlines() if l.strip().startswith("#")]
        assert len(comment_lines) >= 10, "Expected at least 10 comment lines in .env.example"
