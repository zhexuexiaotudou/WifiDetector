# WifiDetector project guide

## Product boundary

- This is a Windows single-PC, local-only monitoring tool for explicitly authorized networks.
- Keep the web service bound to loopback. Do not broaden it to LAN or public access without an explicit security review.
- Never add password cracking, CAPTCHA bypass, packet-content capture, DNS/domain logging, interception, deauthentication, or automated misconduct conclusions.
- Do not persist complete client MAC addresses. Preserve the HMAC-SHA256 anonymization and log redaction boundary.

## Implementation invariants

- Scan the eight configured rooms sequentially. They reuse the same gateway address on isolated LANs and must not be queried concurrently.
- Keep H10e-31 capabilities false until a field capability is supported by sanitized, authorized evidence.
- Prefer a documented JSON API adapter. Use DOM extraction only when no stable API exists, and keep authentication manual when CAPTCHA or human verification appears.
- Store credentials only in Windows profiles, local `.env`, Credential Manager, or runtime input. Never commit credentials, cookies, browser state, raw HAR files, screenshots, or field databases.
- Keep room IDs exactly `2301`, `2302`, `2303`, `2305`, `2306`, `2307`, `2309`, and `2310` unless the product scope is explicitly changed.
- A single authorized field-evidence room may use `field_test_mode: true`; keep it to exactly one room and never report that result as acceptance of the production eight-room set.
- `local_pc` is a degraded evidence source: it may use bounded ICMP/ARP and SSDP, but must never be described as a complete client list, per-device traffic, TV power, playback, HDMI, or viewer evidence.
- Generic type labels (`手机`, `平板`, `个人电脑`, `未知设备`) classify a device but do not authorize it or suppress unknown-device events; only explicit allowed/fixed/TV labels may do that.

## Verification

Run these checks before opening a pull request:

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\mypy.exe app
.\.venv\Scripts\pytest.exe -q
```

For UI or service changes, start the local service, wait for readiness, exercise the affected HTTP path, and inspect the rendered page. Real field claims additionally require the Wi-Fi and evidence gates in `docs/FIELD_SETUP.md`.

## Documentation map

- `README.md`: setup, scope, and current operator entry point.
- `docs/ARCHITECTURE.md`: data flow, API surface, and SQLite model.
- `docs/OPERATOR_GUIDE.md`: commands, environment variables, and local operations.
- `docs/FIELD_SETUP.md`: authorized field gates and calibration.
- `docs/PRIVACY_AND_LIMITATIONS.md`: non-negotiable privacy and inference limits.
- `IMPLEMENTATION_STATUS.md`: verified delivery status and explicit field blockers.
