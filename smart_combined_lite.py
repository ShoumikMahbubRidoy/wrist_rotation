#!/usr/bin/env python3
"""
Smart Combined Detection - LITE VERSION
Optimized for slower PCs - Lower resolution, better FPS
"""
import sys
import os
from pathlib import Path
import shutil

# Get paths
if getattr(sys, 'frozen', False):
    application_path = Path(sys._MEIPASS)
    exe_dir = Path(sys.executable).parent
else:
    application_path = Path(__file__).parent
    exe_dir = application_path

# Set up model paths
models_locations = [
    exe_dir / "models",
    application_path / "models",
    application_path / "gesture_oak" / "detection" / "models",
]

models_source = None
for loc in models_locations:
    if loc.exists() and (loc / "palm_detection_sh4.blob").exists():
        models_source = loc
        print(f"✓ Models: {loc}")
        break

if models_source is None:
    print("\n❌ Models not found!")
    input("Press Enter to exit...")
    sys.exit(1)

# Copy to temp (where HandTracker expects)
temp_models = Path(os.environ.get('TEMP', '/tmp')) / "models"
try:
    temp_models.mkdir(parents=True, exist_ok=True)
    for blob_file in models_source.glob("*.blob"):
        target = temp_models / blob_file.name
        if not target.exists():
            shutil.copy2(blob_file, target)
except Exception as e:
    print(f"⚠ Copy warning: {e}")

sys.path.insert(0, str(application_path))
sys.path.insert(0, str(application_path / "gesture_oak"))

import cv2
import numpy as np

try:
    from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
    from gesture_oak.detection.smart_combined_detector import (
        SmartCombinedDetector, DetectionMode, GestureType
    )
except ImportError as e:
    print(f"❌ Import Error: {e}")
    input("Press Enter...")
    sys.exit(1)

WRIST, INDEX_TIP = 0, 8


def draw_simple_hand(img, hand):
    """Simplified hand drawing - faster"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    lm = hand.landmarks
    # Only draw key points (faster)
    for i in [0, 4, 8, 12, 16, 20]:  # Just fingertips and wrist
        cv2.circle(img, tuple(lm[i].astype(int)), 8, (0, 255, 0), -1)
    
    # Simple palm lines
    for a, b in [(0,5), (0,9), (0,13), (0,17), (5,9), (9,13), (13,17)]:
        cv2.line(img, tuple(lm[a].astype(int)), tuple(lm[b].astype(int)), (0, 255, 0), 2)


def draw_simple_wrist_zones(img, wrist_pt, position):
    """Simplified wrist zones - just show active position"""
    cx, cy = int(wrist_pt[0]), int(wrist_pt[1])
    colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (255, 128, 0), 4: (0, 0, 255)}
    
    if position > 0:
        col = colors[position]
        cv2.circle(img, (cx, cy), 80, col, 4)
        cv2.putText(img, str(position), (cx - 20, cy + 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2.0, col, 4)


def draw_simple_areas(img, position):
    """Simplified 3-area display"""
    h, w = img.shape[:2]
    colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (0, 0, 255)}
    area_w = w // 3
    
    if position > 0:
        x1 = (position - 1) * area_w
        x2 = position * area_w
        col = colors[position]
        cv2.rectangle(img, (x1, 0), (x2, h), col, 8)


def main():
    print("="*70)
    print("SMART COMBINED DETECTION - LITE VERSION")
    print("Optimized for better performance on slower PCs")
    print("="*70)
    print("🤚 OPEN → Wrist | ☝ ONE → Areas | ✊ FIST")
    print("Controls: q=Quit | r=Reset")
    print("="*70)
    
    # OPTIMIZED SETTINGS - Lower resolution, lower FPS
    WIDTH, HEIGHT = 640, 480  # Lower resolution (was 1280x720)
    TARGET_FPS = 15           # Lower FPS target (was 30)
    PD_THRESH = 0.6           # Higher threshold = faster (was 0.5)
    
    print(f"\nLITE MODE: {WIDTH}x{HEIGHT} @ {TARGET_FPS} FPS")
    print("Initializing...\n")
    
    try:
        detector = RGBHandDetector(
            fps=TARGET_FPS, 
            resolution=(WIDTH, HEIGHT), 
            pd_score_thresh=PD_THRESH, 
            use_gesture=False
        )
    except Exception as e:
        print(f"❌ Init failed: {e}")
        input("Press Enter...")
        return
    
    if not detector.connect():
        print("❌ Camera failed!")
        input("Press Enter...")
        return
    
    combined = SmartCombinedDetector(resolution=(WIDTH, HEIGHT))
    print("✓ Ready!\n")
    
    # Performance tracking
    frame_times = []
    
    try:
        while True:
            import time
            t_start = time.time()
            
            frame, hands, _ = detector.get_frame_and_hands()
            if frame is None:
                continue
            
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            for hand in hands:
                if hasattr(hand, 'landmarks') and hand.landmarks is not None:
                    hand.landmarks[:, 0] = w - hand.landmarks[:, 0]
            
            # Use original frame (no copying for performance)
            display = frame
            hand = hands[0] if hands else None
            mode, gesture, position, angle = combined.update(hand, w, h)
            
            if hand is not None:
                # SIMPLIFIED DRAWING (faster)
                if mode == DetectionMode.WRIST_ROTATION:
                    draw_simple_wrist_zones(display, hand.landmarks[WRIST], position)
                elif mode == DetectionMode.THREE_AREA:
                    draw_simple_areas(display, position)
                
                draw_simple_hand(display, hand)
                
                # Minimal info overlay
                mode_txt = "WRIST" if mode == DetectionMode.WRIST_ROTATION else "AREA" if mode == DetectionMode.THREE_AREA else "?"
                gest_txt = "FIST" if gesture == GestureType.FIST else "OPEN" if gesture == GestureType.OPEN else "ONE" if gesture == GestureType.ONE else "?"
                
                # Simple text overlay
                cv2.rectangle(display, (5, 5), (250, 90), (0, 0, 0), -1)
                cv2.putText(display, f"Mode: {mode_txt}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display, f"Gest: {gest_txt}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(display, f"Pos: {position}", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Big position indicator
                if position > 0:
                    colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (255, 128, 0), 4: (0, 0, 255)}
                    col = colors.get(position, (255, 255, 255))
                    cv2.putText(display, str(position), (w - 80, h - 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 2.5, col, 6)
            else:
                cv2.putText(display, "SHOW HAND", (w//2 - 100, h//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
            # FPS (track last 30 frames)
            frame_times.append(time.time() - t_start)
            if len(frame_times) > 30:
                frame_times.pop(0)
            avg_time = sum(frame_times) / len(frame_times)
            current_fps = 1.0 / avg_time if avg_time > 0 else 0
            
            cv2.putText(display, f"FPS: {current_fps:.1f}", (w - 120, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            cv2.imshow("Smart Combined (LITE)", display)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                combined.reset()
    
    except KeyboardInterrupt:
        print("\nStopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter...")
    finally:
        detector.close()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal: {e}")
        import traceback
        traceback.print_exc()
        input("Press Enter...")