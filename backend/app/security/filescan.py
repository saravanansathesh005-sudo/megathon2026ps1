"""Deterministic file risk analysis.

An uploaded file is untrusted input. This module inspects it and reports risk
indicators. It never executes it, never extracts an archive to disk, and never
calls out to a network. Everything here is regex, byte comparison and arithmetic,
so it produces the same answer offline, every time, in a few milliseconds.

**This is not antivirus.** There is no signature database and no reputation
lookup, so it cannot tell you "this is Emotet". It tells you what the file
structurally *is* and what it would *do* - a file claiming to be a JPEG that
starts with the Windows executable header, a shell script that pipes curl into
bash, an archive whose entries escape the extraction directory. Those are the
things that survive being renamed, repacked or recompiled, which is exactly what
a signature does not.

The scan produces evidence. The deterministic policy engine decides.
"""

from __future__ import annotations

import hashlib
import io
import math
import re
import zipfile

MAX_FILE_BYTES = 10 * 1024 * 1024
ENTROPY_SAMPLE_BYTES = 256 * 1024
SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")

# Magic numbers, longest first so a specific match wins over a generic one.
SIGNATURES: list[tuple[bytes, str, str]] = [
    (b"\x7fELF", "elf", "Linux/Unix executable"),
    (b"MZ", "pe", "Windows executable"),
    (b"\xca\xfe\xba\xbe", "class", "Java class file"),
    (b"dex\n", "dex", "Android Dalvik executable"),
    (b"\xcf\xfa\xed\xfe", "macho", "macOS executable"),
    (b"\xce\xfa\xed\xfe", "macho", "macOS executable"),
    (b"\xfe\xed\xfa\xcf", "macho", "macOS executable"),
    (b"\xfe\xed\xfa\xce", "macho", "macOS executable"),
    (b"PK\x03\x04", "zip", "ZIP container"),
    (b"PK\x05\x06", "zip", "ZIP container (empty)"),
    (b"Rar!\x1a\x07", "rar", "RAR archive"),
    (b"7z\xbc\xaf\x27\x1c", "7z", "7-Zip archive"),
    (b"\x1f\x8b", "gzip", "gzip archive"),
    (b"%PDF", "pdf", "PDF document"),
    (b"\x89PNG\r\n\x1a\n", "png", "PNG image"),
    (b"\xff\xd8\xff", "jpeg", "JPEG image"),
    (b"GIF87a", "gif", "GIF image"),
    (b"GIF89a", "gif", "GIF image"),
    (b"\x00\x00\x01\x00", "ico", "Windows icon"),
    (b"#!", "script", "Script with an interpreter line"),
]

# What each detected type is legitimately called.
EXPECTED_EXTENSIONS = {
    "elf": {"", "so", "bin", "elf", "o", "out", "ko"},
    "pe": {"exe", "dll", "sys", "scr", "com", "ocx", "cpl", "msi", "efi"},
    "class": {"class"},
    "dex": {"dex"},
    "macho": {"", "dylib", "bundle", "o"},
    "zip": {"zip", "apk", "jar", "docx", "xlsx", "pptx", "odt", "ods", "epub",
            "aar", "war", "ipa", "whl", "nupkg", "xpi", "crx", "kmz"},
    "rar": {"rar"},
    "7z": {"7z"},
    "gzip": {"gz", "tgz", "gzip"},
    "pdf": {"pdf"},
    "png": {"png"},
    "jpeg": {"jpg", "jpeg", "jpe"},
    "gif": {"gif"},
    "ico": {"ico", "cur"},
}

# Types that run as code on some machine.
EXECUTABLE_TYPES = {"elf", "pe", "macho", "dex", "class"}

# Extensions that execute when opened, whatever the icon says.
EXECUTABLE_EXTENSIONS = {
    "exe", "scr", "com", "pif", "cpl", "msi", "msp", "bat", "cmd", "vbs", "vbe",
    "js", "jse", "wsf", "wsh", "ps1", "psm1", "sh", "bash", "zsh", "run", "app",
    "apk", "jar", "dll", "so", "dylib", "hta", "reg", "lnk", "deb", "rpm", "dmg",
}

