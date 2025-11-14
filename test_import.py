# Quick Import Test
# Save as: test_import.py in project root

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("="*60)
print("Testing Imports")
print("="*60)

print("\n1. Testing HandTracker import...")
try:
    from gesture_oak.detection.HandTracker import HandTracker
    print("   ✅ SUCCESS: HandTracker imported")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")

print("\n2. Testing RGBHandDetector import...")
try:
    from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
    print("   ✅ SUCCESS: RGBHandDetector imported")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")

print("\n3. Testing three_area_detector import...")
try:
    from gesture_oak.detection.three_area_detector import ThreeAreaDetector
    print("   ✅ SUCCESS: ThreeAreaDetector imported")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")

print("\n4. Testing three_area_app import...")
try:
    from gesture_oak.apps.three_area_app import main
    print("   ✅ SUCCESS: three_area_app imported")
except ImportError as e:
    print(f"   ❌ FAILED: {e}")

print("\n" + "="*60)
print("If all tests passed, option 6 should work!")
print("="*60)