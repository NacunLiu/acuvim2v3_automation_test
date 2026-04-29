"""Send test report email via Gmail SMTP."""
import glob
import os
import smtplib
import ssl
import sys
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_html(status, build_number, build_url, log_text):
    color = "green" if status == "SUCCESS" else "red"
    return f"""
<html><body style="font-family:sans-serif">
<h2>AcuVim II v3 Automation Test Report</h2>
<table border="1" cellpadding="8" cellspacing="0">
  <tr><td><b>Build</b></td><td>#{build_number}</td></tr>
  <tr><td><b>Status</b></td>
      <td style="color:{color};font-weight:bold">{status}</td></tr>
  <tr><td><b>Console</b></td>
      <td><a href="{build_url}console">View Full Log</a></td></tr>
</table>
<h3>Test Log (last 200 lines)</h3>
<pre style="background:#f4f4f4;padding:12px;font-size:12px">{log_text}</pre>
</body></html>
"""


def collect_logs(log_dir):
    lines = []
    for path in sorted(glob.glob(os.path.join(log_dir, "*.log"))):
        lines.append(f"=== {os.path.basename(path)} ===")
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                lines.extend(f.readlines()[-200:])
        except OSError:
            lines.append("(could not read file)")
    return "".join(lines) if lines else "No log files found."


def send_report(status, build_number, build_url, log_dir, attach_dir):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_PASS"]
    to_email = os.environ.get("REPORT_EMAIL", "nacun.liu@accuenergy.com")

    log_text = collect_logs(log_dir)

    msg = MIMEMultipart("mixed")
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg["Subject"] = (
        f"[Jenkins] AcuVim II v3 Test - {status} - Build #{build_number}"
    )

    msg.attach(MIMEText(build_html(status, build_number, build_url, log_text), "html"))

    for pattern in [
        os.path.join(attach_dir, "logs", "*.log"),
        os.path.join(attach_dir, "data", "*.png"),
    ]:
        for path in glob.glob(pattern):
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(path)}"',
            )
            msg.attach(part)

    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls(context=ctx)
        server.login(gmail_user, gmail_pass)
        server.sendmail(gmail_user, to_email, msg.as_string())
    print(f"Report sent to {to_email}")


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: send_report.py <STATUS> <BUILD_NUMBER> <BUILD_URL> <TEST_DIR>")
        sys.exit(1)
    send_report(
        status=sys.argv[1],
        build_number=sys.argv[2],
        build_url=sys.argv[3],
        log_dir=os.path.join(sys.argv[4], "logs"),
        attach_dir=sys.argv[4],
    )