# Extensions that read as harmless to a person clicking them.
INNOCENT_EXTENSIONS = {
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "csv",
    "jpg", "jpeg", "png", "gif", "bmp", "svg", "mp3", "mp4", "avi", "mov", "zip",
}

TEXT_EXTENSIONS = {
    "sh", "bash", "zsh", "bat", "cmd", "ps1", "psm1", "py", "js", "rb", "pl",
    "php", "txt", "yml", "yaml", "json", "conf", "cfg", "ini", "env", "sql",
}

# ---------------------------------------------------------------- script behaviour
# (pattern, severity, title, detail, fix)
SCRIPT_PATTERNS: list[tuple[str, str, str, str, str]] = [
    (r"(?:curl|wget)[^\n|]{0,200}\|\s*(?:sudo\s+)?(?:ba|z|k)?sh",
     "CRITICAL", "Downloads and executes remote code",
     "The script fetches a payload over the network and pipes it straight into a "
     "shell. Whatever that server returns runs with the user's privileges, and it "
     "can return something different tomorrow.",
     "Download to a file, verify a checksum or signature, review it, then run it."),
    (r"base64\s+(?:--decode|-d|-D)[^\n]{0,120}\|\s*(?:ba|z|k)?sh",
     "CRITICAL", "Executes base64-decoded commands",
     "Encoding exists here only to stop a reader and a log from seeing the command.",
     "Remove it. Legitimate scripts have no reason to hide their own commands."),
    (r"\brm\s+(?:-[a-zA-Z]*[rR][a-zA-Z]*[fF]|-[a-zA-Z]*[fF][a-zA-Z]*[rR])\s+"
     r"(?:/|~|\$HOME|/\*|\.\s*$)",
     "CRITICAL", "Recursive force delete of a root or home path",
     "Removes an entire filesystem or home directory with no confirmation and no "
     "recovery.",
     "Delete a specific, named directory and never interpolate the path."),
    (r":\s*\(\s*\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",
     "CRITICAL", "Fork bomb",
     "Spawns processes until the machine stops responding.",
     "Remove it. This has no legitimate use."),
    (r"\bdd\s+[^\n]{0,120}\bof=/dev/(?:[sh]d[a-z]|nvme|disk)",
     "CRITICAL", "Writes raw data over a block device",
     "Overwrites a disk directly, destroying every partition on it.",
     "Never target a raw device from a script."),
    (r"\bmkfs(?:\.[a-z0-9]+)?\s+/dev/",
     "CRITICAL", "Formats a disk",
     "Creates a new filesystem, discarding everything already on the device.",
     "Remove it."),
    (r"(?:bash|sh)\s+-i\s*>&\s*/dev/tcp/|/dev/tcp/\d|\bnc\b[^\n]{0,60}\s-[a-z]*e[a-z]*\s",
     "CRITICAL", "Reverse shell",
     "Opens an interactive shell back to a remote host, handing that host control "
     "of this machine.",
     "Remove it. This is not a deployment technique."),
    (r"(?i)vssadmin[^\n]{0,80}delete[^\n]{0,40}shadows|wbadmin[^\n]{0,60}delete",
     "CRITICAL", "Deletes Windows shadow copies",
     "Destroys the restore points recovery depends on. This is the standard "
     "opening move of ransomware.",
     "Remove it."),
    (r"(?i)(?:Invoke-Expression|\bIEX\b)[^\n]{0,120}(?:DownloadString|DownloadFile|WebClient)",
     "CRITICAL", "PowerShell downloads and evaluates remote code",
     "Fetches a script from the network and evaluates it in memory, leaving little "
     "on disk to inspect afterwards.",
     "Download, verify, review, then run."),
    (r"(?i)Set-MpPreference[^\n]{0,120}Disable(?:RealtimeMonitoring|IOAVProtection)"
     r"[^\n]{0,20}\$?true",
     "CRITICAL", "Disables Windows Defender real-time protection",
     "Turns off the endpoint's own defences before doing something else.",
     "Remove it. No installer needs this."),
    (r"(?i)\bchmod\s+(?:-R\s+)?0?777\b",
     "HIGH", "Grants world-writable permissions",
     "Any user or process on the machine can modify these files, including "
     "replacing an executable with their own.",
     "Grant the narrowest permission that works, usually 644 or 755."),
    (r"(?i)-Enc(?:odedCommand)?\s+[A-Za-z0-9+/=]{40,}",
     "HIGH", "Base64-encoded PowerShell command",
     "The real command is hidden from anyone reading the script or the logs.",
     "Write the command in clear text."),
    (r"(?i)reg(?:\.exe)?\s+add[^\n]{0,160}(?:CurrentVersion\\\\?Run|Winlogon\\\\?Shell)",
     "HIGH", "Registry persistence",
     "Registers something to launch at every login, surviving reboots.",
     "Use a documented installer or a scheduled task the user can see."),
    (r"(?i)netsh\s+advfirewall[^\n]{0,80}(?:state\s+off|set\s+allprofiles[^\n]{0,30}off)",
     "HIGH", "Disables the Windows firewall",
     "Removes network filtering for every profile.",
     "Add a specific rule instead of disabling the firewall."),
    (r"\bNOPASSWD\s*:|\becho\s+[^\n]{0,60}>>\s*/etc/sudoers",
     "HIGH", "Grants passwordless sudo",
     "Escalates privilege permanently and silently.",
     "Remove it."),
    (r"(?:curl|wget)\s+[^\n]{0,80}https?://(?:\d{1,3}\.){3}\d{1,3}",
     "MEDIUM", "Downloads from a bare IP address",
     "A hard-coded IP skips DNS and certificate-name checks, and is typical of "
     "throwaway infrastructure.",
     "Use a hostname over HTTPS and verify the certificate."),
    (r"(?:crontab\s+-|>>\s*(?:~|\$HOME)/\.(?:bashrc|zshrc|profile)|"
     r"systemctl\s+enable|launchctl\s+load)",
     "MEDIUM", "Installs persistence",
     "Arranges to run again later, without the user asking again.",
     "Only if the user knowingly installed a service; otherwise remove it."),
    (r"\bhistory\s+-c\b|>\s*(?:~|\$HOME)/\.bash_history|Clear-History",
     "MEDIUM", "Clears shell history",
     "Removes the record of what was run. Anti-forensic, not maintenance.",
     "Remove it."),
    (r"(?i)(?:AKIA[0-9A-Z]{16}|(?:password|passwd|api[_-]?key|secret|token)"
     r"\s*=\s*[\"'][^\"']{8,}[\"'])",
     "HIGH", "Hard-coded credential",
     "A secret in a script is in every copy of that script.",
     "Read it from the environment at run time."),
]

