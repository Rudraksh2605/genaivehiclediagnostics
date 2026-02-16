import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_validate():
    print("\n[TEST] /codegen/validate (Auto-Execution)...")
    payload = {
        "requirement": "Write a Python function 'add(a, b)' that returns the sum of a and b.",
        "language": "python"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/codegen/validate", json=payload, timeout=60)
        if response.status_code == 200:
            data = response.json()
            passed = data["test_execution"]["passed"]
            total = data["test_execution"]["total_tests"]
            success = data["test_execution"]["success"]
            
            print(f"  Code Lines: {data['source_code']['lines']}")
            print(f"  Test Lines: {data['test_code']['lines']}")
            print(f"  Execution: {passed}/{total} passed (Success={success})")
            
            if success and passed > 0:
                print("  [PASS] Validation pipeline working")
            else:
                print("  [FAIL] Tests failed or none ran")
                print(json.dumps(data["test_execution"], indent=2))
        else:
            print(f"  [FAIL] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")


def test_build():
    print("\n[TEST] /codegen/build (Iterative Build)...")
    payload = {
        "code": "import os\ndef my_func():\n    return os.getcwd()",
        "language": "python"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/codegen/build", json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            success = data["build_success"]
            lang = data["language"]
            
            print(f"  Language: {lang}")
            print(f"  Build Success: {success}")
            print(f"  Details: {data.get('details', {})}")
            
            if success:
                print("  [PASS] Build pipeline working")
            else:
                print("  [FAIL] Build validation failed")
        else:
            print(f"  [FAIL] HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"  [FAIL] Exception: {e}")

if __name__ == "__main__":
    test_validate()
    test_build()
