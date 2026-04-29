"""Mailer service.

Defines a Mailer Protocol with the send methods used by the plan
lifecycle (assignment, modification, archival, pause, resume, cancel,
restart) and the user-creation flow, plus two implementations:

  - SMTPMailer: real SMTP via aiosmtplib. Configured by environment.
                Works with Mailpit (dev), AWS SES, Gmail SMTP, SendGrid, etc.
  - LogMailer:  no-op that writes to the application log. Used when
                EMAILS_ENABLED=false and in tests.

The choice between them is made by `get_mailer()` which reads `Settings`.

Every send takes an optional ``actor: User`` so the email body can
attribute the change to the admin that performed it. Pass ``None`` for
system-triggered sends (none today, but the type leaves room).

The plan-modified email also takes a structured ``changes`` payload (see
``services.plan_diff.compute_plan_diff``) so the recipient sees what
actually changed instead of a one-liner.
"""

from __future__ import annotations

import html
import logging
from datetime import date
from email.message import EmailMessage
from typing import Any, Iterable, Optional, Protocol, runtime_checkable

import aiosmtplib

from config import Settings, get_settings
from models import Plan, User

logger = logging.getLogger("virtuagym.mailer")


@runtime_checkable
class Mailer(Protocol):
    async def send_plan_assigned(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None: ...
    async def send_plan_modified(
        self,
        to: str,
        plan: Plan,
        *,
        actor: Optional[User] = None,
        changes: Optional[list[dict[str, Any]]] = None,
    ) -> None: ...
    async def send_plan_archived(
        self, to: str, plan_title: str, *, actor: Optional[User] = None
    ) -> None: ...
    async def send_plan_paused(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None: ...
    async def send_plan_resumed(
        self,
        to: str,
        plan: Plan,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None: ...
    async def send_plan_cancelled(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None: ...
    async def send_plan_restarted(
        self,
        to: str,
        plan: Plan,
        start_date: date,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None: ...
    async def send_user_account_created(
        self,
        to: str,
        new_user_first_name: str,
        *,
        creator: User,
    ) -> None: ...


# ---------------------------------------------------------------------------
# Helpers — actor labels and message building
# ---------------------------------------------------------------------------


def actor_label(actor: Optional[User]) -> Optional[str]:
    if actor is None:
        return None
    name = f"{actor.first_name} {actor.last_name}".strip()
    if not name:
        return actor.email
    return f"{name} ({actor.email})"


def actor_html_label(actor: Optional[User]) -> Optional[str]:
    if actor is None:
        return None
    name = f"{actor.first_name} {actor.last_name}".strip()
    if not name:
        return html.escape(actor.email)
    return f"{html.escape(name)} (<a href=\"mailto:{html.escape(actor.email)}\">{html.escape(actor.email)}</a>)"


def build_message(
    *,
    sender: str,
    to: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    # Plain-text fallback first, then HTML alternative — clients that
    # prefer text get the readable version; HTML-capable ones render the
    # styled one.
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


# ---------------------------------------------------------------------------
# HTML template — small, inline-styled, dark-friendly accent on Virtuagym orange
# ---------------------------------------------------------------------------


_HTML_SHELL = """\
<!doctype html>
<html lang="en">
  <body style="margin:0;padding:0;background-color:#f5f5f3;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#181818;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f5f5f3;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="560" cellpadding="0" cellspacing="0" border="0" style="background-color:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
            <tr>
              <td style="background-color:#181818;padding:18px 24px;">
                <span style="color:#ff6f14;font-weight:700;font-size:18px;letter-spacing:0.5px;">VIRTUAGYM</span>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 28px 24px 28px;font-size:14px;line-height:1.55;color:#181818;">
                {body}
              </td>
            </tr>
            <tr>
              <td style="padding:18px 28px;background-color:#fafaf8;border-top:1px solid #ececea;font-size:12px;color:#6f6f68;">
                You're receiving this because you're a Virtuagym member.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def wrap_html(inner: str) -> str:
    return _HTML_SHELL.format(body=inner)


def heading(text: str) -> str:
    return (
        f'<h1 style="margin:0 0 16px 0;font-size:20px;font-weight:700;color:#181818;">'
        f"{html.escape(text)}</h1>"
    )


def para(text_html: str) -> str:
    return (
        f'<p style="margin:0 0 14px 0;font-size:14px;line-height:1.55;color:#181818;">'
        f"{text_html}</p>"
    )


def muted(text_html: str) -> str:
    return (
        f'<p style="margin:0 0 14px 0;font-size:13px;color:#6f6f68;">'
        f"{text_html}</p>"
    )


def signature_html() -> str:
    return (
        '<p style="margin:18px 0 0 0;font-size:13px;color:#6f6f68;">— Virtuagym</p>'
    )


def actor_block_html(actor: Optional[User], verb: str) -> str:
    label = actor_html_label(actor)
    if label is None:
        return ""
    return muted(f"{html.escape(verb)} by {label}.")


def actor_block_text(actor: Optional[User], verb: str) -> str:
    label = actor_label(actor)
    if label is None:
        return ""
    return f"{verb} by {label}.\n\n"


# ---------------------------------------------------------------------------
# Plan-diff rendering
# ---------------------------------------------------------------------------


def render_changes_html(changes: Iterable[dict[str, Any]]) -> str:
    items: list[str] = []
    for change in changes:
        kind = change.get("kind")
        if kind == "field":
            items.append(
                f'<li style="margin:6px 0;"><strong>{html.escape(str(change["label"]))}</strong>: '
                f'<span style="color:#a14a00;text-decoration:line-through;">{html.escape(str(change["old"]))}</span> '
                f'→ <span style="color:#1f7a3a;font-weight:600;">{html.escape(str(change["new"]))}</span></li>'
            )
        elif kind == "image":
            items.append(
                f'<li style="margin:6px 0;">Cover image {html.escape(str(change["action"]))}</li>'
            )
        elif kind == "structure":
            items.append(
                f'<li style="margin:6px 0;">{html.escape(str(change["summary"]))}</li>'
            )
        elif kind == "day":
            day_changes = "".join(
                f'<li style="margin:4px 0;color:#3a3a37;">{html.escape(c)}</li>'
                for c in change.get("changes", [])
            )
            items.append(
                f'<li style="margin:10px 0;"><strong>{html.escape(str(change["where"]))}</strong>'
                f'<ul style="margin:4px 0 0 0;padding-left:18px;">{day_changes}</ul></li>'
            )
    if not items:
        return ""
    return (
        '<div style="margin:18px 0;padding:14px 18px;background-color:#fafaf8;border-left:3px solid #ff6f14;border-radius:6px;">'
        '<p style="margin:0 0 10px 0;font-size:13px;font-weight:600;color:#181818;">What changed</p>'
        f'<ul style="margin:0;padding-left:18px;">{"".join(items)}</ul>'
        "</div>"
    )


def render_changes_text(changes: Iterable[dict[str, Any]]) -> str:
    lines: list[str] = []
    for change in changes:
        kind = change.get("kind")
        if kind == "field":
            lines.append(f"  • {change['label']}: {change['old']} → {change['new']}")
        elif kind == "image":
            lines.append(f"  • Cover image {change['action']}")
        elif kind == "structure":
            lines.append(f"  • {change['summary']}")
        elif kind == "day":
            lines.append(f"  • {change['where']}:")
            for c in change.get("changes", []):
                lines.append(f"      - {c}")
    if not lines:
        return ""
    return "What changed:\n" + "\n".join(lines) + "\n\n"


# ---------------------------------------------------------------------------
# LogMailer — for tests + EMAILS_ENABLED=false
# ---------------------------------------------------------------------------


class LogMailer:
    """Mailer that records would-be sends to the application log only."""

    async def send_plan_assigned(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        logger.info(
            "[LogMailer] plan-assigned to %s for plan '%s' by %s",
            to, plan.title, actor_label(actor) or "(system)",
        )

    async def send_plan_modified(
        self,
        to: str,
        plan: Plan,
        *,
        actor: Optional[User] = None,
        changes: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        logger.info(
            "[LogMailer] plan-modified to %s for plan '%s' by %s (%d changes)",
            to, plan.title, actor_label(actor) or "(system)", len(changes or []),
        )

    async def send_plan_archived(
        self, to: str, plan_title: str, *, actor: Optional[User] = None
    ) -> None:
        logger.info(
            "[LogMailer] plan-archived to %s for plan '%s' by %s",
            to, plan_title, actor_label(actor) or "(system)",
        )

    async def send_plan_paused(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        logger.info(
            "[LogMailer] plan-paused to %s for plan '%s' by %s",
            to, plan.title, actor_label(actor) or "(system)",
        )

    async def send_plan_resumed(
        self,
        to: str,
        plan: Plan,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None:
        logger.info(
            "[LogMailer] plan-resumed to %s for plan '%s' (end %s) by %s",
            to, plan.title, end_date.isoformat(), actor_label(actor) or "(system)",
        )

    async def send_plan_cancelled(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        logger.info(
            "[LogMailer] plan-cancelled to %s for plan '%s' by %s",
            to, plan.title, actor_label(actor) or "(system)",
        )

    async def send_plan_restarted(
        self,
        to: str,
        plan: Plan,
        start_date: date,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None:
        logger.info(
            "[LogMailer] plan-restarted to %s for plan '%s' (%s → %s) by %s",
            to, plan.title, start_date.isoformat(), end_date.isoformat(),
            actor_label(actor) or "(system)",
        )

    async def send_user_account_created(
        self,
        to: str,
        new_user_first_name: str,
        *,
        creator: User,
    ) -> None:
        logger.info(
            "[LogMailer] account-created to %s (first_name=%s) by %s",
            to, new_user_first_name, actor_label(creator),
        )


# ---------------------------------------------------------------------------
# SMTPMailer — real SMTP delivery via aiosmtplib
# ---------------------------------------------------------------------------


class SMTPMailer:
    """Mailer that delivers via aiosmtplib to any SMTP-compatible server."""

    def __init__(self, settings: Settings):
        self._settings = settings

    async def send(self, msg: EmailMessage) -> None:
        s = self._settings
        try:
            await aiosmtplib.send(
                msg,
                hostname=s.smtp_host,
                port=s.smtp_port,
                username=s.smtp_username or None,
                password=s.smtp_password or None,
                use_tls=s.smtp_use_tls,
                start_tls=False,
            )
        except Exception:
            logger.exception("SMTP send failed (host=%s port=%s)", s.smtp_host, s.smtp_port)
            raise

    # ----- plan assigned -----
    async def send_plan_assigned(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        title = html.escape(plan.title)
        actor_text = actor_block_text(actor, "Assigned")
        actor_html = actor_block_html(actor, "Assigned")
        text_body = (
            f"Hi,\n\n"
            f"You've been assigned to the workout plan '{plan.title}'.\n\n"
            f"{actor_text}"
            f"— Virtuagym\n"
        )
        html_inner = (
            heading(f"You've been assigned to a new plan")
            + para(f"You've been assigned to the workout plan <strong>{title}</strong>.")
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"You've been assigned to plan: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- plan modified (with diff) -----
    async def send_plan_modified(
        self,
        to: str,
        plan: Plan,
        *,
        actor: Optional[User] = None,
        changes: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        title = html.escape(plan.title)
        actor_text = actor_block_text(actor, "Modified")
        actor_html = actor_block_html(actor, "Modified")
        diff_text = render_changes_text(changes or [])
        diff_html = render_changes_html(changes or [])

        if not (changes or []):
            body_text_lead = (
                f"Your workout plan '{plan.title}' was updated.\n"
                f"Open the app to see the latest version.\n\n"
            )
            body_html_lead = para(
                f"Your workout plan <strong>{title}</strong> was updated. "
                f"Open the app to see the latest version."
            )
        else:
            body_text_lead = f"Your workout plan '{plan.title}' was updated.\n\n"
            body_html_lead = para(
                f"Your workout plan <strong>{title}</strong> was updated."
            )

        text_body = f"Hi,\n\n{body_text_lead}{diff_text}{actor_text}— Virtuagym\n"
        html_inner = (
            heading("Your plan was updated")
            + body_html_lead
            + diff_html
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was updated: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- plan archived -----
    async def send_plan_archived(
        self, to: str, plan_title: str, *, actor: Optional[User] = None
    ) -> None:
        title_html = html.escape(plan_title)
        actor_text = actor_block_text(actor, "Archived")
        actor_html = actor_block_html(actor, "Archived")
        text_body = (
            f"Hi,\n\n"
            f"The workout plan '{plan_title}' you were assigned to has been archived.\n"
            f"Reach out to your trainer if you need a new plan.\n\n"
            f"{actor_text}— Virtuagym\n"
        )
        html_inner = (
            heading("Your plan was archived")
            + para(
                f"The workout plan <strong>{title_html}</strong> you were assigned to has been archived. "
                f"Reach out to your trainer if you need a new plan."
            )
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was archived: {plan_title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- pause -----
    async def send_plan_paused(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        title = html.escape(plan.title)
        actor_text = actor_block_text(actor, "Paused")
        actor_html = actor_block_html(actor, "Paused")
        text_body = (
            f"Hi,\n\n"
            f"Your workout plan '{plan.title}' has been paused.\n"
            f"We will let you know when your plan gets resumed, restarted, or cancelled.\n\n"
            f"{actor_text}— Virtuagym\n"
        )
        html_inner = (
            heading("Your plan was paused")
            + para(
                f"Your workout plan <strong>{title}</strong> has been paused. "
                f"We will let you know when your plan gets resumed, restarted, or cancelled."
            )
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was paused: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- resume -----
    async def send_plan_resumed(
        self,
        to: str,
        plan: Plan,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None:
        title = html.escape(plan.title)
        end_str = end_date.isoformat()
        actor_text = actor_block_text(actor, "Resumed")
        actor_html = actor_block_html(actor, "Resumed")
        text_body = (
            f"Hi,\n\n"
            f"Your workout plan '{plan.title}' has been resumed.\n"
            f"New end date: {end_str}.\n\n"
            f"{actor_text}— Virtuagym\n"
        )
        html_inner = (
            heading("Your plan was resumed")
            + para(
                f"Your workout plan <strong>{title}</strong> has been resumed. "
                f"New end date: <strong>{html.escape(end_str)}</strong>."
            )
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was resumed: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- cancel -----
    async def send_plan_cancelled(
        self, to: str, plan: Plan, *, actor: Optional[User] = None
    ) -> None:
        title = html.escape(plan.title)
        actor_text = actor_block_text(actor, "Cancelled")
        actor_html = actor_block_html(actor, "Cancelled")
        text_body = (
            f"Hi,\n\n"
            f"Your workout plan '{plan.title}' has been cancelled.\n"
            f"Reach out to your trainer if you need a new plan.\n\n"
            f"{actor_text}— Virtuagym\n"
        )
        html_inner = (
            heading("Your plan was cancelled")
            + para(
                f"Your workout plan <strong>{title}</strong> has been cancelled. "
                f"Reach out to your trainer if you need a new plan."
            )
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was cancelled: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- restart -----
    async def send_plan_restarted(
        self,
        to: str,
        plan: Plan,
        start_date: date,
        end_date: date,
        *,
        actor: Optional[User] = None,
    ) -> None:
        title = html.escape(plan.title)
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        actor_text = actor_block_text(actor, "Restarted")
        actor_html = actor_block_html(actor, "Restarted")
        text_body = (
            f"Hi,\n\n"
            f"Your workout plan '{plan.title}' has been restarted.\n"
            f"New start date: {start_str}.\n"
            f"New end date: {end_str}.\n\n"
            f"{actor_text}— Virtuagym\n"
        )
        html_inner = (
            heading("Your plan was restarted")
            + para(
                f"Your workout plan <strong>{title}</strong> has been restarted."
            )
            + para(
                f"New start date: <strong>{html.escape(start_str)}</strong><br/>"
                f"New end date: <strong>{html.escape(end_str)}</strong>"
            )
            + actor_html
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject=f"Your plan was restarted: {plan.title}",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)

    # ----- account created (sent to the new user) -----
    async def send_user_account_created(
        self,
        to: str,
        new_user_first_name: str,
        *,
        creator: User,
    ) -> None:
        creator_name = f"{creator.first_name} {creator.last_name}".strip() or creator.email
        contact_lines_text: list[str] = [f"Email: {creator.email}"]
        contact_lines_html: list[str] = [
            f'Email: <a href="mailto:{html.escape(creator.email)}">{html.escape(creator.email)}</a>'
        ]
        if creator.phone_number:
            contact_lines_text.append(f"Phone: {creator.phone_number}")
            contact_lines_html.append(f"Phone: {html.escape(creator.phone_number)}")

        text_body = (
            f"Hi {new_user_first_name},\n\n"
            f"An account has been created for you on Virtuagym by {creator_name}.\n\n"
            f"To receive your password and start using the app, please contact {creator_name}:\n"
            + "\n".join(f"  - {line}" for line in contact_lines_text)
            + "\n\n"
            f"Once you have your password you can sign in at the Virtuagym app.\n\n"
            f"— Virtuagym\n"
        )
        contact_html = (
            '<ul style="margin:6px 0 0 0;padding-left:18px;">'
            + "".join(f'<li style="margin:3px 0;">{line}</li>' for line in contact_lines_html)
            + "</ul>"
        )
        html_inner = (
            heading(f"Welcome to Virtuagym, {html.escape(new_user_first_name)}")
            + para(
                f"An account has been created for you on Virtuagym by "
                f"<strong>{html.escape(creator_name)}</strong>."
            )
            + para(
                f"To receive your password and start using the app, please contact "
                f"<strong>{html.escape(creator_name)}</strong>:"
            )
            + f'<div style="margin:0 0 14px 0;font-size:14px;color:#181818;">{contact_html}</div>'
            + muted("Once you have your password you can sign in at the Virtuagym app.")
            + signature_html()
        )
        msg = build_message(
            sender=self._settings.smtp_from,
            to=to,
            subject="Your Virtuagym account is ready",
            text_body=text_body,
            html_body=wrap_html(html_inner),
        )
        await self.send(msg)


def get_mailer() -> Mailer:
    """FastAPI dependency that returns the active mailer.

    Decides at request time so flipping EMAILS_ENABLED takes effect on the
    next request without restarting the process (settings are cached, but the
    branch is evaluated each call).
    """
    settings = get_settings()
    if settings.emails_enabled:
        return SMTPMailer(settings)
    return LogMailer()
