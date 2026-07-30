#!/usr/bin/env python3
"""FengMail CLI — IMAP email operations via ortie OAuth tokens.

Usage:
  python fengmail.py <account> list [--limit N]
  python fengmail.py <account> read <uid>
  python fengmail.py <account> flag <uid> [--seen | --unseen | --delete]
  python fengmail.py <account> delete <uid>
  python fengmail.py <account> send --to <addr> --subject <msg> [--body <text> | --body-file <path>] [--in-reply-to <msgid>]
  python fengmail.py <account> reply <uid> --body <text>

Accounts defined in accounts.json (same directory, gitignored).
"""

import imaplib
import json
import os
import smtplib
import subprocess
import sys
import base64
import email.utils
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Force UTF-8 output to prevent GBK encoding errors on Chinese Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
ORTIE = os.path.join(HERE, "ortie.exe")
ACCOUNTS_FILE = os.path.join(HERE, "accounts.json")

# Provider defaults (IMAP server by provider type)
PROVIDERS = {
    "gmail": {"imap": "imap.gmail.com", "port": 993, "smtp": "smtp.gmail.com", "smtp_port": 587},
    "outlook": {"imap": "outlook.office365.com", "port": 993, "smtp": "smtp.office365.com", "smtp_port": 587},
}


def load_accounts():
    """Load account config from accounts.json (local, gitignored)."""
    if not os.path.exists(ACCOUNTS_FILE):
        print(json.dumps({"error": f"accounts.json not found at {ACCOUNTS_FILE}"}))
        sys.exit(1)
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)


def get_token(account: str) -> str:
    """Get OAuth2 access token from ortie."""
    result = subprocess.run(
        [ORTIE, "-a", account, "token", "show", "--auto-refresh"],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ortie failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _xoauth2_string(user: str, token: str) -> bytes:
    return f"user={user}\x01auth=Bearer {token}\x01\x01".encode()


def connect(account: str, accounts: dict):
    """Connect to IMAP server using XOAUTH2."""
    info = accounts.get(account)
    if not info:
        raise ValueError(f"Unknown account: {account}")
    email = info["email"]
    provider = PROVIDERS.get(info.get("provider"))
    if not provider:
        raise ValueError(f"Unknown provider for {account}: {info.get('provider')}")

    token = get_token(account)
    imap = imaplib.IMAP4_SSL(provider["imap"], provider["port"])
    try:
        imap.authenticate("XOAUTH2", lambda _: _xoauth2_string(email, token))
    except imaplib.IMAP4.error as e:
        imap.logout()
        raise RuntimeError(f"XOAUTH2 failed for {account}: {e}")
    return imap


def _decode_mime(s: str) -> str:
    if not s or "=?" not in s:
        return s
    parts = decode_header(s)
    return "".join(
        p.decode(charset or "utf-8", errors="replace") if isinstance(p, bytes) else p
        for p, charset in parts
    )


def _has_flag(resp_part, flag: bytes) -> bool:
    if isinstance(resp_part, tuple) and len(resp_part) > 0:
        return flag in resp_part[0]
    return False


def _parse_email_date(date_str: str) -> str:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str.replace(" (UTC)", "").replace(" (CST)", ""))
        return dt.isoformat()
    except Exception:
        return date_str


