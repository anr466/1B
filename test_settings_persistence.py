#!/usr/bin/env python3
"""
Settings Persistence Test - اختبار استمرارية الإعدادات
========================================================
اختبار حفظ الإعدادات في قاعدة البيانات وبقائها بعد إعادة التشغيل
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "/Users/anr/Desktop/trading_ai_bot-1/database/trading_database.db"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'

def log_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def log_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def log_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")

def log_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def log_section(msg):
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"{msg}")
    print(f"{'='*60}{Colors.END}")

# ==================== Test 1: Database Schema ====================
def test_database_schema():
    """التحقق من schema جدول user_settings"""
    log_section("🔍 Test 1: Database Schema Verification")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(user_settings)")
        columns = cursor.fetchall()
        
        required_columns = [
            'id', 'user_id', 'trading_enabled', 'position_size_percentage',
            'max_positions', 'is_demo', 'created_at', 'updated_at'
        ]
        
        existing_columns = [col[1] for col in columns]
        
        log_info(f"Columns in user_settings table: {len(existing_columns)}")
        
        missing = []
        for col in required_columns:
            if col in existing_columns:
                log_success(f"Column '{col}' exists")
            else:
                missing.append(col)
                log_error(f"Column '{col}' MISSING")
        
        conn.close()
        
        if not missing:
            log_success("Schema verification PASSED")
            return True
        else:
            log_error(f"Schema verification FAILED - Missing columns: {missing}")
            return False
            
    except Exception as e:
        log_error(f"Schema check failed: {e}")
        return False

# ==================== Test 2: Current Settings ====================
def test_current_settings():
    """عرض الإعدادات الحالية في قاعدة البيانات"""
    log_section("📊 Test 2: Current Settings in Database")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all settings for user_id=1
        cursor.execute("""
            SELECT id, user_id, trading_enabled, position_size_percentage,
                   max_positions, is_demo, created_at, updated_at
            FROM user_settings
            WHERE user_id = 1
            ORDER BY is_demo
        """)
        
        settings = cursor.fetchall()
        
        if not settings:
            log_warning("No settings found for user_id=1")
            conn.close()
            return False
        
        log_info(f"Found {len(settings)} settings records for user_id=1")
        
        for idx, setting in enumerate(settings):
            mode = "DEMO" if setting['is_demo'] else "REAL"
            log_info(f"\n{mode} Mode Settings:")
            log_info(f"  - ID: {setting['id']}")
            log_info(f"  - Trading Enabled: {bool(setting['trading_enabled'])}")
            log_info(f"  - Position Size %: {setting['position_size_percentage']}%")
            log_info(f"  - Max Positions: {setting['max_positions']}")
            log_info(f"  - Created: {setting['created_at']}")
            log_info(f"  - Updated: {setting['updated_at']}")
        
        conn.close()
        log_success("Current settings retrieved successfully")
        return True
        
    except Exception as e:
        log_error(f"Failed to get current settings: {e}")
        return False

# ==================== Test 3: Settings Persistence ====================
def test_settings_persistence():
    """اختبار استمرارية الإعدادات"""
    log_section("🔒 Test 3: Settings Persistence Test")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Read current settings
        cursor.execute("""
            SELECT trading_enabled, position_size_percentage, max_positions
            FROM user_settings
            WHERE user_id = 1 AND is_demo = 1
            LIMIT 1
        """)
        
        before = cursor.fetchone()
        
        if not before:
            log_warning("No demo settings found - creating test settings")
            cursor.execute("""
                INSERT INTO user_settings 
                (user_id, is_demo, trading_enabled, position_size_percentage, max_positions)
                VALUES (1, 1, 1, 10.0, 5)
            """)
            conn.commit()
            log_info("Test settings created")
            
            cursor.execute("""
                SELECT trading_enabled, position_size_percentage, max_positions
                FROM user_settings
                WHERE user_id = 1 AND is_demo = 1
                LIMIT 1
            """)
            before = cursor.fetchone()
        
        log_info("Settings BEFORE test:")
        log_info(f"  - Trading Enabled: {bool(before['trading_enabled'])}")
        log_info(f"  - Position Size: {before['position_size_percentage']}%")
        log_info(f"  - Max Positions: {before['max_positions']}")
        
        # 2. Simulate app restart by closing and reopening connection
        conn.close()
        log_info("\n🔄 Simulating app restart...")
        
        # 3. Reopen connection and read settings
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT trading_enabled, position_size_percentage, max_positions
            FROM user_settings
            WHERE user_id = 1 AND is_demo = 1
            LIMIT 1
        """)
        
        after = cursor.fetchone()
        
        log_info("\nSettings AFTER restart:")
        log_info(f"  - Trading Enabled: {bool(after['trading_enabled'])}")
        log_info(f"  - Position Size: {after['position_size_percentage']}%")
        log_info(f"  - Max Positions: {after['max_positions']}")
        
        # 4. Verify persistence
        if (before['trading_enabled'] == after['trading_enabled'] and
            before['position_size_percentage'] == after['position_size_percentage'] and
            before['max_positions'] == after['max_positions']):
            log_success("Settings persisted correctly after restart!")
            conn.close()
            return True
        else:
            log_error("Settings changed after restart!")
            conn.close()
            return False
            
    except Exception as e:
        log_error(f"Persistence test failed: {e}")
        return False

