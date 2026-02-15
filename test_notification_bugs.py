#!/usr/bin/env python3
"""
Notification System Bug Testing - اختبار أخطاء نظام الإشعارات
================================================================
اكتشاف المشاكل الفعلية في نظام الإشعارات
"""

import requests
import sqlite3
import json
from datetime import datetime

BASE_URL = "http://localhost:3002/api"
DB_PATH = "/Users/anr/Desktop/trading_ai_bot-1/database/trading_database.db"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

# ==================== Test 1: API Route Verification ====================
def test_notification_routes():
    """اختبار مسارات API للإشعارات"""
    print("\n" + "="*60)
    print("🔍 Test 1: API Routes Verification")
    print("="*60)
    
    routes_to_test = [
        ("GET", "/user/notifications/1"),
        ("PUT", "/user/notifications/1/read"),
        ("POST", "/user/notifications/1/mark-all-read")
    ]
    
    results = {}
    
    for method, route in routes_to_test:
        try:
            url = f"{BASE_URL}{route}"
            response = requests.request(method, url, timeout=5)
            
            if response.status_code == 401:
                log_warning(f"{method} {route} - Authentication required (expected)")
                results[route] = "AUTH_REQUIRED"
            elif response.status_code == 404:
                log_error(f"{method} {route} - Route NOT FOUND")
                results[route] = "NOT_FOUND"
            elif response.status_code in [200, 400, 403]:
                log_success(f"{method} {route} - Route exists")
                results[route] = "EXISTS"
            else:
                log_warning(f"{method} {route} - Status: {response.status_code}")
                results[route] = f"STATUS_{response.status_code}"
                
        except Exception as e:
            log_error(f"{method} {route} - Connection failed: {e}")
            results[route] = "CONNECTION_ERROR"
    
    return results

# ==================== Test 2: Database Schema Verification ====================
def test_database_schema():
    """فحص schema قاعدة البيانات للإشعارات"""
    print("\n" + "="*60)
    print("🔍 Test 2: Database Schema")
    print("="*60)
    
    issues = []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check notification_history table
        cursor.execute("PRAGMA table_info(notification_history)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        log_info(f"notification_history columns: {len(column_names)}")
        
        required_columns = ['id', 'user_id', 'type', 'title', 'message', 'status', 'created_at']
        missing_columns = []
        
        for col in required_columns:
            if col in column_names:
                log_success(f"Column '{col}' exists")
            else:
                missing_columns.append(col)
                log_error(f"Column '{col}' MISSING")
        
        if missing_columns:
            issues.append(f"Missing columns: {missing_columns}")
        
        # Check for is_read column issue
        if 'is_read' not in column_names:
            log_warning("Column 'is_read' missing - using 'status' instead")
            issues.append("No is_read column - using status field")
        
        # Check data format
        cursor.execute("SELECT * FROM notification_history LIMIT 3")
        sample_data = cursor.fetchall()
        
        if sample_data:
            log_success(f"Sample data: {len(sample_data)} records found")
            for i, row in enumerate(sample_data):
                log_info(f"Record {i+1}: ID={row[0]}, Type={row[2] if len(row) > 2 else 'N/A'}")
        else:
            log_warning("No sample data found in notification_history")
            issues.append("No sample data in database")
        
        conn.close()
        
    except Exception as e:
        log_error(f"Database schema check failed: {e}")
        issues.append(f"Database error: {e}")
    
    return issues

# ==================== Test 3: API Response Format ====================
def test_api_response_format():
    """فحص تنسيق استجابة API"""
    print("\n" + "="*60)
    print("🔍 Test 3: API Response Format")
    print("="*60)
    
    issues = []
    
    # Test without authentication (should get proper error format)
    try:
        response = requests.get(f"{BASE_URL}/user/notifications/1", timeout=5)
        
        if response.status_code == 401:
            try:
                data = response.json()
                if 'success' in data and 'error' in data:
                    log_success("Error response format is correct")
                else:
                    log_error("Error response format is incorrect")
                    issues.append("Wrong error response format")
            except json.JSONDecodeError:
                log_error("Response is not valid JSON")
                issues.append("Invalid JSON response")
        else:
            log_warning(f"Expected 401, got {response.status_code}")
            
    except Exception as e:
        log_error(f"API response test failed: {e}")
        issues.append(f"API response error: {e}")
    
    return issues

# ==================== Test 4: Frontend Icon References ====================
def test_frontend_icons():
    """فحص مراجع الأيقونات في Frontend"""
    print("\n" + "="*60)
    print("🔍 Test 4: Frontend Icon References")
    print("="*60)
    
    issues = []
    
    # Check NotificationsScreen.js for icon references
    try:
        with open('/Users/anr/Desktop/trading_ai_bot-1/mobile_app/TradingApp/src/screens/NotificationsScreen.js', 'r') as f:
            content = f.read()
            
        # Check for icon references
        icon_references = [
            'chart-line',
            'alert-triangle',
            'trending-up',
            'trending-down',
            'settings',
            'shield',
            'notification'
        ]
        
        for icon in icon_references:
            if f"'{icon}'" in content or f'"{icon}"' in content:
                log_success(f"Icon reference '{icon}' found in NotificationsScreen")
            else:
                log_warning(f"Icon reference '{icon}' not found")
        
        # Check BrandIcons.js for actual icon definitions
        with open('/Users/anr/Desktop/trading_ai_bot-1/mobile_app/TradingApp/src/components/BrandIcons.js', 'r') as f:
            icons_content = f.read()
        
        missing_icons = []
        for icon in icon_references:
            if f"'{icon}':" in icons_content or f'"{icon}":' in icons_content:
                log_success(f"Icon definition '{icon}' found in BrandIcons")
            else:
                missing_icons.append(icon)
                log_error(f"Icon definition '{icon}' MISSING in BrandIcons")
        
        if missing_icons:
            issues.append(f"Missing icon definitions: {missing_icons}")
            
    except Exception as e:
        log_error(f"Frontend icon check failed: {e}")
        issues.append(f"Frontend check error: {e}")
    
    return issues

# ==================== Main Test Runner ====================
def main():
    print("\n" + "="*60)
    print("🐛 Notification System Bug Detection")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_issues = []
    
    # Test 1: API Routes
    try:
        route_results = test_notification_routes()
        not_found_routes = [route for route, status in route_results.items() if status == "NOT_FOUND"]
        if not_found_routes:
            all_issues.extend([f"Route not found: {route}" for route in not_found_routes])
    except Exception as e:
        all_issues.append(f"Route testing failed: {e}")
    
    # Test 2: Database Schema
    try:
        db_issues = test_database_schema()
        all_issues.extend(db_issues)
    except Exception as e:
        all_issues.append(f"Database testing failed: {e}")
    
    # Test 3: API Response Format
    try:
        api_issues = test_api_response_format()
        all_issues.extend(api_issues)
    except Exception as e:
        all_issues.append(f"API testing failed: {e}")
    
    # Test 4: Frontend Icons
    try:
        icon_issues = test_frontend_icons()
        all_issues.extend(icon_issues)
    except Exception as e:
        all_issues.append(f"Frontend testing failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 Bug Detection Summary")
    print("="*60)
    
    if not all_issues:
        print(f"{Colors.GREEN}✅ No critical issues detected{Colors.END}")
    else:
        print(f"{Colors.RED}❌ {len(all_issues)} issues detected:{Colors.END}")
        for i, issue in enumerate(all_issues, 1):
            print(f"{Colors.RED}  {i}. {issue}{Colors.END}")
    
    print("="*60)

if __name__ == "__main__":
    main()
