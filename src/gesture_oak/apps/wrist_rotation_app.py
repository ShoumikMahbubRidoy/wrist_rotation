#!/usr/bin/env python3
"""
Wrist Rotation Tracking Application
Real-time wrist rotation detection with visual feedback
"""
import cv2
import numpy as np
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gesture_oak.detection.hand_detector import HandDetector
from gesture_oak.detection.wrist_rotation_detector import (
    WristRotationDetector, HandState, RotationPosition
)


def draw_rotation_arc(frame, center_x, center_y, radius, angle, position):
    """
    Draw rotation arc indicator showing current angle and position zones.
    
    Args:
        frame: Image to draw on
        center_x, center_y: Arc center coordinates
        radius: Arc radius
        angle: Current angle (0-180)
        position: Current RotationPosition
    """
    # Zone colors
    zone_colors = {
        1: (0, 255, 255),    # Yellow - Left Far
        2: (0, 255, 0),      # Green - Left Near
        3: (255, 128, 0),    # Orange - Right Near
        4: (0, 0, 255),      # Red - Right Far
    }
    
    # Draw zone arcs (background)
    # Position 1: 0° to 60°
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 0, 60, (100, 100, 100), 2)
    
    # Position 2: 60° to 90°
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 60, 90, (100, 100, 100), 2)
    
    # Position 3: 90° to 120°
    cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                180, 90, 120, (100, 100, 100), 2)
    
    # Position 4: 120° to 180°
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
        else:  # RIGHT_FAR
            start_angle, end_angle = 120, 180
        
        cv2.ellipse(frame, (center_x, center_y), (radius, radius), 
                   180, start_angle, end_angle, color, 8)
    
    # Draw current angle indicator (line)
    angle_rad = np.radians(180 - angle)  # Flip for display
    end_x = int(center_x + radius * np.cos(angle_rad))
    end_y = int(center_y + radius * np.sin(angle_rad))
    
    cv2.line(frame, (center_x, center_y), (end_x, end_y), (255, 255, 255), 3)
    cv2.circle(frame, (end_x, end_y), 8, (0, 255, 0), -1)
    
    # Draw center point
    cv2.circle(frame, (center_x, center_y), 5, (255, 255, 255), -1)
    
    # Draw angle text
    text = f"{int(angle)}°"
    cv2.putText(frame, text, (center_x - 20, center_y - radius - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)


def draw_hand_state_indicator(frame, hand_state, x, y):
    """
    Draw hand state (fisted/open) indicator.
    
    Args:
        frame: Image to draw on
        hand_state: HandState enum
        x, y: Position to draw at
    """
    if hand_state == HandState.OPEN:
        color = (0, 255, 0)  # Green
        text = "HAND: OPEN"
        icon = "OPEN"
    else:
        color = (0, 0, 255)  # Red
        text = "HAND: FISTED"
        icon = "FIST"
    
    # Background box
    cv2.rectangle(frame, (x, y), (x + 200, y + 50), (0, 0, 0), -1)
    cv2.rectangle(frame, (x, y), (x + 200, y + 50), color, 2)
    
    # Text
    cv2.putText(frame, text, (x + 10, y + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)


def draw_position_display(frame, position, position_name, x, y):
    """
    Draw current position display.
    
    Args:
        frame: Image to draw on
        position: Position value (0-4)
        position_name: Position name string
        x, y: Position to draw at
    """
    # Position color
    if position == 0:
        color = (128, 128, 128)  # Gray
    elif position == 1:
        color = (0, 255, 255)  # Yellow
    elif position == 2:
        color = (0, 255, 0)  # Green
    elif position == 3:
        color = (255, 128, 0)  # Orange
    else:
        color = (0, 0, 255)  # Red
    
    # Large position number
    cv2.putText(frame, str(position), (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 3.0, color, 8)
    
    # Position name
    cv2.putText(frame, position_name, (x, y + 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


def draw_hand_landmarks(frame, hand):
    """Draw hand landmarks and skeleton"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    landmarks = hand.landmarks
    
    # Draw connections (simplified skeleton)
    connections = [
        # Thumb
        (0, 1), (1, 2), (2, 3), (3, 4),
        # Index
        (0, 5), (5, 6), (6, 7), (7, 8),
        # Middle
        (0, 9), (9, 10), (10, 11), (11, 12),
        # Ring
        (0, 13), (13, 14), (14, 15), (15, 16),
        # Pinky
        (0, 17), (17, 18), (18, 19), (19, 20),
        # Palm
        (5, 9), (9, 13), (13, 17)
    ]
    
    for start, end in connections:
        try:
            pt1 = tuple(landmarks[start].astype(int))
            pt2 = tuple(landmarks[end].astype(int))
            cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        except (IndexError, AttributeError):
            continue
    
    # Draw landmark points
    for i, point in enumerate(landmarks):
        try:
            pt = tuple(point.astype(int))
            # Wrist and finger tips larger
            if i in [0, 4, 8, 12, 16, 20]:
                cv2.circle(frame, pt, 6, (0, 0, 255), -1)
            else:
                cv2.circle(frame, pt, 4, (255, 255, 255), -1)
        except (AttributeError, ValueError):
            continue


def main():
    """Main application loop"""
    print("="*60)
    print("WRIST ROTATION DETECTION SYSTEM")
    print("="*60)
    print("Camera: Palm-facing, 40-100cm distance")
    print("Detection: Hand state → Rotation angle → Position (1-4)")
    print()
    print("Controls:")
    print("  'q' - Quit")
    print("  'r' - Reset statistics")
    print("  's' - Save frame")
    print("="*60)
    
    # Initialize detectors
    print("Initializing hand detector...")
    hand_detector = HandDetector(
        fps=30,
        resolution=(640, 480),
        pd_score_thresh=0.12,  # Slightly lower for palm-facing
        use_gesture=False
    )
    
    if not hand_detector.connect():
        print("Failed to connect to OAK-D camera!")
        print("Please check:")
        print("  1. Camera is connected via USB 3.0")
        print("  2. Drivers are installed")
        print("  3. No other application is using the camera")
        return
    
    print("Initializing wrist rotation detector...")
    rotation_detector = WristRotationDetector(
        buffer_size=10,
        angle_smoothing=5
    )
    
    print("Starting detection...")
    print()
    
    frame_count = 0
    saved_frame_count = 0
    
    # Check for stop flag
    stop_file_path = os.environ.get("TG25_STOP_FILE", "")
    
    try:
        while True:
            # Check stop flag
            if stop_file_path and os.path.exists(stop_file_path):
                print("Stop flag detected. Exiting...")
                break
            
            # Get frame and hands
            frame, hands, depth_frame = hand_detector.get_frame_and_hands()
            
            if frame is None:
                continue
            
            frame_count += 1
            
            # Create display frame
            display_frame = frame.copy()
            h, w = display_frame.shape[:2]
            
            # Process first detected hand
            if len(hands) > 0:
                hand = hands[0]  # Use first hand
                
                # Update rotation detector
                position, angle, hand_state = rotation_detector.update(hand)
                
                # Get state info
                state_info = rotation_detector.get_state_info()
                
                # Draw hand landmarks
                draw_hand_landmarks(display_frame, hand)
                
                # Draw rotation arc (top-right)
                arc_x = w - 150
                arc_y = 150
                arc_radius = 100
                draw_rotation_arc(display_frame, arc_x, arc_y, arc_radius, 
                                angle, position)
                
                # Draw hand state indicator (top-left)
                draw_hand_state_indicator(display_frame, hand_state, 10, 10)
                
                # Draw position display (bottom-left, large)
                draw_position_display(display_frame, position.value, 
                                    state_info['position_name'], 20, h - 100)
                
                # Draw statistics (bottom-right)
                stats_x = w - 350
                stats_y = h - 120
                stats_lines = [
                    f"Position: {state_info['position']}",
                    f"Angle: {state_info['angle']:.1f}",
                    f"Hand: {state_info['hand_state']}",
                    f"Changes: {state_info['total_changes']}",
                ]
                
                for i, line in enumerate(stats_lines):
                    y = stats_y + i * 30
                    cv2.putText(display_frame, line, (stats_x, y),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            else:
                # No hand detected
                cv2.putText(display_frame, "NO HAND DETECTED", (20, h - 30),
                          cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
            
            # Draw FPS
            fps = hand_detector.fps_counter.get_global()
            cv2.putText(display_frame, f"FPS: {fps:.1f}", (w - 150, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show frame
            cv2.imshow("Wrist Rotation Detection", display_frame)
            
            # Handle keys
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("Quit requested")
                break
            elif key == ord('r'):
                print("Resetting statistics...")
                rotation_detector.reset()
            elif key == ord('s'):
                filename = f"wrist_rotation_frame_{saved_frame_count:04d}.jpg"
                cv2.imwrite(filename, display_frame)
                print(f"Saved frame: {filename}")
                saved_frame_count += 1
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Cleanup
        print("Cleaning up...")
        hand_detector.close()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()