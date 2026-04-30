# driftwatch

Lightweight daemon that detects infrastructure configuration drift and emits structured alerts.

---

## Installation

```bash
pip install driftwatch
```

Or install from source:

```bash
git clone https://github.com/yourorg/driftwatch.git && cd driftwatch && pip install .
```

---

## Usage

Define your expected configuration in a YAML file:

```yaml
# driftwatch.yaml
checks:
  - name: nginx-config
    path: /etc/nginx/nginx.conf
    checksum: sha256:a3f1c9...
  - name: sshd-port
    type: sysctl
    key: net.ipv4.conf.all.forwarding
    expected: "0"

alerts:
  output: json
  destination: stdout
```

Then run the daemon:

```bash
driftwatch --config driftwatch.yaml --interval 60
```

Driftwatch will poll at the specified interval (in seconds) and emit structured JSON alerts when drift is detected:

```json
{
  "timestamp": "2024-11-01T12:34:56Z",
  "check": "sshd-port",
  "status": "drift_detected",
  "expected": "0",
  "actual": "1"
}
```

Pipe alerts to any downstream system — log aggregators, PagerDuty, Slack webhooks, or a SIEM.

---

## License

This project is licensed under the [MIT License](LICENSE).