def cmd_list(imap, limit: int = 20):
    imap.select("INBOX", readonly=True)
    _, data = imap.search(None, "ALL")
    uids = data[0].split() if data[0] else []
    if not uids:
        print(json.dumps({"envelopes": []}, ensure_ascii=False))
        return
    recent = uids[-limit:]
    envelopes = []
    for uid in reversed(recent):
        _, data = imap.fetch(uid, "(FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        if data[0] is None:
            continue
        resp_part = data[0]
        seen = _has_flag(resp_part, b"\\Seen")
        raw = resp_part[1] if isinstance(resp_part, tuple) and len(resp_part) > 1 else b""
        headers = {}
        for line in raw.split(b"\r\n"):
            if b":" in line:
                k, v = line.split(b":", 1)
                headers[k.strip().lower().decode("utf-8", errors="replace")] = (
                    v.strip().decode("utf-8", errors="replace")
                )
        envelopes.append({
            "uid": int(uid),
            "from": _decode_mime(headers.get("from", "")),
            "subject": _decode_mime(headers.get("subject", "")),
            "date": _parse_email_date(headers.get("date", "")),
            "seen": seen,
        })
    print(json.dumps({"envelopes": envelopes}, ensure_ascii=False, indent=2))


def cmd_read(imap, uid: int):
    imap.select("INBOX", readonly=True)
    _, data = imap.fetch(str(uid), "(BODY[])")
    if data[0] is None:
        print(json.dumps({"error": f"UID {uid} not found"}))
        return
    raw = data[0][1] if isinstance(data[0], tuple) else b""
    print(json.dumps({"uid": uid, "raw_length": len(raw)}, ensure_ascii=False))


def cmd_flag(imap, uid: int, action: str):
    imap.select("INBOX", readonly=False)
    flag_map = {"seen": "\\Seen", "unseen": "\\Unseen", "delete": "\\Deleted"}
    flag = flag_map.get(action)
    if not flag:
        raise ValueError(f"Invalid flag action: {action}")
    if action == "unseen":
        imap.store(str(uid), "-FLAGS", flag)
    else:
        imap.store(str(uid), "+FLAGS", flag)
    if action == "delete":
        imap.expunge()
    print(json.dumps({"ok": True, "uid": uid, "action": action}))


def cmd_delete(imap, uid: int):
    imap.select("INBOX", readonly=False)
    imap.store(str(uid), "+FLAGS", "\\Deleted")
    imap.expunge()
    print(json.dumps({"ok": True, "uid": uid, "action": "delete"}))


def _get_email_body(msg):
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True)
                if body:
                    text = body.decode('utf-8', errors='replace')
                    return _normalize_body(text)
        return ""
    body = msg.get_payload(decode=True)
    if body:
        text = body.decode('utf-8', errors='replace')
        return _normalize_body(text)
    return ""


def _normalize_body(text: str) -> str:
    """Normalize literal \\n to real newlines (QQ Agent bug workaround)."""
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    return text


def _quote_original(orig, reply_body: str) -> str:
    """Append the original email as quoted text below the reply."""
    orig_from = orig.get("From", "")
    orig_date = orig.get("Date", "")
    orig_subject = orig.get("Subject", "")
    orig_body = _get_email_body(orig).strip()

    quoted = (
        f"\n\n--- Original Message ---\n"
        f"From: {orig_from}\n"
        f"Date: {orig_date}\n"
        f"Subject: {orig_subject}\n"
        f"\n"
        f"{orig_body}"
    )
    return reply_body + quoted


def cmd_reply(account: str, accounts: dict, uid: int, body: str):
    """Reply to an email by UID. Reads original headers from IMAP for threading."""
    import email as email_lib
    info = accounts.get(account)
    if not info:
        raise ValueError(f"Unknown account: {account}")

    imap = connect(account, accounts)
    try:
        imap.select("INBOX", readonly=True)
        _, data = imap.fetch(str(uid), "(BODY[])")
        if data[0] is None:
            print(json.dumps({"error": f"UID {uid} not found"}))
            return
        raw = data[0][1] if isinstance(data[0], tuple) else b""
        orig = email_lib.message_from_bytes(raw)
    finally:
        imap.logout()

    # Extract headers from original
    orig_msg_id = orig["Message-ID"]
    orig_refs = orig["References"]
    orig_subject = orig["Subject"]
    orig_from = orig["From"]

    if not orig_msg_id:
        print(json.dumps({"error": "Original email has no Message-ID header, cannot reply"}))
        return
    if not orig_from:
        print(json.dumps({"error": "Original email has no From header, cannot reply"}))
        return

    msg_id = orig_msg_id.strip()
    references = (orig_refs.strip() + " " + msg_id) if orig_refs else msg_id

    # Build reply subject
    subject = orig_subject or ""
    upper = subject.upper()
    if not (upper.startswith("RE:") or upper.startswith("RE：")):
        subject = "Re: " + subject

    to_addr = email.utils.parseaddr(orig_from)[1]

    # Attach quoted original body
    full_body = _quote_original(orig, body)

    cmd_send(account, accounts, to_addr, subject, full_body, msg_id, references)


