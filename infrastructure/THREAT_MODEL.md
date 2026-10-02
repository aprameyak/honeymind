# HoneyMind Threat Model (Lab)

## Scope

Defensive research platform running exclusively in Docker Compose on a researcher workstation.

## Assets

- Host OS integrity
- Researcher credentials and cloud keys (must never enter containers)
- Integrity of telemetry / experimental conclusions

## Adversaries

1. Automated scanners and scripted bots (simulated or accidental)
2. Human operators probing decoys
3. Simulated LLM agents constrained by allowlist
4. Prompt-injection payloads targeting the deception LLM path

## Controls

| Control | Implementation |
|---------|----------------|
| Isolation | Separate `honeypot_net` / `backend_net`; honeypot net internal (no egress); no host networking |
| Least privilege | `cap_drop: ALL`, `no-new-privileges`, non-root honeypot images |
| Filesystem | Honeypot `read_only: true` + tmpfs `/tmp` |
| Resources | CPU / memory / PID limits |
| Secrets | Synthetic-only; settings validator rejects AWS-looking keys |
| Input | Rate limits, max body size, attacker-text sanitization |
| LLM | Optional; no tools; output validation; untrusted delimiters |

## Non-goals

- Production Internet deployment
- Real malware execution or credential theft against external systems
- Definitive attribution of real-world actors as AI-generated
