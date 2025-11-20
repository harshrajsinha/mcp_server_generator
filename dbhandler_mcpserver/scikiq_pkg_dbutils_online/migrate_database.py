#!/usr/bin/env python3
"""
Database Migration Script for SciKiq MCP Server

This script adds the missing 'state' and 'is_used' columns to the authorization_codes table.
Run this on your production server before deploying the updated code.
"""

import sqlite3
import sys
import os

def migrate_database(db_path="mcp_auth.db"):
    """Add missing columns to authorization_codes table"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database file '{db_path}' not found!")
        return False
    
    print(f"🔧 Migrating database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(authorization_codes)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        changes_made = False
        
        # Add state column if missing
        if 'state' not in columns:
            cursor.execute("ALTER TABLE authorization_codes ADD COLUMN state TEXT")
            print("✅ Added 'state' column")
            changes_made = True
        else:
            print("ℹ️  'state' column already exists")
        
        # Add is_used column if missing
        if 'is_used' not in columns:
            cursor.execute("ALTER TABLE authorization_codes ADD COLUMN is_used BOOLEAN DEFAULT FALSE")
            print("✅ Added 'is_used' column")
            changes_made = True
        else:
            print("ℹ️  'is_used' column already exists")
        
        if changes_made:
            conn.commit()
            print("✅ Database migration completed successfully!")
        else:
            print("ℹ️  No migration needed - database is up to date")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(authorization_codes)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Updated columns: {updated_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    # Allow custom database path as command line argument
    db_path = sys.argv[1] if len(sys.argv) > 1 else "mcp_auth.db"
    
    print("🚀 SciKiq MCP Server Database Migration")
    print("=" * 50)
    
    success = migrate_database(db_path)
    
    if success:
        print("\n🎉 Migration completed! You can now deploy the updated server.")
        sys.exit(0)
    else:
        print("\n💥 Migration failed! Please check the error above.")
        sys.exit(1)