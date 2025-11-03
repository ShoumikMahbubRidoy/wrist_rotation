#!/usr/bin/env python3
"""
FIXED Wrist Rotation App
- Better fist detection with debug display
- Original rotation logic (no dead zone)
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


def draw_rotation_arc(frame, center_x, center_y, radius, angle, position):
    """Draw rotation arc - ORIGINAL (no dead zone)"""
    zone_colors = {
        1: (0, 255, 255),    # Yellow - Left Far
        2: (0, 255, 0),      # Green - Left Near
        3: (255, 128, 0),    # Orange - Right Near
        4: (0, 0, 255),      # Red - Right Far
    }
    
    # Draw zone arcs
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 0, 60, (100, 100, 100), 2)
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 60, 90, (100, 100, 100), 2)
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 90, 120, (100, 100, 100), 2)
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 120, 180, (100, 100, 100), 2)
    
    # Highlight current zone
    if position.value > 0:
        color = zone_colors.get(position.value, (255, 255, 255))
        
        if position == RotationPosition.LEFT_FAR:
            start_angle, end_angle = 0, 60
        elif position == RotationPosition.LEFT_NEAR:
            start_angle, end_angle = 60, 90
        elif position == RotationPosition.RIGHT_NEAR:
            start_angle, end_angle = 90, 120
        else:
            start_angle, end_angle = 120, 180
        
        cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                   180, start_angle, end_angle, color, 8)
    
    # Draw angle indicator
    if angle is not None:
        angle_rad = np.radians(180 - angle)
        end_x = int(center_x + radius * np.cos(angle_rad))
        end_y = int(center_y + radius * np.sin(angle_rad))
        
        cv2.line(frame, (center_x, center_y), (end_x, end_y), (255, 255, 255), 3)
        cv2.circle(frame, (end_x, end_y), 8, (0, 255, 0), -1)
        
        text = f"{int(angle)}"
        cv2.putText(frame, text, (center_x - 20, center_y - radius - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.circle(frame, (center_x, center_y), 5, (255, 255, 255), -1)


def draw_hand_state_indicator(frame, hand_state, x, y):
    """Draw hand state"""
    if hand_state == HandState.OPEN:
        color = (0, 255, 0)
        text = "HAND: OPEN"
    elif hand_state == HandState.FISTED:
        color = (0, 0, 255)
        text = "HAND: FISTED"
    else:
        color = (128, 128, 128)
        text = "HAND: UNKNOWN"
    
    cv2.rectangle(frame, (x, y), (x + 220, y + 50), (0, 0, 0), -1)
    cv2.rectangle(frame, (x, y), (x + 220, y + 50), color, 2)
    cv2.putText(frame, text, (x + 10, y + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def draw_finger_curl_ratios(frame, finger_ratios, curl_threshold, x, y):
    """
    Draw finger curl ratios for debugging
    Shows the distance ratio for each finger
    Green = Extended (ratio > threshold)
    Red = Curled (ratio < threshold)
    """
    # Title
    cv2.putText(frame, "Finger Curl Ratios:", (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(frame, f"(Threshold: {curl_threshold:.2f})", (x, y + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    
    fingers = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    
    for i, finger in enumerate(fingers):
        finger_key = finger.lower()
        ratio = finger_ratios.get(finger_key, 0.0)
        
        # Extended if ratio > threshold
        is_extended = ratio > curl_threshold
        color = (0, 255, 0) if is_extended else (0, 0, 255)
        state = "EXT" if is_extended else "CURL"
        
        y_pos = y + 45 + (i * 25)
        text = f"{finger}: {ratio:.2f} [{state}]"
        cv2.putText(frame, text, (x, y_pos),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def draw_position_display(frame, position, position_name, x, y):
    """Draw position number"""
    if position == 0:
        color = (128, 128, 128)
    elif position == 1:
        color = (0, 255, 255)
    elif position == 2:
        color = (0, 255, 0)
    elif position == 3:
        color = (255, 128, 0)
    else:
        color = (0, 0, 255)
    
    cv2.putText(frame, str(position), (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 3.0, color, 8)
    cv2.putText(frame, position_name, (x, y + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)


def draw_hand_landmarks(frame, hand):
    """Draw hand skeleton"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    landmarks = hand.landmarks
    connections = [
        (0, 1), (1, 2), (2, 3), (3, 4),
        (0, 5), (5, 6), (6, 7), (7, 8),
        (0, 9), (9, 10), (10, 11), (11, 12),
        (0, 13), (13, 14), (14, 15), (15, 16),
        (0, 17), (17, 18), (18, 19), (19, 20),
        (5, 9), (9, 13), (13, 17)
    ]
    
    for start, end in connections:
        try:
            pt1 = tuple(landmarks[start].astype(int))
            pt2 = tuple(landmarks[end].astype(int))
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        except (IndexError, AttributeError):
            continue
    
    for i, point in enumerate(landmarks):
        try:
            pt = tuple(point.astype(int))
            if i in [0, 4, 8, 12, 16, 20]:
                cv2.circle(frame, pt, 6, (0, 0, 255), -1)
            else:
                cv2.circle(frame, pt, 4, (255, 255, 255), -1)
        except (AttributeError, ValueError):
            continue


