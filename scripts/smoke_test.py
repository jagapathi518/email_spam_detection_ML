"""
SpamGuard AI — Smoke Test

Usage: python scripts/smoke_test.py <base_url>
Example: python scripts/smoke_test.py https://spamguard-ai.onrender.com

Checks:
  1. /api/health (with long first-request timeout for cold start)
  2. One spam sample prediction
  3. One legit sample prediction
  4. Empty-input 400/422
  5. Security headers
"""

import json
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def check(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def request_json(url, data=None, method="GET", timeout=90):
    """Make an HTTP request and return (status_code, response_data, headers)."""
    headers_dict = {"Content-Type": "application/json"} if data else {}

    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers_dict, method=method)

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        resp_data = json.loads(resp.read().decode("utf-8"))
        return resp.status, resp_data, dict(resp.headers)
    except urllib.error.HTTPError as e:
        try:
            resp_data = json.loads(e.read().decode("utf-8"))
        except Exception:
            resp_data = {"error": str(e)}
        return e.code, resp_data, dict(e.headers)
    except Exception as e:
        return 0, {"error": str(e)}, {}


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_test.py <base_url>")
        print("Example: python scripts/smoke_test.py http://localhost:5000")
        return 1

    base_url = sys.argv[1].rstrip("/")
    results = []

    print("\nSpamGuard AI — Smoke Test")
    print(f"Target: {base_url}")
    print("=" * 50)

    # 1. Health check (long timeout for cold start)
    print("\n1. Health Check")
    start = time.time()
    status, data, headers = request_json(f"{base_url}/api/health", timeout=120)
    elapsed = time.time() - start
    results.append(check("Health endpoint returns 200", status == 200, f"status={status}, time={elapsed:.1f}s"))
    if status == 200:
        results.append(check("Health has model_loaded field", "model_loaded" in data))
        results.append(check("Model is loaded", data.get("model_loaded") is True))

    # 2. Spam sample
    print("\n2. Spam Sample Prediction")
    spam_data = {
        "subject": "URGENT: You Won $1,000,000",
        "body": "Congratulations! You have won a million dollars. Click here to claim your prize immediately. This offer expires today. Verify your account at http://192.168.1.1/claim",
    }
    status, data, headers = request_json(f"{base_url}/api/predict", data=spam_data, method="POST")
    results.append(check("Spam prediction returns 200", status == 200, f"status={status}"))
    if status == 200:
        results.append(check("Has label field", "label" in data))
        results.append(
            check(
                "Label is spam or uncertain", data.get("label") in ("spam", "uncertain"), f"label={data.get('label')}"
            )
        )
        results.append(check("Has score field", "score" in data))
        results.append(check("Has signals field", "signals" in data))
        results.append(check("Has disclaimer field", "disclaimer" in data))
        results.append(check("Has model_version field", "model_version" in data))

    # 3. Legit sample
    print("\n3. Legit Sample Prediction")
    legit_data = {
        "subject": "Team Meeting Notes",
        "body": "Hi everyone, here are the notes from today's meeting. The Q3 report is due next Friday. Please submit your sections by Wednesday. Best, Sarah",
    }
    status, data, headers = request_json(f"{base_url}/api/predict", data=legit_data, method="POST")
    results.append(check("Legit prediction returns 200", status == 200, f"status={status}"))
    if status == 200:
        results.append(
            check(
                "Label is not_spam or uncertain",
                data.get("label") in ("not_spam", "uncertain"),
                f"label={data.get('label')}",
            )
        )

    # 4. Empty input
    print("\n4. Empty Input Validation")
    status, data, headers = request_json(f"{base_url}/api/predict", data={"body": ""}, method="POST")
    results.append(check("Empty body returns 422", status == 422, f"status={status}"))
    if status == 422:
        results.append(check("Error response has error field", "error" in data))

    # 5. Security headers
    print("\n5. Security Headers")
    status, data, resp_headers = request_json(f"{base_url}/api/health")
    if resp_headers:
        results.append(
            check(
                "X-Content-Type-Options present",
                "X-Content-Type-Options" in resp_headers or "x-content-type-options" in resp_headers,
            )
        )
        results.append(
            check(
                "Content-Security-Policy present",
                "Content-Security-Policy" in resp_headers or "content-security-policy" in resp_headers,
            )
        )
        results.append(
            check("Referrer-Policy present", "Referrer-Policy" in resp_headers or "referrer-policy" in resp_headers)
        )

    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 ALL CHECKS PASSED!")
        return 0
    else:
        print(f"⚠️  {total - passed} check(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
