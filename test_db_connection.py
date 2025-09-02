#!/usr/bin/env python3
"""
Test script to verify database connection with Supabase.
Run this script to test if the database connection is properly configured.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import init_database, close_database, AsyncSessionLocal
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_database_connection():
    """Test the database connection and basic operations."""
    
    print("=" * 50)
    print("Testing Supabase Database Connection")
    print("=" * 50)
    
    # Display configuration
    print(f"Database Host: {settings.HOST}")
    print(f"Database Name: {settings.DBNAME}")
    print(f"Database User: {settings.DBUSER}")
    print(f"Database Port: {settings.PORT}")
    print()
    
    try:
        # Initialize database connection
        print("1. Initializing database connection...")
        await init_database()
        print("✅ Database connection initialized successfully!")
        print()
        
        # Test session creation
        print("2. Testing database session...")
        async with AsyncSessionLocal() as session:
            # Test a simple query
            result = await session.execute("SELECT 1 as test_value")
            test_value = result.scalar()
            print(f"✅ Database session test successful! Query result: {test_value}")
        print()
        
        # Test tables exist (optional - since tables are already created in Supabase)
        print("3. Testing table access...")
        async with AsyncSessionLocal() as session:
            try:
                # Try to query the Audio table structure
                result = await session.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN ('Audio', 'Transcriptions')"
                )
                tables = result.fetchall()
                
                if tables:
                    print("✅ Found expected tables:")
                    for table in tables:
                        print(f"   - {table[0]}")
                else:
                    print("⚠️  Expected tables (Audio, Transcriptions) not found.")
                    print("   Make sure the tables are created in your Supabase database.")
                    
            except Exception as e:
                print(f"⚠️  Error checking tables: {e}")
        print()
        
        print("=" * 50)
        print("✅ Database connection test completed successfully!")
        print("Your Supabase connection is properly configured.")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        print()
        print("Troubleshooting tips:")
        print("1. Check your .env file has the correct Supabase credentials")
        print("2. Ensure your Supabase database is running")
        print("3. Verify network connectivity to Supabase")
        print("4. Check if the database user has proper permissions")
        print("=" * 50)
        return False
        
    finally:
        # Close database connection
        try:
            await close_database()
            print("Database connection closed.")
        except Exception as e:
            print(f"Error closing database: {e}")
    
    return True


if __name__ == "__main__":
    # Check if .env file exists
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        print("Please create a .env file with your Supabase credentials.")
        print("See .env.example for the required format.")
        sys.exit(1)
    
    # Run the test
    try:
        success = asyncio.run(test_database_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
