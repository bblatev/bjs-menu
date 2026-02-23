"""Comprehensive production endpoint tester for BJS Menu API."""
import json
import sys
import re
import time
import requests
from collections import defaultdict, Counter

BASE_URL = "http://127.0.0.1:8000"

# Generate a valid JWT token using the project's own security module
sys.path.insert(0, "/opt/bjs-menu/backend")
from app.core.security import create_access_token
TOKEN = create_access_token(data={"sub": "1", "email": "admin@bjs.bar", "role": "owner", "venue_id": 1})
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# First get the OpenAPI spec from local server (production has docs disabled)
# We'll build the endpoint list from the route definitions instead
print("=" * 80)
print("BJS-MENU PRODUCTION ENDPOINT TEST")
print(f"Target: {BASE_URL}")
print("=" * 80)

# Try to get OpenAPI spec from local
try:
    resp = requests.get("http://127.0.0.1:8000/openapi.json", timeout=5)
    spec = resp.json()
    paths = spec.get("paths", {})
    print(f"\nLoaded {len(paths)} paths from OpenAPI spec")
except Exception:
    print("\nCouldn't load OpenAPI spec from local, using manual endpoint list")
    paths = None

results = defaultdict(list)
status_counter = Counter()
errors_detail = []
timing_data = []

def replace_path_params(path):
    """Replace path parameters with test values."""
    result = re.sub(r'\{[^}]*_id\}', '1', path)
    result = re.sub(r'\{venue_id\}', '1', result)
    result = re.sub(r'\{id\}', '1', result)
    result = re.sub(r'\{token\}', 'test-token', result)
    result = re.sub(r'\{barcode\}', '1234567890', result)
    result = re.sub(r'\{[^}]+\}', '1', result)
    return result

tested = 0
skipped_methods = {"options", "head", "trace"}

if paths:
    for path in sorted(paths.keys()):
        methods_info = paths[path]
        for method_name in sorted(methods_info.keys()):
            if method_name in skipped_methods:
                continue
            actual_path = replace_path_params(path)
            url = f"{BASE_URL}{actual_path}"

            # Only test GET endpoints against production to be safe
            # POST/PUT/DELETE could modify data
            if method_name != "get":
                # For non-GET, just record as skipped
                results["SKIPPED (write)"].append(f"{method_name.upper()} {path}")
                continue

            try:
                start = time.time()
                r = requests.get(url, headers=HEADERS, timeout=15)
                elapsed = time.time() - start

                status_counter[r.status_code] += 1
                timing_data.append((path, elapsed))

                category = f"{r.status_code}"
                results[category].append(f"GET {path}")

                if r.status_code >= 500:
                    try:
                        detail = r.json().get("detail", r.text[:100])
                    except Exception:
                        detail = r.text[:100]
                    errors_detail.append(f"GET {path} => {r.status_code}: {detail}")

                tested += 1

                # Print progress
                status_icon = "✓" if r.status_code < 400 else "✗" if r.status_code >= 500 else "⚠"
                print(f"  {status_icon} {r.status_code} | {elapsed:.3f}s | GET {actual_path}")

            except requests.exceptions.Timeout:
                results["TIMEOUT"].append(f"GET {path}")
                errors_detail.append(f"GET {path} => TIMEOUT (>15s)")
                print(f"  ⏱ TIMEOUT | GET {actual_path}")
                tested += 1
            except Exception as e:
                results["ERROR"].append(f"GET {path}: {str(e)[:60]}")
                print(f"  ✗ ERROR | GET {actual_path}: {str(e)[:60]}")
                tested += 1

            # Small delay to avoid rate limiting
            time.sleep(0.05)

# Print summary
print("\n" + "=" * 80)
print("RESULTS SUMMARY")
print("=" * 80)

print(f"\nTotal endpoints tested: {tested}")
print(f"Total write endpoints skipped: {len(results.get('SKIPPED (write)', []))}")

print("\n--- Status Code Distribution ---")
for code in sorted(status_counter.keys()):
    count = status_counter[code]
    pct = (count / tested * 100) if tested > 0 else 0
    bar = "█" * int(pct / 2)
    print(f"  HTTP {code}: {count:4d} ({pct:5.1f}%) {bar}")

if timing_data:
    times = [t for _, t in timing_data]
    print(f"\n--- Response Times ---")
    print(f"  Average: {sum(times)/len(times):.3f}s")
    print(f"  Min:     {min(times):.3f}s")
    print(f"  Max:     {max(times):.3f}s")
    print(f"  p95:     {sorted(times)[int(len(times)*0.95)]:.3f}s")

    # Slowest endpoints
    print(f"\n--- Top 10 Slowest Endpoints ---")
    for path, t in sorted(timing_data, key=lambda x: -x[1])[:10]:
        print(f"  {t:.3f}s | GET {path}")

print(f"\n--- Successful (2xx) Endpoints ({status_counter.get(200, 0)}) ---")
for ep in sorted(results.get("200", [])):
    print(f"  ✓ {ep}")

print(f"\n--- Not Found (404) Endpoints ({status_counter.get(404, 0)}) ---")
for ep in sorted(results.get("404", []))[:20]:
    print(f"  ⚠ {ep}")
if len(results.get("404", [])) > 20:
    print(f"  ... and {len(results['404']) - 20} more")

print(f"\n--- Server Errors (5xx) ({sum(v for k, v in status_counter.items() if k >= 500)}) ---")
for err in sorted(errors_detail):
    print(f"  ✗ {err}")

print(f"\n--- Auth Errors (401) ({status_counter.get(401, 0)}) ---")
for ep in sorted(results.get("401", []))[:20]:
    print(f"  🔒 {ep}")
if len(results.get("401", [])) > 20:
    print(f"  ... and {len(results['401']) - 20} more")

print(f"\n--- Validation Errors (422) ({status_counter.get(422, 0)}) ---")
for ep in sorted(results.get("422", []))[:20]:
    print(f"  ⚠ {ep}")
if len(results.get("422", [])) > 20:
    print(f"  ... and {len(results['422']) - 20} more")

other_codes = {k: v for k, v in status_counter.items() if k not in (200, 401, 404, 422, 500)}
if other_codes:
    print(f"\n--- Other Status Codes ---")
    for code, count in sorted(other_codes.items()):
        print(f"  HTTP {code}: {count} endpoints")
        for ep in sorted(results.get(str(code), []))[:5]:
            print(f"    {ep}")

# Write detailed results to file
with open("/opt/bjs-menu/test_production_results.json", "w") as f:
    json.dump({
        "tested": tested,
        "skipped_write": len(results.get("SKIPPED (write)", [])),
        "status_distribution": dict(status_counter),
        "results_by_status": {k: v for k, v in results.items()},
        "errors": errors_detail,
        "timing": {
            "average": sum(times)/len(times) if timing_data else 0,
            "min": min(times) if timing_data else 0,
            "max": max(times) if timing_data else 0,
        }
    }, f, indent=2)

print(f"\nDetailed results saved to /opt/bjs-menu/test_production_results.json")
print("=" * 80)