_SCRIPT_COMPILED = [(re.compile(p, re.MULTILINE), sev, t, d, f)
                    for p, sev, t, d, f in SCRIPT_PATTERNS]

# Android permissions worth a second look, and why.
APK_PERMISSIONS = {
    "SEND_SMS": ("HIGH", "can send SMS, including to premium-rate numbers"),
    "READ_SMS": ("HIGH", "can read messages, including one-time passcodes"),
    "RECEIVE_SMS": ("HIGH", "can intercept incoming messages"),
    "CALL_PHONE": ("MEDIUM", "can place calls without asking"),
    "READ_CONTACTS": ("MEDIUM", "can read the address book"),
    "READ_CALL_LOG": ("HIGH", "can read who was called and when"),
    "RECORD_AUDIO": ("HIGH", "can record from the microphone"),
    "CAMERA": ("MEDIUM", "can capture photo and video"),
    "ACCESS_FINE_LOCATION": ("MEDIUM", "can track precise location"),
    "REQUEST_INSTALL_PACKAGES": ("CRITICAL", "can install further applications"),
    "BIND_ACCESSIBILITY_SERVICE": ("CRITICAL",
                                   "can observe and control the whole interface - "
                                   "the usual route to on-device fraud"),
    "SYSTEM_ALERT_WINDOW": ("HIGH", "can draw over other apps, enabling overlay attacks"),
    "RECEIVE_BOOT_COMPLETED": ("MEDIUM", "starts itself when the device boots"),
    "READ_EXTERNAL_STORAGE": ("LOW", "can read shared storage"),
    "WRITE_EXTERNAL_STORAGE": ("LOW", "can write shared storage"),
}

