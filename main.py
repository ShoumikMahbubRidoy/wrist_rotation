#!/usr/bin/env python3
"""
TG_25_GestureOAK-D Main Menu
Updated with RGB 3-Area Detection
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def print_menu():
    """Display main menu"""
    print("\n" + "="*60)
    print("TG_25_GestureOAK-D - Main Menu")
    print("="*60)
    print("1. Test camera connection")
    print("2. Run hand tracking app (with swipe)")
    print("3. Run swipe detection app")
    print("4. Run motion-based swipe")
    print("5. Run wrist rotation detection")
    print("6. Run 3-area detection (NEW - RGB)")
    print("7. Exit")
    print("="*60)


def main():
    """Main menu loop"""
    while True:
        print_menu()
        choice = input("Enter your choice (1-7): ").strip()
        
        if choice == '1':
            # Test camera
            print("\nTesting camera connection...")
            from gesture_oak.core.oak_camera import test_camera_connection
            test_camera_connection()
        
        elif choice == '2':
            # Hand tracking with swipe
            print("\nStarting hand tracking application...")
            from gesture_oak.apps.hand_tracking_app import main as hand_main
            hand_main()
        
        elif choice == '3':
            # Swipe detection only
            print("\nStarting swipe detection application...")
            from gesture_oak.apps.swipe_detection_app import main as swipe_main
            swipe_main()
        
        elif choice == '4':
            # Motion-based swipe
            print("\nStarting motion-based swipe application...")
            from gesture_oak.apps.motion_swipe_app import main as motion_main
            motion_main()
        
        elif choice == '5':
            # Wrist rotation detection
            print("\nStarting wrist rotation detection...")
            from gesture_oak.apps.wrist_rotation_app import main as rotation_main
            rotation_main()
        
        elif choice == '6':
            # 3-area detection (NEW)
            print("\nStarting 3-area detection (RGB mode)...")
            try:
                from gesture_oak.apps.three_area_app import main as area_main
                area_main()
            except ImportError as e:
                print(f"\n❌ Error: Could not import three_area_app")
                print(f"Details: {e}")
                print("\nMake sure you have:")
                print("  1. Copied three_area_app.py to src/gesture_oak/apps/")
                print("  2. Copied rgb_hand_detector.py to src/gesture_oak/detection/")
                print("  3. Copied three_area_detector.py to src/gesture_oak/detection/")
                print("\nRefer to INTEGRATION_SUMMARY.md for setup instructions.")
        
        elif choice == '7':
            # Exit
            print("\nExiting...")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-7.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()