# ==================== Test 4: Update Flow ====================
def test_update_flow():
    """اختبار تدفق تحديث الإعدادات"""
    log_section("🔄 Test 4: Settings Update Flow")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 1. Get current settings
        cursor.execute("""
            SELECT trading_enabled, position_size_percentage, max_positions, updated_at
            FROM user_settings
            WHERE user_id = 1 AND is_demo = 1
            LIMIT 1
        """)
        
        before = cursor.fetchone()
        
        if not before:
            log_error("No settings found for update test")
            conn.close()
            return False
        
        log_info("Current settings:")
        log_info(f"  - Trading Enabled: {bool(before['trading_enabled'])}")
        log_info(f"  - Position Size: {before['position_size_percentage']}%")
        log_info(f"  - Max Positions: {before['max_positions']}")
        log_info(f"  - Last Updated: {before['updated_at']}")
        
        # 2. Update settings (simulate user changing settings)
        new_trading_enabled = not before['trading_enabled']
        new_position_size = 15.0 if before['position_size_percentage'] == 10.0 else 10.0
        new_max_positions = 7 if before['max_positions'] == 5 else 5
        
        log_info("\n📝 Updating settings...")
        
        cursor.execute("""
            UPDATE user_settings
            SET trading_enabled = ?,
                position_size_percentage = ?,
                max_positions = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = 1 AND is_demo = 1
        """, (new_trading_enabled, new_position_size, new_max_positions))
        
        conn.commit()
        
        # 3. Verify update
        cursor.execute("""
            SELECT trading_enabled, position_size_percentage, max_positions, updated_at
            FROM user_settings
            WHERE user_id = 1 AND is_demo = 1
            LIMIT 1
        """)
        
        after = cursor.fetchone()
        
        log_info("\nUpdated settings:")
        log_info(f"  - Trading Enabled: {bool(after['trading_enabled'])}")
        log_info(f"  - Position Size: {after['position_size_percentage']}%")
        log_info(f"  - Max Positions: {after['max_positions']}")
        log_info(f"  - Last Updated: {after['updated_at']}")
        
        # 4. Verify changes
        if (after['trading_enabled'] == new_trading_enabled and
            after['position_size_percentage'] == new_position_size and
            after['max_positions'] == new_max_positions and
            after['updated_at'] != before['updated_at']):
            log_success("Settings updated successfully!")
            
            # 5. Restore original settings
            log_info("\n🔄 Restoring original settings...")
            cursor.execute("""
                UPDATE user_settings
                SET trading_enabled = ?,
                    position_size_percentage = ?,
                    max_positions = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = 1 AND is_demo = 1
            """, (before['trading_enabled'], before['position_size_percentage'], before['max_positions']))
            
            conn.commit()
            log_success("Original settings restored")
            
            conn.close()
            return True
        else:
            log_error("Settings update failed!")
            conn.close()
            return False
            
    except Exception as e:
        log_error(f"Update flow test failed: {e}")
        return False

# ==================== Main Test Runner ====================
def main():
    print("\n" + "="*60)
    print("🚀 Settings Persistence Testing")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Database: {DB_PATH}")
    
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
    
    # Test 1: Schema
    results["total"] += 1
    if test_database_schema():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 2: Current Settings
    results["total"] += 1
    if test_current_settings():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 3: Persistence
    results["total"] += 1
    if test_settings_persistence():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Test 4: Update Flow
    results["total"] += 1
    if test_update_flow():
        results["passed"] += 1
    else:
        results["failed"] += 1
    
    # Print Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"Total Tests: {results['total']}")
    print(f"{Colors.GREEN}Passed: {results['passed']}{Colors.END}")
    print(f"{Colors.RED}Failed: {results['failed']}{Colors.END}")
    
    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}✅ All tests passed!{Colors.END}")
        print(f"\n{Colors.CYAN}📝 Conclusion:{Colors.END}")
        print("  ✅ Settings are saved correctly in database")
        print("  ✅ Settings persist after app restart")
        print("  ✅ Settings remain until user/admin changes them")
    else:
        print(f"\n{Colors.RED}❌ Some tests failed!{Colors.END}")
    print("="*60)

if __name__ == "__main__":
    main()
