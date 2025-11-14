"""
Final Verification - Everything Should Work Now!
Run from project root: python final_test.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("="*70)
print("FINAL VERIFICATION TEST")
print("="*70)

# Check model files
print("\n[1] Checking model files...")
models_dir = Path("src/gesture_oak/detection/models")
required_models = [
    "palm_detection_sh4.blob",
    "hand_landmark_lite_sh4.blob"
]

all_models_ok = True
for model in required_models:
    model_path = models_dir / model
    if model_path.exists():
        print(f"✅ {model} - Found ({model_path.stat().st_size:,} bytes)")
    else:
        print(f"❌ {model} - NOT FOUND")
        all_models_ok = False

if not all_models_ok:
    print("\n⚠️  Some models are missing. Cannot proceed.")
    sys.exit(1)

# Test imports
print("\n[2] Testing imports...")
try:
    from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
    print("✅ RGBHandDetector imported successfully")
except Exception as e:
    print(f"❌ Failed to import RGBHandDetector: {e}")
    sys.exit(1)

try:
    from gesture_oak.detection.three_area_detector import ThreeAreaDetector
    print("✅ ThreeAreaDetector imported successfully")
except Exception as e:
    print(f"❌ Failed to import ThreeAreaDetector: {e}")
    sys.exit(1)

try:
    from gesture_oak.apps.three_area_app import main as area_main
    print("✅ three_area_app imported successfully")
except Exception as e:
    print(f"❌ Failed to import three_area_app: {e}")
    sys.exit(1)

# Test creating detector instance
print("\n[3] Testing RGBHandDetector initialization...")
print("    (This will initialize the camera)")
try:
    detector = RGBHandDetector(fps=15, resolution=(640, 480), pd_score_thresh=0.5)
    print("✅ RGBHandDetector instance created successfully!")
    print("    Camera initialized and ready")
    
    # Clean up
    detector.close()
    print("    Detector closed cleanly")
    
except Exception as e:
    print(f"❌ Failed to create detector: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*70)
print("✅ ALL TESTS PASSED!")
print("="*70)
print("\n🎉 Everything is working! You can now:")
print("   1. Run: python main.py")
print("   2. Select option: 6")
print("   3. Enjoy 3-area detection!")
print("\n" + "="*70)
