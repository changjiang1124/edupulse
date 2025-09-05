#!/usr/bin/env python
"""
Test Google Maps API configuration for EduPulse teacher attendance system
"""
import os
import requests
from decimal import Decimal

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

def test_geocoding_api():
    """Test Google Geocoding API"""
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    if not api_key:
        print("❌ GOOGLE_MAPS_API_KEY not found in environment")
        return False
    
    print(f"🔑 Testing Google Maps API Key: {api_key[:20]}...")
    
    # Test address for Perth Art School
    test_address = "Perth, Western Australia, Australia"
    
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {
        'address': test_address,
        'key': api_key
    }
    
    try:
        print(f"🌐 Testing Geocoding API with address: {test_address}")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"📡 API Response Status: {data.get('status')}")
        
        if data['status'] == 'OK' and data['results']:
            location = data['results'][0]['geometry']['location']
            lat, lng = location['lat'], location['lng']
            formatted_address = data['results'][0]['formatted_address']
            
            print(f"✅ Geocoding API Test PASSED")
            print(f"   📍 Address: {formatted_address}")
            print(f"   🗺️  Coordinates: {lat}, {lng}")
            return True
        
        elif data['status'] == 'REQUEST_DENIED':
            print(f"❌ Geocoding API Test FAILED: Request Denied")
            print(f"   🔒 Check API key restrictions and billing")
            return False
            
        else:
            print(f"❌ Geocoding API Test FAILED: {data.get('status')}")
            print(f"   ℹ️  Error: {data.get('error_message', 'Unknown error')}")
            return False
            
    except requests.RequestException as e:
        print(f"❌ Network Error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return False

def test_distance_calculation():
    """Test GPS distance calculation function"""
    print("\n🧮 Testing GPS Distance Calculation...")
    
    try:
        # Import our GPS utilities
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edupulse.settings')
        django.setup()
        
        from core.utils.gps_utils import haversine_distance
        
        # Test coordinates: Perth CBD to Fremantle
        perth_lat, perth_lng = -31.9505, 115.8605
        fremantle_lat, fremantle_lng = -32.0569, 115.7475
        
        distance = haversine_distance(perth_lat, perth_lng, fremantle_lat, fremantle_lng)
        
        print(f"✅ Distance Calculation Test PASSED")
        print(f"   📏 Perth CBD to Fremantle: {distance:.1f} meters ({distance/1000:.1f} km)")
        
        # Test with close coordinates (should be within attendance radius)
        close_distance = haversine_distance(perth_lat, perth_lng, perth_lat + 0.001, perth_lng + 0.001)
        print(f"   📏 Close proximity test: {close_distance:.1f} meters")
        
        return True
        
    except Exception as e:
        print(f"❌ Distance Calculation Test FAILED: {str(e)}")
        return False

def test_places_api():
    """Test Google Places API (optional)"""
    places_key = os.getenv('GOOGLE_PLACES_API_KEY')
    if not places_key:
        print("\n⚠️  GOOGLE_PLACES_API_KEY not configured (optional)")
        return None
    
    print(f"\n🏢 Testing Google Places API Key: {places_key[:20]}...")
    
    # Simple Places API test
    url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
    params = {
        'input': 'Perth Art School',
        'inputtype': 'textquery',
        'fields': 'place_id,name,geometry',
        'key': places_key
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('status') == 'OK':
            print(f"✅ Places API Test PASSED")
            if data.get('candidates'):
                candidate = data['candidates'][0]
                print(f"   🏢 Found: {candidate.get('name', 'Unknown')}")
            return True
        else:
            print(f"⚠️  Places API Test FAILED: {data.get('status')}")
            return False
            
    except Exception as e:
        print(f"⚠️  Places API Error: {str(e)}")
        return False

def main():
    """Run all API tests"""
    print("🧪 EduPulse Google Maps API Configuration Test")
    print("=" * 50)
    
    results = []
    
    # Test Geocoding API (required)
    results.append(test_geocoding_api())
    
    # Test distance calculation (required)
    results.append(test_distance_calculation())
    
    # Test Places API (optional)
    places_result = test_places_api()
    if places_result is not None:
        results.append(places_result)
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    
    passed = sum(1 for r in results if r is True)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests PASSED ({passed}/{total})")
        print("🚀 Teacher attendance system is ready to use!")
    else:
        failed = total - passed
        print(f"⚠️  {failed} test(s) FAILED ({passed}/{total} passed)")
        print("🔧 Please check API configuration and try again")
    
    return passed == total

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)