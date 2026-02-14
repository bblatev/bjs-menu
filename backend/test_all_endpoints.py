"""Comprehensive endpoint tester for BJS Menu API."""
import json, sys, re, requests
from collections import defaultdict

BASE_URL = "http://127.0.0.1:8001"
sys.path.insert(0, "/opt/bjs-menu/backend")
from app.core.security import create_access_token
TOKEN = create_access_token(data={"sub": "1", "email": "admin@bjs.bar", "role": "owner"})
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

resp = requests.get(f"{BASE_URL}/openapi.json")
spec = resp.json()
paths = spec.get("paths", {})

results = defaultdict(list)
errors_detail = []

def get_test_body(path, method):
    if method in ("get", "delete"):
        return None
    return {"name": "Test", "description": "Test", "price": 10.0, "quantity": 1}

def replace_path_params(path):
    result = re.sub(r'\{[^}]+_id\}', '1', path)
    result = re.sub(r'\{venue_id\}', '1', result)
    result = re.sub(r'\{id\}', '1', result)
    result = re.sub(r'\{token\}', 'test-token', result)
    result = re.sub(r'\{[^}]+\}', '1', result)
    return result

tested = 0
total_500 = 0

for path in sorted(paths.keys()):
    methods_info = paths[path]
    for method_name in sorted(methods_info.keys()):
        if method_name not in ("get", "post", "put", "patch", "delete"):
            continue
        actual_path = replace_path_params(path)
        url = f"{BASE_URL}{actual_path}"
        try:
            body = get_test_body(path, method_name)
            if method_name == "get":
                r = requests.get(url, headers=HEADERS, timeout=10)
            elif method_name == "post":
                r = requests.post(url, headers=HEADERS, json=body, timeout=10)
            elif method_name == "put":
                r = requests.put(url, headers=HEADERS, json=body, timeout=10)
            elif method_name == "patch":
                r = requests.patch(url, headers=HEADERS, json=body, timeout=10)
            elif method_name == "delete":
                r = requests.delete(url, headers=HEADERS, timeout=10)
            status = r.status_code
            tested += 1
            if status == 500:
                total_500 += 1
                try:
                    detail = r.json().get("detail", r.text[:200])
                except Exception:
                    detail = r.text[:200]
                errors_detail.append({"method": method_name.upper(), "path": path, "status": 500, "detail": str(detail)[:300]})
                print(f"500: {method_name.upper()} {path} -> {str(detail)[:120]}")
            results[status].append(f"{method_name.upper()} {path}")
        except requests.exceptions.Timeout:
            errors_detail.append({"method": method_name.upper(), "path": path, "status": "TIMEOUT", "detail": "timeout"})
            print(f"TIMEOUT: {method_name.upper()} {path}")
        except Exception as e:
            errors_detail.append({"method": method_name.upper(), "path": path, "status": "EXCEPTION", "detail": str(e)[:200]})

print(f"\n{'='*80}")
print(f"Total tested: {tested}")
print(f"500 errors: {total_500}")
print("Status distribution:")
for k in sorted(results.keys()):
    print(f"  {k}: {len(results[k])}")

with open("/tmp/endpoint_test_results.json", "w") as f:
    json.dump({"total_tested": tested, "total_500": total_500, "errors": errors_detail, "status_dist": {str(k): len(v) for k,v in results.items()}, "all_500_paths": [e["path"] for e in errors_detail if e["status"]==500]}, f, indent=2)
print(f"\nResults saved to /tmp/endpoint_test_results.json")
