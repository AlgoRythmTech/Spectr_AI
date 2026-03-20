#!/usr/bin/env python3
"""
Backend API Testing for ASSOCIATE Legal Platform
Tests all critical endpoints using provided test credentials.
"""

import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class AssociateAPITester:
    def __init__(self, base_url: str, session_token: str, test_user_id: str):
        self.base_url = base_url
        self.session_token = session_token
        self.test_user_id = test_user_id
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {session_token}'
        }

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Dict[Any, Any] = None, auth_required: bool = True) -> tuple:
        """Run a single API test and return success status and response data."""
        url = f"{self.base_url}/api/{endpoint}" if endpoint != "" else f"{self.base_url}/api"
        headers = self.headers if auth_required else {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            # Use longer timeout for AI and library operations
            timeout_duration = 30 if 'assistant' in endpoint or 'library' in endpoint else 15
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout_duration)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout_duration)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout_duration)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                try:
                    response_data = response.json() if response.content else {}
                    if isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                    elif isinstance(response_data, dict):
                        # Show only key fields for readability
                        if 'message' in response_data:
                            print(f"   Message: {response_data['message']}")
                        elif 'user_id' in response_data:
                            print(f"   User: {response_data.get('name', 'N/A')} ({response_data['user_id']})")
                        else:
                            print(f"   Response: {len(response_data)} fields returned")
                    return True, response_data
                except:
                    return True, {"status": "success", "raw_content": response.text[:200]}
            else:
                self.failed_tests.append({
                    'test': name,
                    'expected': expected_status,
                    'actual': response.status_code,
                    'url': url,
                    'response': response.text[:300]
                })
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except requests.exceptions.Timeout:
            timeout_duration = 30 if 'assistant' in endpoint or 'library' in endpoint else 15
            self.failed_tests.append({
                'test': name,
                'error': f'Request timeout ({timeout_duration}s)',
                'url': url
            })
            print(f"❌ FAILED - Request timeout ({timeout_duration}s)")
            return False, {}
        except Exception as e:
            self.failed_tests.append({
                'test': name,
                'error': str(e),
                'url': url
            })
            print(f"❌ FAILED - Error: {str(e)}")
            return False, {}

    def test_basic_endpoints(self):
        """Test basic non-auth endpoints."""
        print("\n" + "="*60)
        print("TESTING BASIC ENDPOINTS")
        print("="*60)
        
        # Test root endpoint
        self.run_test("Root API", "GET", "", 200, auth_required=False)
        
        # Test workflows list (should work without auth)
        self.run_test("List Workflows", "GET", "workflows", 200, auth_required=False)
        
    def test_auth_endpoints(self):
        """Test authentication endpoints."""
        print("\n" + "="*60)
        print("TESTING AUTHENTICATION")
        print("="*60)
        
        # Test /auth/me with valid session
        success, user_data = self.run_test("Get Current User", "GET", "auth/me", 200)
        if success and user_data:
            expected_user_id = self.test_user_id
            actual_user_id = user_data.get('user_id', '')
            if expected_user_id in actual_user_id or actual_user_id in expected_user_id:
                print(f"   ✅ User ID validation passed")
            else:
                print(f"   ⚠️  User ID mismatch - Expected: {expected_user_id}, Got: {actual_user_id}")
        
    def test_statute_search(self):
        """Test statute search functionality."""
        print("\n" + "="*60)
        print("TESTING STATUTE SEARCH")
        print("="*60)
        
        # Test statute search with query
        success, results = self.run_test("Search Statutes - Income", "GET", "statutes?q=income", 200, auth_required=False)
        if success and isinstance(results, list):
            print(f"   Found {len(results)} statute results for 'income'")
        
    def test_matters_crud(self):
        """Test matter creation and listing."""
        print("\n" + "="*60)
        print("TESTING MATTERS MANAGEMENT") 
        print("="*60)
        
        # Create a new matter
        matter_data = {
            "name": f"Test Matter - {datetime.now().strftime('%H%M%S')}",
            "client_name": "Test Client",
            "matter_type": "litigation",
            "description": "Automated test matter"
        }
        
        success, created_matter = self.run_test("Create Matter", "POST", "matters", 200, data=matter_data)
        matter_id = None
        if success and created_matter:
            matter_id = created_matter.get('matter_id')
            print(f"   Created matter ID: {matter_id}")
        
        # List all matters
        success, matters_list = self.run_test("List Matters", "GET", "matters", 200)
        if success and isinstance(matters_list, list):
            print(f"   Found {len(matters_list)} total matters")
            
        return matter_id
    
    def test_assistant_query(self, matter_id=None):
        """Test AI assistant query functionality."""
        print("\n" + "="*60)
        print("TESTING AI ASSISTANT")
        print("="*60)
        
        query_data = {
            "query": "What are the essential elements under Section 138 of the Negotiable Instruments Act?",
            "mode": "partner",
            "matter_id": matter_id or "",
            "language": "english"
        }
        
        print("   🤖 This test may take 10-15 seconds for AI processing...")
        success, response = self.run_test("Assistant Query", "POST", "assistant/query", 200, data=query_data)
        if success and response:
            print(f"   AI Model: {response.get('model_used', 'N/A')}")
            print(f"   Citations: {response.get('citations_count', 0)}")
            print(f"   Response length: {len(response.get('response_text', ''))} chars")
            return response.get('history_id')
        return None
    
    def test_library_operations(self):
        """Test library CRUD operations."""
        print("\n" + "="*60)
        print("TESTING LIBRARY MODULE")
        print("="*60)
        
        # Create library item
        library_item = {
            "title": f"Test Template - {datetime.now().strftime('%H%M%S')}",
            "content": "This is a test template for automated testing.",
            "item_type": "template",
            "tags": ["test", "automation"]
        }
        
        success, created_item = self.run_test("Create Library Item", "POST", "library", 200, data=library_item)
        item_id = None
        if success and created_item:
            item_id = created_item.get('item_id')
            print(f"   Created library item ID: {item_id}")
        
        # List library items
        success, library_list = self.run_test("List Library Items", "GET", "library", 200)
        if success and isinstance(library_list, list):
            print(f"   Found {len(library_list)} library items")
            
        return item_id
    
    def test_history_endpoints(self):
        """Test history retrieval."""
        print("\n" + "="*60)
        print("TESTING HISTORY MODULE")
        print("="*60)
        
        success, history = self.run_test("Get Query History", "GET", "history", 200)
        if success and isinstance(history, list):
            print(f"   Found {len(history)} history entries")
    
    def test_search_endpoints(self):
        """Test external search integrations."""
        print("\n" + "="*60)
        print("TESTING SEARCH INTEGRATIONS")
        print("="*60)
        
        # Test IndianKanoon case search
        self.run_test("Search Cases", "GET", "search/cases?q=cheque bounce", 200)
        
        # Test company search 
        self.run_test("Search Companies", "GET", "search/companies?q=reliance", 200)
    
    def run_comprehensive_test(self):
        """Run all test suites."""
        print(f"\n{'='*80}")
        print(f"ASSOCIATE API TESTING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Backend URL: {self.base_url}")
        print(f"Session Token: {self.session_token[:20]}...")
        print(f"{'='*80}")
        
        # Run test suites in logical order
        self.test_basic_endpoints()
        self.test_auth_endpoints()
        self.test_statute_search()
        
        matter_id = self.test_matters_crud()
        history_id = self.test_assistant_query(matter_id)
        library_item_id = self.test_library_operations()
        
        self.test_history_endpoints()
        self.test_search_endpoints()
        
        # Final summary
        print(f"\n{'='*80}")
        print(f"TEST SUMMARY")
        print(f"{'='*80}")
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {len(self.failed_tests)}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failed_tests:
            print(f"\nFAILED TESTS:")
            for i, failure in enumerate(self.failed_tests, 1):
                print(f"{i}. {failure['test']}")
                if 'expected' in failure:
                    print(f"   Expected: {failure['expected']}, Got: {failure['actual']}")
                if 'error' in failure:
                    print(f"   Error: {failure['error']}")
                if 'response' in failure:
                    print(f"   Response: {failure['response'][:150]}...")
                print()
        
        return len(self.failed_tests) == 0


def main():
    # Configuration from review request
    BACKEND_URL = "https://precedent-hub-1.preview.emergentagent.com"
    SESSION_TOKEN = "test_session_1773997515091"
    TEST_USER_ID = "test-user-1773997515091"
    
    print("ASSOCIATE Legal Platform - Backend API Testing")
    print("=" * 50)
    
    tester = AssociateAPITester(BACKEND_URL, SESSION_TOKEN, TEST_USER_ID)
    
    try:
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\nTesting interrupted by user.")
        return 1
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)