# src/gesture_oak/apps/wrist_rotation_app.py
#!/usr/bin/env python3
"""
FIXED Wrist Rotation App
- Mirrored frame (natural hand movement)
- Better fist detection
- Writes to result.txt
- Shows selected position when fisted
"""
import cv2
import numpy as np
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gesture_oak.detection.hand_detector import HandDetector
from gesture_oak.detection.wrist_rotation_detector import (
    WristRotationDetector, HandState, RotationPosition
)


def draw_hand_landmarks(frame, hand):
    """Draw hand skeleton"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    landmarks = hand.landmarks
    
    # Connections
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
        (0, 5), (5, 6), (6, 7), (7, 8),  # Index
        (0, 9), (9, 10), (10, 11), (11, 12),  # Middle
        (0, 13), (13, 14), (14, 15), (15, 16),  # Ring
        (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
        (5, 9), (9, 13), (13, 17)  # Palm
    ]
    
    for start, end in connections:
        try:
            pt1 = tuple(landmarks[start].astype(int))
            pt2 = tuple(landmarks[end].astype(int))
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        except (IndexError, AttributeError):
            continue
    
    # Landmark points
    for i, point in enumerate(landmarks):
        try:
            pt = tuple(point.astype(int))
            if i in [0, 4, 8, 12, 16, 20]:  # Wrist and fingertips
                cv2.circle(frame, pt, 6, (0, 0, 255), -1)
            else:
                cv2.circle(frame, pt, 4, (255, 255, 255), -1)
        except (AttributeError, ValueError):
            continue


def main():
    """Main application"""
    print("="*70)
    print("WRIST ROTATION DETECTION SYSTEM")
    print("="*70)
    print("Camera: Palm-facing, 40-100cm distance")
    print()
    print("Workflow:")
    print("  1. If fisted → Returns: Fisted=1, SelectedPosition=(last position)")
    print("  2. If hand open → Returns: HandOpen=1, Position=1/2/3/4")
    print("     - Position 1: 0° to 60° (LEFT)")
    print("     - Position 2: 60° to 90° (LEFT-CENTER)")
    print("     - Position 3: 90° to 120° (RIGHT-CENTER)")
    print("     - Position 4: 120° to 180° (RIGHT)")
    print("  3. When fist closes → Selected position is saved")
    print()
    print("Output: result.txt (updates in real-time)")
    print()
    print("Controls:")
    print("  'q' - Quit")
    print("  'r' - Reset")
    print("  's' - Save frame")
    print("="*70)
    
    # Initialize
    print("Initializing...")
    hand_detector = HandDetector(
        fps=30,
        resolution=(640, 480),
        pd_score_thresh=0.10,
        use_gesture=False
    )
    
    if not hand_detector.connect():
        print("❌ Failed to connect to camera!")
        return
    
    rotation_detector = WristRotationDetector(
        buffer_size=10,
        angle_smoothing=5,
        ema_alpha=0.3,
        open_frames=2,
        fist_frames=3,
        finger_extension_threshold=0.65,  # Stricter fist detection
    )
    
    print("✅ Started!")
    print()
    
    saved_count = 0
    stop_file = os.environ.get("TG25_STOP_FILE", "")
    
    try:
        while True:
            # Check stop
            if stop_file and os.path.exists(stop_file):
                break
            
            # Get frame
            frame, hands, depth_frame = hand_detector.get_frame_and_hands()
            if frame is None:
                continue
            
            # MIRROR THE FRAME (natural hand movement)
            frame = cv2.flip(frame, 1)
            
            # MIRROR THE HAND LANDMARKS TOO!
            if len(hands) > 0:
                for hand in hands:
                    if hasattr(hand, 'landmarks') and hand.landmarks is not None:
                        # Mirror X coordinates
                        hand.landmarks[:, 0] = w - hand.landmarks[:, 0]
            
            # Create display
            display = frame.copy()
            h, w = display.shape[:2]
            
            if len(hands) > 0:
                hand = hands[0]
                
                # Update detector
                position, angle, hand_state = rotation_detector.update(hand)
                state_info = rotation_detector.get_state_info()
                
                # Draw hand
                draw_hand_landmarks(display, hand)
                
                # Draw info panel (top-left)
                panel_h = 200
                overlay = display.copy()
                cv2.rectangle(overlay, (10, 10), (350, panel_h), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, display, 0.3, 0, display)
                
                y = 40
                
                # Hand state
                if hand_state == HandState.FISTED:
                    color = (0, 0, 255)  # Red
                    text = "FISTED = 1"
                elif hand_state == HandState.OPEN:
                    color = (0, 255, 0)  # Green
                    text = "HAND OPEN = 1"
                else:
                    color = (128, 128, 128)
                    text = "UNKNOWN"
                
                cv2.putText(display, text, (20, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                y += 40
                
                # Position or Selected Position
                if hand_state == HandState.FISTED:
                    # Show selected position
                    sel_pos = state_info['selected_position']
                    cv2.putText(display, f"Selected Position: {sel_pos}", (20, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                elif hand_state == HandState.OPEN:
                    # Show current position
                    pos_val = position.value
                    cv2.putText(display, f"Position: {pos_val}", (20, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                y += 40
                
                # Angle
                if angle is not None:
                    cv2.putText(display, f"Angle: {angle:.1f}°", (20, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 128, 0), 2)
                y += 35
                
                # Finger states (debug)
                finger_states = state_info.get('finger_states', {})
                fingers_text = "Fingers: "
                for name, extended in finger_states.items():
                    fingers_text += f"{name[0].upper()}:{'✓' if extended else '✗'} "
                cv2.putText(display, fingers_text, (20, y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # Large position display (bottom-right)
                if hand_state == HandState.OPEN and position.value > 0:
                    pos_color = {
                        1: (0, 255, 255),
                        2: (0, 255, 0),
                        3: (255, 128, 0),
                        4: (0, 0, 255)
                    }.get(position.value, (255, 255, 255))
                    
                    cv2.putText(display, str(position.value), (w - 120, h - 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 3.0, pos_color, 8)
                elif hand_state == HandState.FISTED:
                    # Show selected position
                    sel_pos = state_info['selected_position']
                    cv2.putText(display, f"SEL:{sel_pos}", (w - 150, h - 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 255), 4)
            
            else:
                # No hand
                cv2.putText(display, "PUT YOUR FISTED HAND", (w//2 - 200, h//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
            
            # FPS
            fps = hand_detector.fps_counter.get_global()
            cv2.putText(display, f"FPS: {fps:.1f}", (w - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show
            cv2.imshow("Wrist Rotation Detection", display)
            
            # Keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                rotation_detector.reset()
                print("Reset!")
            elif key == ord('s'):
                filename = f"wrist_{saved_count:04d}.jpg"
                cv2.imwrite(filename, display)
                print(f"Saved: {filename}")
                saved_count += 1
    
    except KeyboardInterrupt:
        print("\nStopped")
    
    finally:
        hand_detector.close()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()