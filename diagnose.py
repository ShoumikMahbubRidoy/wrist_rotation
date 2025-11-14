"""
Simple diagnostic to find the ghost import error
Save as: diagnose.py in project root
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("="*70)
print("DIAGNOSTIC: Finding the Import Ghost")
print("="*70)

# Test 1: Check if HandTracker.py exists and can be read
print("\n[Test 1] Checking HandTracker.py file...")
tracker_path = Path("src/gesture_oak/detection/HandTracker.py")
if tracker_path.exists():
    print(f"✅ File exists: {tracker_path.absolute()}")
    print(f"   Size: {tracker_path.stat().st_size} bytes")
else:
    print(f"❌ File NOT found: {tracker_path.absolute()}")

# Test 2: Check rgb_hand_detector.py
print("\n[Test 2] Checking rgb_hand_detector.py content...")
rgb_path = Path("src/gesture_oak/detection/rgb_hand_detector.py")
if rgb_path.exists():
    print(f"✅ File exists: {rgb_path.absolute()}")
    with open(rgb_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the correct import
    if "from .HandTracker import HandTracker" in content:
        print("✅ Has correct relative import: 'from .HandTracker import HandTracker'")
    elif "from HandTracker import HandTracker" in content:
        print("⚠️  Has OLD import: 'from HandTracker import HandTracker'")
        print("   This needs to be changed to: 'from .HandTracker import HandTracker'")
    else:
        print("❓ Import statement not found in expected format")
        
    # Show the actual import lines
    print("\n   Import lines found:")
    for i, line in enumerate(content.split('\n')[:50], 1):
        if 'HandTracker' in line and 'import' in line:
            print(f"   Line {i}: {line.strip()}")
else:
    print(f"❌ File NOT found: {rgb_path.absolute()}")

# Test 3: Try the actual imports
print("\n[Test 3] Trying actual imports...")
print("\n3a. Importing HandTracker directly...")
try:
    from gesture_oak.detection.HandTracker import HandTracker
    print("✅ SUCCESS: HandTracker imported")
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}")

print("\n3b. Importing RGBHandDetector...")
try:
    from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
    print("✅ SUCCESS: RGBHandDetector imported")
    
    # Try to create an instance
    print("\n3c. Creating RGBHandDetector instance...")
    try:
        detector = RGBHandDetector(fps=15, resolution=(640, 480), pd_score_thresh=0.5)
        print("✅ SUCCESS: Instance created!")
        print("   This means everything should work!")
    except Exception as e:
        print(f"❌ FAILED at creation: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ FAILED: {type(e).__name__}: {e}")
    print("\nFull error traceback:")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("Diagnosis Complete")
print("="*70)
