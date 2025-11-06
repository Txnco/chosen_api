"""
Test script for Notification Preferences API endpoints

Prerequisites:
1. Run the SQL migration to add notification_preferences column to users table
2. Ensure the API server is running
3. Have a valid user account and JWT token

Usage:
    python test_notifications_api.py

Or set environment variables:
    export API_BASE_URL=http://localhost:8000
    export JWT_TOKEN=your_jwt_token_here
    python test_notifications_api.py
"""

import os
import sys
import json
import requests
from typing import Dict, Any

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
JWT_TOKEN = os.getenv("JWT_TOKEN", "")

# Test credentials for login (update these with your test account)
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@example.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "password123")


class NotificationAPITester:
    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def login(self, email: str, password: str) -> bool:
        """Login and get JWT token"""
        print(f"\n🔐 Logging in as {email}...")
        url = f"{self.base_url}/auth/login"
        data = {"email": email, "password": password}

        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            result = response.json()
            self.token = result.get("access_token")
            self.headers["Authorization"] = f"Bearer {self.token}"
            print(f"✅ Login successful! Token obtained.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Login failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"   Response: {e.response.text}")
            return False

    def get_preferences(self) -> Dict[str, Any]:
        """Test GET /notifications/preferences"""
        print(f"\n📥 Testing GET /notifications/preferences...")
        url = f"{self.base_url}/notifications/preferences"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            print(f"✅ GET preferences successful!")
            print(f"   Response: {json.dumps(result, indent=2)}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"❌ GET preferences failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            return {}

    def update_preferences(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Test PUT /notifications/preferences"""
        print(f"\n📤 Testing PUT /notifications/preferences...")
        print(f"   Updates: {json.dumps(updates, indent=2)}")
        url = f"{self.base_url}/notifications/preferences"

        try:
            response = requests.put(url, json=updates, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            print(f"✅ PUT preferences successful!")
            print(f"   Response: {json.dumps(result, indent=2)}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"❌ PUT preferences failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            return {}

    def reset_preferences(self) -> Dict[str, Any]:
        """Test POST /notifications/reset"""
        print(f"\n🔄 Testing POST /notifications/reset...")
        url = f"{self.base_url}/notifications/reset"

        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            result = response.json()
            print(f"✅ POST reset successful!")
            print(f"   Response: {json.dumps(result, indent=2)}")
            return result
        except requests.exceptions.RequestException as e:
            print(f"❌ POST reset failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Status: {e.response.status_code}")
                print(f"   Response: {e.response.text}")
            return {}

    def run_all_tests(self):
        """Run all API tests"""
        print("=" * 70)
        print("🧪 NOTIFICATION PREFERENCES API TESTS")
        print("=" * 70)
        print(f"Base URL: {self.base_url}")
        print(f"Token: {'✓ Provided' if self.token else '✗ Not provided'}")

        # Test 1: Get default preferences
        print("\n" + "─" * 70)
        print("TEST 1: Get Current Preferences (should return defaults)")
        print("─" * 70)
        prefs = self.get_preferences()

        # Test 2: Update single notification preference
        print("\n" + "─" * 70)
        print("TEST 2: Update Water Intake Notification")
        print("─" * 70)
        update_data = {
            "water_intake": {
                "enabled": True,
                "interval_hours": 3
            }
        }
        self.update_preferences(update_data)

        # Test 3: Update multiple notification preferences
        print("\n" + "─" * 70)
        print("TEST 3: Update Multiple Notification Preferences")
        print("─" * 70)
        update_data = {
            "daily_planning": {
                "enabled": False,
                "time": "21:00"
            },
            "day_rating": {
                "enabled": True,
                "time": "22:00"
            }
        }
        self.update_preferences(update_data)

        # Test 4: Get updated preferences
        print("\n" + "─" * 70)
        print("TEST 4: Verify Updated Preferences")
        print("─" * 70)
        self.get_preferences()

        # Test 5: Reset to defaults
        print("\n" + "─" * 70)
        print("TEST 5: Reset to Default Preferences")
        print("─" * 70)
        self.reset_preferences()

        # Test 6: Verify reset
        print("\n" + "─" * 70)
        print("TEST 6: Verify Reset to Defaults")
        print("─" * 70)
        self.get_preferences()

        # Test 7: Test invalid time format (should fail validation)
        print("\n" + "─" * 70)
        print("TEST 7: Test Invalid Time Format (Expected to Fail)")
        print("─" * 70)
        invalid_update = {
            "daily_planning": {
                "enabled": True,
                "time": "25:00"  # Invalid time
            }
        }
        self.update_preferences(invalid_update)

        # Test 8: Test invalid day (should fail validation)
        print("\n" + "─" * 70)
        print("TEST 8: Test Invalid Day (Expected to Fail)")
        print("─" * 70)
        invalid_update = {
            "weigh_in": {
                "enabled": True,
                "day": "funday",  # Invalid day
                "time": "08:00"
            }
        }
        self.update_preferences(invalid_update)

        print("\n" + "=" * 70)
        print("✅ ALL TESTS COMPLETED!")
        print("=" * 70)


def main():
    """Main test runner"""
    tester = NotificationAPITester(API_BASE_URL, JWT_TOKEN)

    # If token not provided, try to login
    if not tester.token:
        print("⚠️  No JWT token provided via environment variable.")
        print("Attempting to login with test credentials...")

        if not tester.login(TEST_EMAIL, TEST_PASSWORD):
            print("\n❌ Cannot proceed without authentication.")
            print("\nOptions:")
            print("1. Set JWT_TOKEN environment variable")
            print("2. Update TEST_EMAIL and TEST_PASSWORD in this script")
            print("3. Login via /auth/login endpoint separately")
            sys.exit(1)

    # Run all tests
    tester.run_all_tests()


if __name__ == "__main__":
    main()