ZIP_BOMB_RATIO = 100
ZIP_BOMB_MIN_BYTES = 5 * 1024 * 1024


def _finding(severity: str, title: str, detail: str, fix: str) -> dict:
    return {"severity": severity, "title": title, "detail": detail, "fix": fix,
            "source": "scanner"}


def _extension(filename: str) -> str:
    name = (filename or "").strip().rstrip(".")
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _detect_type(data: bytes) -> tuple[str, str]:
    """Identify the file from its bytes. The name is not evidence."""
    for magic, kind, label in SIGNATURES:
        if data.startswith(magic):
            return kind, label
    return "unknown", "unrecognised format"


def entropy(data: bytes) -> float:
    """Shannon entropy in bits per byte, 0.0 to 8.0.

    Compressed and encrypted data sits near 8.0; text and code sit near 4 to 5.
    High entropy in something claiming to be a document means a packed payload.
    """
    sample = data[:ENTROPY_SAMPLE_BYTES]
    if not sample:
        return 0.0
    counts = [0] * 256
    for byte in sample:
        counts[byte] += 1
    size = len(sample)
    total = 0.0
    for count in counts:
        if count:
            p = count / size
            total -= p * math.log2(p)
    return round(total, 2)


def _scan_script(text: str) -> list[dict]:
    findings = []
    for rx, severity, title, detail, fix in _SCRIPT_COMPILED:
        match = rx.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            item = _finding(severity, title, detail, fix)
            item["line"] = line
            item["evidence"] = match.group(0).strip()[:160]
            findings.append(item)
    return findings


def _scan_zip(data: bytes, extension: str) -> tuple[list[dict], dict]:
    """Read the archive's central directory. Nothing is extracted to disk."""
    findings: list[dict] = []
    facts: dict = {"entries": 0, "uncompressed_bytes": 0, "compression_ratio": None}
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = archive.infolist()
    except (zipfile.BadZipFile, OSError, RuntimeError, ValueError):
        findings.append(_finding(
            "MEDIUM", "Archive is malformed",
            "The ZIP structure could not be read, so its contents cannot be "
            "inspected. A corrupt archive may also be a deliberately malformed one.",
            "Reject it, or obtain an intact copy from the original source."))
        return findings, facts

    names = [i.filename for i in infos]
    facts["entries"] = len(infos)
    facts["uncompressed_bytes"] = sum(i.file_size for i in infos)
    compressed = sum(i.compress_size for i in infos) or 1
    ratio = facts["uncompressed_bytes"] / compressed
    facts["compression_ratio"] = round(ratio, 1)

    # Path traversal: an entry that writes outside the extraction directory.
    escaping = [n for n in names
                if n.startswith("/") or ".." in n.replace("\\", "/").split("/")
                or re.match(r"^[A-Za-z]:", n)]
    if escaping:
        findings.append(_finding(
            "CRITICAL", "Archive entry escapes the extraction directory",
            "Entries such as " + ", ".join(escaping[:3]) + " use an absolute or "
            "parent path, so extracting the archive overwrites files elsewhere on "
            "the system. This is the Zip Slip vulnerability.",
            "Reject the archive. A legitimate one uses relative paths only."))

    if ratio >= ZIP_BOMB_RATIO and facts["uncompressed_bytes"] >= ZIP_BOMB_MIN_BYTES:
        findings.append(_finding(
            "HIGH", "Extreme compression ratio",
            "Expands to " + str(round(facts["uncompressed_bytes"] / 1048576, 1))
            + " MB from " + str(round(compressed / 1024, 1)) + " KB, a ratio of "
            + str(facts["compression_ratio"]) + ":1. An archive built to exhaust "
            "disk or memory on extraction looks exactly like this.",
            "Do not extract it. Enforce a decompression limit in whatever handles it."))

    # Executables riding inside a container that should not carry them.
    if extension in ("docx", "xlsx", "pptx", "odt", "ods", "epub"):
        if any(n.endswith(("vbaProject.bin", ".bin")) and "vba" in n.lower() for n in names):
            findings.append(_finding(
                "HIGH", "Document contains a macro project",
                "The document embeds VBA code, which runs when macros are enabled.",
                "Open it in Protected View, or request a macro-free copy."))
        carried = [n for n in names if _extension(n) in ("exe", "dll", "scr", "bat", "ps1")]
        if carried:
            findings.append(_finding(
                "CRITICAL", "Document carries an executable",
                "Contains " + ", ".join(carried[:3]) + ". A document has no reason "
                "to embed a program.",
                "Reject it."))

    if extension == "apk" or any(n == "classes.dex" for n in names):
        findings.extend(_scan_apk(archive, names, facts))

    return findings, facts


