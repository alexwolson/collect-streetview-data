#!/usr/bin/env python3
"""
Test script to verify the package installation works.
"""

def test_imports():
    """Test that all modules can be imported."""
    try:
        from toronto_streetview_crawler import load_boundary, get_panorama, crawl
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_functions():
    """Test that key functions are available."""
    try:
        from toronto_streetview_crawler.load_boundary import load_toronto_boundary, get_boundary_centerpoint
        from toronto_streetview_crawler.get_panorama import get_panorama_data, save_panorama_data
        from toronto_streetview_crawler.crawl import init_db, save_panorama_metadata_to_db
        print("✅ All functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Function import failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Toronto StreetView Crawler Package")
    print("=" * 40)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test functions
    if not test_functions():
        success = False
    
    if success:
        print("\n🎉 All tests passed! Package is ready to use.")
        print("\nYou can now run:")
        print("  toronto-boundary    # Load Toronto boundary")
        print("  toronto-panorama    # Get a single panorama")
        print("  toronto-crawl       # Start crawling panoramas")
    else:
        print("\n❌ Some tests failed. Check the installation.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