def main():
    """Main application"""
    print("="*70)
    print("FIXED WRIST ROTATION DETECTION")
    print("="*70)
    print("Camera: Palm-facing, 40-100cm")
    print()
    print("Position Mapping (ORIGINAL - NO DEAD ZONE):")
    print("  Position 1: 0° to 60° (LEFT FAR)")
    print("  Position 2: 60° to 90° (LEFT NEAR)")
    print("  Position 3: 90° to 120° (RIGHT NEAR)")
    print("  Position 4: 120° to 180° (RIGHT FAR)")
    print()
    print("Fist Detection: Distance ratio method")
    print("  Extended finger: ratio > 0.70")
    print("  Curled finger: ratio < 0.70")
    print()
    print("Controls:")
    print("  'q' - Quit")
    print("  'r' - Reset")
    print("  's' - Save frame")
    print("  'd' - Toggle debug")
    print("  '+' - Increase threshold (stricter)")
    print("  '-' - Decrease threshold (looser)")
    print("="*70)
    
    # Initialize
    print("Initializing hand detector...")
    hand_detector = HandDetector(
        fps=30,
        resolution=(640, 480),
        pd_score_thresh=0.10,
        use_gesture=False
    )
    
    if not hand_detector.connect():
        print("Failed to connect to camera!")
        return
    
    print("Initializing rotation detector...")
    rotation_detector = WristRotationDetector(
        buffer_size=15,
        angle_smoothing=7,
        ema_alpha=0.35,
        open_frames=3,
        fist_frames=5,
        min_lm_score=0.3,
        max_angle_jump=40.0,
        neutral_calibration_frames=12,
        curl_threshold=0.70,  # ADJUSTABLE - increase if too sensitive
    )
    
    print("Starting...")
    print()
    
    saved_count = 0
    show_debug = True
    stop_file = os.environ.get("TG25_STOP_FILE", "")
    
    try:
        while True:
            if stop_file and os.path.exists(stop_file):
                break
            
            frame, hands, depth = hand_detector.get_frame_and_hands()
            if frame is None:
                continue
            
            display = frame.copy()
            h, w = display.shape[:2]
            
            if len(hands) > 0:
                hand = hands[0]
                
                # Update detector
                position, angle, hand_state = rotation_detector.update(hand)
                info = rotation_detector.get_state_info()
                
                # Draw everything
                draw_hand_landmarks(display, hand)
                
                # Rotation arc (top-right)
                draw_rotation_arc(display, w - 150, 150, 100, angle, position)
                
                # Hand state (top-left)
                draw_hand_state_indicator(display, hand_state, 10, 10)
                
                # Position (bottom-left)
                draw_position_display(display, position.value,
                                    info['position_name'], 20, h - 100)
                
                # Curl ratios debug (left side)
                if show_debug:
                    finger_ratios = info.get('finger_ratios', {})
                    # Get current threshold from detector
                    curl_threshold = rotation_detector.curl_threshold
                    draw_finger_curl_ratios(display, finger_ratios, 
                                          curl_threshold, 10, 80)
                
                # Stats (bottom-right)
                stats_x = w - 400
                stats_y = h - 150
                stats = [
                    f"Position: {info['position']}",
                    f"Angle: {info['angle']:.1f}" if info['angle'] else "Angle: N/A",
                    f"Hand: {info['hand_state']}",
                    f"Changes: {info['total_changes']}",
                    f"Threshold: {rotation_detector.curl_threshold:.2f}",
                ]
                
                for i, line in enumerate(stats):
                    cv2.putText(display, line, (stats_x, stats_y + i * 25),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            else:
                cv2.putText(display, "NO HAND DETECTED", (20, h - 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
            # FPS
            fps = hand_detector.fps_counter.get_global()
            cv2.putText(display, f"FPS: {fps:.1f}", (w - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            cv2.imshow("Wrist Rotation Detection", display)
            
            # Keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                print("Reset")
                rotation_detector.reset()
            elif key == ord('s'):
                filename = f"wrist_{saved_count:04d}.jpg"
                cv2.imwrite(filename, display)
                print(f"Saved: {filename}")
                saved_count += 1
            elif key == ord('d'):
                show_debug = not show_debug
                print(f"Debug: {'ON' if show_debug else 'OFF'}")
            elif key == ord('+') or key == ord('='):
                rotation_detector.curl_threshold += 0.05
                print(f"Threshold: {rotation_detector.curl_threshold:.2f} (stricter)")
            elif key == ord('-') or key == ord('_'):
                rotation_detector.curl_threshold = max(0.1, rotation_detector.curl_threshold - 0.05)
                print(f"Threshold: {rotation_detector.curl_threshold:.2f} (looser)")
    
    except KeyboardInterrupt:
        print("\nInterrupted")
    
    finally:
        print("Cleanup...")
        hand_detector.close()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()