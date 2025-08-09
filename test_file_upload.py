#!/usr/bin/env python3
"""
Test script for the file upload PR review API
"""

import requests
import tempfile
import os

SAMPLE_PR_DIFF = """--- a/src/main.py
+++ b/src/main.py
@@ -10,7 +10,7 @@
 def main():
-    print("old code")
+    print("new code")
+    validate_input()
     return True

--- a/src/utils.py
+++ b/src/utils.py
@@ -5,6 +5,8 @@
 def helper():
+    # Added new functionality
+    validate_input()
     return process_data()
"""

SAMPLE_CODEBASE = """=== FILE: src/main.py ===
import utils
from config import settings

def main():
    print("new code")
    validate_input()
    return True

def validate_input():
    pass

=== FILE: src/utils.py ===
def helper():
    validate_input()
    return process_data()

def process_data():
    return "processed"

=== FILE: src/config.py ===
settings = {
    "debug": True,
    "version": "1.0.0"
}
"""

def test_file_upload_api():
    """Test the file upload API endpoint"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as diff_file:
        diff_file.write(SAMPLE_PR_DIFF)
        diff_file_path = diff_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as codebase_file:
        codebase_file.write(SAMPLE_CODEBASE)
        codebase_file_path = codebase_file.name
    
    try:
        files = {
            'pr_diff_file': open(diff_file_path, 'rb'),
            'codebase_file': open(codebase_file_path, 'rb')
        }
        data = {'analysis_scope': 'full'}
        
        print("Testing file upload API...")
        response = requests.post('http://localhost:8080/review/pr/files/', files=files, data=data)
        
        if response.status_code == 200:
            print("✅ API call successful!")
            result = response.json()
            print(f"Files analyzed: {result['summary']['total_files_changed']}")
            print(f"Total changes: {result['summary']['total_lines_changed']}")
            print(f"Analysis scope: {result['summary']['analysis_scope']}")
            print(f"Has codebase context: {result['summary']['has_codebase_context']}")
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(response.text)
            
        for file in files.values():
            file.close()
            
    finally:
        os.unlink(diff_file_path)
        os.unlink(codebase_file_path)

def test_diff_only():
    """Test with PR diff only"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.diff', delete=False) as diff_file:
        diff_file.write(SAMPLE_PR_DIFF)
        diff_file_path = diff_file.name
    
    try:
        files = {'pr_diff_file': open(diff_file_path, 'rb')}
        data = {'analysis_scope': 'diff_only'}
        
        print("\nTesting diff-only analysis...")
        response = requests.post('http://localhost:8080/review/pr/files/', files=files, data=data)
        
        if response.status_code == 200:
            print("✅ Diff-only analysis successful!")
            result = response.json()
            print(f"Files analyzed: {result['summary']['total_files_changed']}")
        else:
            print(f"❌ Diff-only analysis failed: {response.status_code}")
            
        files['pr_diff_file'].close()
        
    finally:
        os.unlink(diff_file_path)

if __name__ == "__main__":
    print("PR Review File Upload API Test")
    print("=" * 40)
    print("Make sure the FastAPI server is running on localhost:8080")
    print("Start with: python autonomous_agent/pr_review_autonomous.py")
    print()
    
    try:
        test_file_upload_api()
        test_diff_only()
        print("\n✅ All tests completed!")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on localhost:8080")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