def _scan_apk(archive: zipfile.ZipFile, names: list[str], facts: dict) -> list[dict]:
    """Inspect an Android package.

    The manifest is binary XML. Rather than pretend to parse it, the permission
    names are recovered from its string pool, which is plain UTF-16 or UTF-8 text
    inside the blob. That is honest and it is enough to name what the app asks for.
    """
    findings: list[dict] = []
    facts["is_apk"] = True
    facts["dex_files"] = [n for n in names if n.endswith(".dex")]

    if not facts["dex_files"]:
        findings.append(_finding(
            "MEDIUM", "Android package with no code",
            "No classes.dex is present, which is unusual for a real application.",
            "Treat the package as suspect."))

    native = [n for n in names if n.endswith(".so")]
    if native:
        facts["native_libraries"] = native[:20]
        findings.append(_finding(
            "INFO", "Contains native libraries",
            str(len(native)) + " compiled .so libraries are bundled. Native code is "
            "normal in many apps, and it is also where analysis is hardest.",
            "No action by itself; weigh it with the permissions below."))

    try:
        manifest = archive.read("AndroidManifest.xml")
    except (KeyError, OSError, RuntimeError):
        findings.append(_finding(
            "HIGH", "Android package has no manifest",
            "AndroidManifest.xml is missing, so the package cannot declare what it "
            "is or what it wants. No legitimate APK is built this way.",
            "Reject it."))
        return findings

    text = manifest.decode("utf-16-le", "ignore") + " " + manifest.decode("utf-8", "ignore")
    requested = sorted({p for p in APK_PERMISSIONS if p in text})
    facts["permissions"] = requested

    dangerous = [(p, APK_PERMISSIONS[p]) for p in requested
                 if APK_PERMISSIONS[p][0] in ("CRITICAL", "HIGH")]
    for name, (severity, why) in dangerous:
        findings.append(_finding(
            severity, "Requests " + name,
            "The application " + why + ".",
            "Confirm the app's stated purpose needs this. If it does not, reject it."))

    if len(dangerous) >= 3:
        findings.append(_finding(
            "CRITICAL", "Permission set matches a surveillance profile",
            "Requests " + str(len(dangerous)) + " separately dangerous permissions: "
            + ", ".join(n for n, _ in dangerous) + ". Individually each has uses; "
            "together they describe an application that can read messages, listen, "
            "and act on the user's behalf.",
            "Do not install. Verify the publisher through an independent channel."))
    return findings