def cmd_send(account: str, accounts: dict, to_addr: str, subject: str, body: str, in_reply_to: str = None, references: str = None):
    """Send email via SMTP with XOAUTH2."""
    info = accounts.get(account)
    if not info:
        raise ValueError(f"Unknown account: {account}")
    email_addr = info["email"]
    provider = PROVIDERS.get(info.get("provider"))
    if not provider:
        raise ValueError(f"Unknown provider for {account}: {info.get('provider')}")

    token = get_token(account)

    msg = MIMEMultipart('alternative')
    msg['From'] = email_addr
    msg['To'] = to_addr
    msg['Subject'] = subject
    if in_reply_to:
        msg['In-Reply-To'] = in_reply_to
        # Build References: use existing References header from original, then append original Message-ID
        if references:
            msg['References'] = references
        else:
            msg['References'] = in_reply_to
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    smtp = smtplib.SMTP(provider["smtp"], provider["smtp_port"])
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    xoauth_b64 = base64.b64encode(_xoauth2_string(email_addr, token)).decode()
    smtp.docmd("AUTH", f"XOAUTH2 {xoauth_b64}")
    smtp.sendmail(email_addr, [to_addr], msg.as_string())
    smtp.quit()

    print(json.dumps({"ok": True, "to": to_addr, "subject": subject, "in_reply_to": in_reply_to}, ensure_ascii=False))


def cmd_list_accounts(accounts: dict):
    """List configured accounts (safe info only, no emails)."""
    result = []
    for name, info in accounts.items():
        result.append({
            "account": name,
            "provider": info.get("provider"),
        })
    print(json.dumps({"accounts": result}, indent=2))


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip())
        sys.exit(1)

    accounts = load_accounts()
    command = sys.argv[1]

    if command == "list-accounts":
        cmd_list_accounts(accounts)
        return

    if len(sys.argv) < 3:
        print(__doc__.strip())
        sys.exit(1)

    account = sys.argv[1]
    command = sys.argv[2]

    if account not in accounts:
        print(json.dumps({"error": f"Unknown account: {account}"}))
        sys.exit(1)

    try:
        if command == "list":
            limit = 20
            if "--limit" in sys.argv:
                idx = sys.argv.index("--limit")
                limit = int(sys.argv[idx + 1])
            imap = connect(account, accounts)
            try:
                cmd_list(imap, limit)
            finally:
                imap.logout()

        elif command == "read":
            uid = int(sys.argv[3])
            imap = connect(account, accounts)
            try:
                cmd_read(imap, uid)
            finally:
                imap.logout()

        elif command == "flag":
            uid = int(sys.argv[3])
            action = "seen"
            if "--seen" in sys.argv:
                action = "seen"
            elif "--unseen" in sys.argv:
                action = "unseen"
            elif "--delete" in sys.argv:
                action = "delete"
            imap = connect(account, accounts)
            try:
                cmd_flag(imap, uid, action)
            finally:
                imap.logout()

        elif command == "delete":
            uid = int(sys.argv[3])
            imap = connect(account, accounts)
            try:
                cmd_delete(imap, uid)
            finally:
                imap.logout()

        elif command == "send":
            to_addr = None
            subject = ""
            body = ""
            in_reply_to = None
            references = None
            if "--to" in sys.argv:
                idx = sys.argv.index("--to")
                to_addr = sys.argv[idx + 1]
            if "--subject" in sys.argv:
                idx = sys.argv.index("--subject")
                subject = sys.argv[idx + 1]
            if "--in-reply-to" in sys.argv:
                idx = sys.argv.index("--in-reply-to")
                in_reply_to = sys.argv[idx + 1]
            if "--references" in sys.argv:
                idx = sys.argv.index("--references")
                references = sys.argv[idx + 1]
            if "--body-file" in sys.argv:
                idx = sys.argv.index("--body-file")
                with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                    body = f.read()
            elif "--body" in sys.argv:
                idx = sys.argv.index("--body")
                body = sys.argv[idx + 1]
            if not to_addr:
                print(json.dumps({"error": "--to is required"}))
                sys.exit(1)
            cmd_send(account, accounts, to_addr, subject, body, in_reply_to, references)

        elif command == "reply":
            uid = int(sys.argv[3])
            body = ""
            if "--body-file" in sys.argv:
                idx = sys.argv.index("--body-file")
                with open(sys.argv[idx + 1], "r", encoding="utf-8") as f:
                    body = f.read()
            elif "--body" in sys.argv:
                idx = sys.argv.index("--body")
                body = sys.argv[idx + 1]
            if not body:
                print(json.dumps({"error": "--body or --body-file is required"}))
                sys.exit(1)
            cmd_reply(account, accounts, uid, body)

        else:
            print(json.dumps({"error": f"Unknown command: {command}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e), "code": type(e).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    main()
