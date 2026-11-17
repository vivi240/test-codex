"""Refresh the publicly published VPNBook OpenVPN credentials.

Executed on a GitHub-hosted runner. Does not print the password in logs.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import urllib.request

SOURCE = "https://www.vpnbook.com/freevpn/openvpn"
TARGET = Path("current.json")

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipped = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript"):
            self.skipped.append(tag)

    def handle_endtag(self, tag):
        if self.skipped and tag == self.skipped[-1]:
            self.skipped.pop()

    def handle_data(self, data):
        if not self.skipped and data.strip():
            self.parts.append(data.strip())

def parse_password(html):
    parser = VisibleText()
    parser.feed(html)
    text = re.sub(r"\s+", " ", " ".join(parser.parts))
    pos = re.search(r"\bVPN Credentials\b", text, re.I)
    if not pos:
        raise ValueError("VPN Credentials section not found; retaining previous file")
    section = text[pos.end():pos.end() + 900]
    match = re.search(
        r"\bUsername\s+vpnbook\s+(?:Copy\s+)?Password\s+([A-Za-z0-9]{5,40})(?=\s+(?:Copy\b|Last updated\b))",
        section, re.I
    )
    if not match:
        raise ValueError("Could not verify password on official page")
    return match.group(1)

def download():
    request = urllib.request.Request(SOURCE, headers={
        "User-Agent": "Mozilla/5.0 (compatible; VPNBookCloudRelay/1.0)",
        "Accept": "text/html",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(request, timeout=25) as response:
        content = response.read(2_000_001)
        if len(content) > 2_000_000:
            raise ValueError("Unexpected response size")
        return content.decode(response.headers.get_content_charset() or "utf-8", "replace")

def main():
    password = parse_password(download())
    previous = {}
    if TARGET.is_file():
        try:
            previous = json.loads(TARGET.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    record = {
        "source": SOURCE,
        "username": "vpnbook",
        "password": password,
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "server": "de20.vpnbook.com",
        "protocol": "udp",
        "port": 25000,
    }
    TARGET.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("Verified VPNBook password:", "changed" if previous.get("password") != password else "unchanged")

if __name__ == "__main__":
    main()
