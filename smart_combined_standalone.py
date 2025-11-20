#!/usr/bin/env python3
"""
Smart Combined Detection - Standalone Launcher (FINAL FIX)
Properly handles model file locations for PyInstaller
"""
import sys
import os
from pathlib import Path
import shutil

# Get paths
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = Path(sys._MEIPASS)  # Temp extraction folder
    exe_dir = Path(sys.executable).parent  # Where EXE is located
else:
    # Running as script
    application_path = Path(__file__).parent
    exe_dir = application_path

# Set up model paths BEFORE importing anything
# Priority: 1. Next to EXE, 2. In bundle, 3. In detection folder
models_locations = [
    exe_dir / "models",                          # Next to EXE (BEST)
    application_path / "models",                 # Inside bundle
    application_path / "gesture_oak" / "detection" / "models",  # In detection
]

# Find models
models_source = None
for loc in models_locations:
    if loc.exists() and (loc / "palm_detection_sh4.blob").exists():
        models_source = loc
        print(f"✓ Found models at: {loc}")
        break

if models_source is None:
    print("\n❌ ERROR: Model files not found!")
    print("Searched in:")
    for loc in models_locations:
        print(f"  - {loc}")
    print("\nMake sure models folder is next to the EXE:")
    print(f"  {exe_dir / 'models'}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# Copy models to detection folder if needed (for HandTracker)
detection_models = application_path / "gesture_oak" / "detection" / "models"
temp_models = Path(os.environ.get('TEMP', '/tmp')) / "models"

# Copy to both locations
for target_dir in [detection_models, temp_models]:
    if not target_dir.exists() or not (target_dir / "palm_detection_sh4.blob").exists():
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for blob_file in models_source.glob("*.blob"):
                target_file = target_dir / blob_file.name
                if not target_file.exists():
                    shutil.copy2(blob_file, target_file)
            print(f"✓ Copied models to: {target_dir}")
        except Exception as e:
            print(f"⚠ Could not copy models to {target_dir}: {e}")

# Add paths
sys.path.insert(0, str(application_path))
sys.path.insert(0, str(application_path / "gesture_oak"))

# Now import
import cv2
import numpy as np

try:
    from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
    from gesture_oak.detection.smart_combined_detector import (
        SmartCombinedDetector, DetectionMode, GestureType
    )
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Application path: {application_path}")
    print(f"EXE directory: {exe_dir}")
    input("\nPress Enter to exit...")
    sys.exit(1)

# Landmarks
WRIST, INDEX_TIP = 0, 8


def draw_hand_skeleton(img, hand):
    """Draw hand skeleton"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    lm = hand.landmarks
    connections = [
        (0,1),(1,2),(2,3),(3,4), (0,5),(5,6),(6,7),(7,8),
        (0,9),(9,10),(10,11),(11,12), (0,13),(13,14),(14,15),(15,16),
        (0,17),(17,18),(18,19),(19,20), (5,9),(9,13),(13,17)
    ]
    
    for a, b in connections:
        cv2.line(img, tuple(lm[a].astype(int)), tuple(lm[b].astype(int)), (0, 255, 0), 2)
    
    for i, pt in enumerate(lm):
        r = 6 if i in [0, 4, 8, 12, 16, 20] else 4
        col = (0, 0, 255) if i in [0, 4, 8, 12, 16, 20] else (255, 255, 255)
        cv2.circle(img, tuple(pt.astype(int)), r, col, -1)


def draw_wrist_rotation_zones(img, wrist_pt, angle, current_position):
    """Draw 4-position wrist rotation zones"""
    cx, cy = int(wrist_pt[0]), int(wrist_pt[1])
    radius = 200
    boundaries = [0, 60, 90, 120, 180]
    zone_colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (255, 128, 0), 4: (0, 0, 255)}
    
    def angle_to_point(angle_deg):
        screen_angle = 180.0 - angle_deg
        rad = np.radians(screen_angle)
        return (cx + int(radius * np.cos(rad)), cy - int(radius * np.sin(rad)))
    
    for zone_num in range(1, 5):
        start_angle, end_angle = boundaries[zone_num - 1], boundaries[zone_num]
        color = zone_colors[zone_num]
        
        if zone_num == current_position:
            overlay = img.copy()
            pts = [np.array([cx, cy])]
            for a in range(int(start_angle), int(end_angle) + 1, 5):
                pts.append(np.array(angle_to_point(a)))
            cv2.fillPoly(overlay, [np.array(pts, dtype=np.int32)], color)
            cv2.addWeighted(overlay, 0.3, img, 0.7, 0, img)
        
        cv2.line(img, (cx, cy), angle_to_point(start_angle), (200, 200, 200), 2)
        cv2.line(img, (cx, cy), angle_to_point(end_angle), (200, 200, 200), 2)
        cv2.ellipse(img, (cx, cy), (radius, radius), 0, -int(end_angle), -int(start_angle), (200, 200, 200), 2)
        
        mid_angle = (start_angle + end_angle) / 2
        label_pt = angle_to_point(mid_angle)
        label_pt = (int(label_pt[0] * 0.6 + cx * 0.4), int(label_pt[1] * 0.6 + cy * 0.4))
        cv2.putText(img, str(zone_num), label_pt, cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3)
    
    if angle is not None:
        angle_pt = angle_to_point(angle)
        cv2.line(img, (cx, cy), angle_pt, (255, 255, 255), 3)
        cv2.circle(img, angle_pt, 8, (0, 255, 0), -1)
    
    cv2.circle(img, (cx, cy), 8, (255, 255, 255), -1)
    cv2.circle(img, (cx, cy), 10, (0, 0, 0), 2)


def draw_three_area_zones(img, index_tip, current_area):
    """Draw 3 vertical area zones"""
    h, w = img.shape[:2]
    area_width = w // 3
    area_colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (0, 0, 255)}
    
    for area_num in range(1, 4):
        x1, x2 = (area_num - 1) * area_width, area_num * area_width
        color = area_colors[area_num]
        
        if area_num == current_area:
            overlay = img.copy()
            cv2.rectangle(overlay, (x1, 0), (x2, h), color, -1)
            cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)
        
        cv2.rectangle(img, (x1, 0), (x2, h), color, 3)
        cv2.putText(img, f"Area {area_num}", (x1 + area_width // 2 - 20, 50),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 3)
    
    if index_tip is not None:
        tip_x, tip_y = int(index_tip[0]), int(index_tip[1])
        cv2.circle(img, (tip_x, tip_y), 15, (255, 0, 255), 3)
        cv2.circle(img, (tip_x, tip_y), 5, (255, 0, 255), -1)


def main():
    print("="*80)
    print("SMART COMBINED DETECTION - STANDALONE")
    print("="*80)
    print("🤚 OPEN HAND → Wrist Rotation | ☝ ONE FINGER → 3-Area | ✊ FIST → Universal")
    print("Controls: q=Quit | r=Reset | s=Save")
    print("="*80)
    
    print("\nInitializing...")
    try:
        detector = RGBHandDetector(fps=30, resolution=(1280, 720), pd_score_thresh=0.5, use_gesture=False)
    except Exception as e:
        print(f"\n❌ Failed to initialize: {e}")
        print("\nMake sure OAK-D camera is connected to USB 3.0 port")
        input("\nPress Enter to exit...")
        return
    
    if not detector.connect():
        print("❌ Failed to connect camera!")
        input("\nPress Enter to exit...")
        return
    
    combined = SmartCombinedDetector(resolution=(1280, 720))
    print("✓ All systems ready!\n")
    
    saved_count = 0
    
    try:
        while True:
            frame, hands, _ = detector.get_frame_and_hands()
            if frame is None:
                continue
            
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            for hand in hands:
                if hasattr(hand, 'landmarks') and hand.landmarks is not None:
                    hand.landmarks[:, 0] = w - hand.landmarks[:, 0]
            
            display = frame.copy()
            hand = hands[0] if hands else None
            mode, gesture, position, angle = combined.update(hand, w, h)
            
            if hand is not None:
                wrist_pt, index_tip = hand.landmarks[WRIST], hand.landmarks[INDEX_TIP]
                
                if mode == DetectionMode.WRIST_ROTATION:
                    draw_wrist_rotation_zones(display, wrist_pt, angle, position)
                    draw_hand_skeleton(display, hand)
                elif mode == DetectionMode.THREE_AREA:
                    draw_three_area_zones(display, index_tip, position)
                    draw_hand_skeleton(display, hand)
                else:
                    draw_hand_skeleton(display, hand)
                
                # Info panel
                overlay = display.copy()
                cv2.rectangle(overlay, (10, 10), (450, 170), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, display, 0.3, 0, display)
                
                y = 40
                mode_text = "WRIST ROTATION" if mode == DetectionMode.WRIST_ROTATION else "3-AREA POINTING" if mode == DetectionMode.THREE_AREA else "UNKNOWN"
                mode_color = (0, 255, 255) if mode == DetectionMode.WRIST_ROTATION else (255, 128, 255) if mode == DetectionMode.THREE_AREA else (128, 128, 128)
                cv2.putText(display, f"Mode: {mode_text}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, mode_color, 2)
                y += 35
                
                gest_text = "FIST" if gesture == GestureType.FIST else "OPEN" if gesture == GestureType.OPEN else "ONE" if gesture == GestureType.ONE else "?"
                gest_color = (0, 0, 255) if gesture == GestureType.FIST else (0, 255, 0) if gesture == GestureType.OPEN else (255, 0, 255) if gesture == GestureType.ONE else (128, 128, 128)
                cv2.putText(display, f"Gesture: {gest_text}", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, gest_color, 2)
                y += 35
                
                pos_text = f"Pos: {position}/4" if mode == DetectionMode.WRIST_ROTATION else f"Area: {position}/3" if mode == DetectionMode.THREE_AREA else "Pos: --"
                cv2.putText(display, pos_text, (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                y += 35
                
                if mode == DetectionMode.WRIST_ROTATION and angle is not None:
                    cv2.putText(display, f"Angle: {angle:.1f}°", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)
                
                # Large position indicator
                pos_colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (255, 128, 0), 4: (0, 0, 255)} if mode == DetectionMode.WRIST_ROTATION else {1: (0, 255, 255), 2: (0, 255, 0), 3: (0, 0, 255)}
                if position > 0:
                    col = pos_colors.get(position, (255, 255, 255))
                    cv2.putText(display, str(position), (w - 110, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 3.0, col, 7)
                    cv2.circle(display, (w - 65, h - 55), 40, col, 4)
            else:
                cv2.putText(display, "SHOW YOUR HAND", (w//2 - 160, h//2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            
            fps = detector.fps_counter.get_global()
            cv2.putText(display, f"FPS: {fps:.1f}", (w - 140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow("Smart Combined Detection", display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                combined.reset()
            elif key == ord('s'):
                cv2.imwrite(f"screenshot_{saved_count:04d}.jpg", display)
                print(f"💾 Saved screenshot_{saved_count:04d}.jpg")
                saved_count += 1
    
    except KeyboardInterrupt:
        print("\n⏹ Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
    finally:
        detector.close()
        cv2.destroyAllWindows()
        print("✓ Done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")