def scan(filename: str, data: bytes) -> dict:
    """Analyse an uploaded file and return structured evidence.

    Nothing is executed, extracted to disk, or sent anywhere.
    """
    data = data or b""
    size = len(data)
    extension = _extension(filename)
    kind, label = _detect_type(data)
    digest = hashlib.sha256(data).hexdigest()
    findings: list[dict] = []
    facts: dict = {}

    if size == 0:
        return _result(filename, extension, "empty", "empty file", digest, 0, 0.0,
                       [_finding("LOW", "File is empty",
                                 "There is nothing to inspect.",
                                 "Check the upload completed.")], {})

    if size > MAX_FILE_BYTES:
        findings.append(_finding(
            "MEDIUM", "File exceeds the inspection limit",
            "At " + str(round(size / 1048576, 1)) + " MB this is larger than the "
            + str(MAX_FILE_BYTES // 1048576) + " MB AEGIS will read, so only the "
            "first portion was examined.",
            "Scan it with a dedicated tool before accepting it."))
        data = data[:MAX_FILE_BYTES]

    # ------------------------------------------------ what it is versus what it claims
    expected = EXPECTED_EXTENSIONS.get(kind)
    if expected is not None and extension not in expected:
        severity = "CRITICAL" if kind in EXECUTABLE_TYPES else "HIGH"
        findings.append(_finding(
            severity, "File type does not match its extension",
            "The name ends in ." + (extension or "(none)") + " but the contents are "
            "a " + label + ". Renaming a program to look like a document is the "
            "oldest delivery trick there is, and the extension is what a person "
            "checks before double-clicking.",
            "Reject it. Ask the sender for the file in its declared format."))

    if kind in EXECUTABLE_TYPES:
        findings.append(_finding(
            "HIGH", "File is an executable program",
            "This is a " + label + ". Once run it has the privileges of whoever "
            "ran it.",
            "Only run it if you can attribute it to a source you already trust."))

    # invoice.pdf.exe - the visible extension is not the effective one.
    parts = (filename or "").lower().split(".")
    if len(parts) >= 3 and parts[-1] in EXECUTABLE_EXTENSIONS \
            and parts[-2] in INNOCENT_EXTENSIONS:
        findings.append(_finding(
            "CRITICAL", "Double extension disguises an executable",
            "The name reads as ." + parts[-2] + " but the effective extension is ."
            + parts[-1] + ". Systems that hide known extensions show this as a "
            + parts[-2] + " file.",
            "Reject it. This construction has no legitimate use."))

    # ------------------------------------------------------------------ what it does
    is_textual = extension in TEXT_EXTENSIONS or kind == "script"
    # Plain text carries no magic number, so "unrecognised" would be technically
    # true and useless. Name it for what it is.
    if is_textual and kind == "unknown":
        kind, label = "text", "plain text"
    if is_textual:
        text = data.decode("utf-8", "replace")
        script_findings = _scan_script(text)
        findings.extend(script_findings)
        facts["lines"] = text.count("\n") + 1

    if kind == "zip":
        zip_findings, zip_facts = _scan_zip(data, extension)
        findings.extend(zip_findings)
        facts.update(zip_facts)

    # --------------------------------------------------------------------- entropy
    bits = entropy(data)
    facts["entropy"] = bits
    compressed_by_design = kind in ("zip", "gzip", "rar", "7z", "png", "jpeg", "gif")
    if bits >= 7.5 and not compressed_by_design and kind != "unknown":
        findings.append(_finding(
            "HIGH", "Contents look packed or encrypted",
            "Entropy is " + str(bits) + " of a possible 8.0, which is what "
            "compressed or encrypted data looks like - not what a " + label
            + " normally looks like. Packing is how a payload avoids being read.",
            "Treat it as an unknown binary and do not run it."))

    if kind == "unknown" and not is_textual:
        findings.append(_finding(
            "LOW", "Unrecognised file format",
            "The header matches no known format, so its structure cannot be checked.",
            "Confirm with the sender what this file is meant to be."))

    return _result(filename, extension, kind, label, digest, size, bits, findings, facts)


def _rank(finding: dict) -> int:
    try:
        return SEVERITIES.index(finding.get("severity", "INFO"))
    except ValueError:
        return len(SEVERITIES)


def _result(filename: str, extension: str, kind: str, label: str, digest: str,
            size: int, bits: float, findings: list[dict], facts: dict) -> dict:
    findings = sorted(findings, key=_rank)
    counts: dict[str, int] = {}
    for item in findings:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1

    highest = findings[0]["severity"] if findings else "NONE"
    if findings:
        summary = (str(len(findings)) + " risk indicator(s) found, highest severity "
                   + highest + ".")
    else:
        summary = "No risk indicators found in this " + label + "."

    return {
        "filename": filename,
        "extension": extension,
        "detected_type": kind,
        "detected_label": label,
        "sha256": digest,
        "size_bytes": size,
        "entropy": bits,
        "findings": findings,
        "counts": counts,
        "highest_severity": highest,
        "summary": summary,
        "facts": facts,
        "analysed_by": "scanner",
    }
