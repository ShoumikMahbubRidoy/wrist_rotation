#!/usr/bin/env python3
"""
Wrist Rotation Detection - DepthAI 3.1.0
"""
import cv2
import numpy as np
import depthai as dai
import math
from collections import deque
from enum import Enum
import mediapipe as mp

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles


class HandState(Enum):
    UNKNOWN = 0
    FISTED = 1
    OPEN = 2


class RotationPosition(Enum):
    NONE = 0
    LEFT_FAR = 1
    LEFT_NEAR = 2
    RIGHT_NEAR = 3
    RIGHT_FAR = 4


class WristRotationDetector:
    def __init__(self):
        self.hands_detector = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.current_state = HandState.UNKNOWN
        self.current_position = RotationPosition.NONE
        self.current_angle = 90.0
        
        self.angle_buffer = deque(maxlen=5)
        self.state_buffer = deque(maxlen=3)
        
        self.position_changes = 0
        self.last_position = RotationPosition.NONE
        
        self.calibrated = False
        self.calibration_angles = []
        self.angle_offset = 0.0
        
        self.finger_extended = {
            'thumb': False,
            'index': False,
            'middle': False,
            'ring': False,
            'pinky': False
        }
    
    def detect_hand_state(self, landmarks) -> HandState:
        if landmarks is None:
            return HandState.UNKNOWN
        
        wrist = landmarks[0]
        
        def is_finger_extended(tip_idx, mcp_idx):
            tip = landmarks[tip_idx]
            mcp = landmarks[mcp_idx]
            
            tip_dist = math.sqrt((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)
            mcp_dist = math.sqrt((mcp.x - wrist.x)**2 + (mcp.y - wrist.y)**2)
            
            if mcp_dist < 0.01:
                return False
            
            ratio = tip_dist / mcp_dist
            return ratio > 1.2
        
        def is_finger_straight(tip_idx, pip_idx, mcp_idx):
            tip = landmarks[tip_idx]
            mcp = landmarks[mcp_idx]
            return tip.y < mcp.y - 0.02
        
        thumb_ext = is_finger_extended(4, 2)
        index_ext = is_finger_extended(8, 5) or is_finger_straight(8, 6, 5)
        middle_ext = is_finger_extended(12, 9) or is_finger_straight(12, 10, 9)
        ring_ext = is_finger_extended(16, 13) or is_finger_straight(16, 14, 13)
        pinky_ext = is_finger_extended(20, 17) or is_finger_straight(20, 18, 17)
        
        self.finger_extended = {
            'thumb': thumb_ext,
            'index': index_ext,
            'middle': middle_ext,
            'ring': ring_ext,
            'pinky': pinky_ext
        }
        
        any_extended = thumb_ext or index_ext or middle_ext or ring_ext or pinky_ext
        return HandState.OPEN if any_extended else HandState.FISTED
    
    def calculate_wrist_angle(self, landmarks):
        if landmarks is None:
            return None
        
        wrist = landmarks[0]
        middle_mcp = landmarks[9]
        
        dx = middle_mcp.x - wrist.x
        dy = middle_mcp.y - wrist.y
        
        angle_rad = math.atan2(-dy, -dx)
        angle_deg = math.degrees(angle_rad)
        
        angle_deg = angle_deg % 360
        if angle_deg > 180:
            angle_deg = 360 - angle_deg
        
        return angle_deg
    
    def calibrate_angle(self, angle: float):
        if not self.calibrated:
            self.calibration_angles.append(angle)
            
            if len(self.calibration_angles) >= 10:
                avg_angle = np.mean(self.calibration_angles)
                self.angle_offset = 90.0 - avg_angle
                self.calibrated = True
                print(f"Calibrated! Offset: {self.angle_offset:.1f} deg")
    
    def map_angle_to_position(self, angle: float) -> RotationPosition:
        if angle < 60:
            return RotationPosition.LEFT_FAR
        elif angle < 90:
            return RotationPosition.LEFT_NEAR
        elif angle < 120:
            return RotationPosition.RIGHT_NEAR
        else:
            return RotationPosition.RIGHT_FAR
    
    def update(self, frame):
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands_detector.process(rgb_frame)
        
        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            
            state = self.detect_hand_state(hand_landmarks.landmark)
            self.state_buffer.append(state)
            
            if len(self.state_buffer) >= 2:
                open_count = sum(1 for s in self.state_buffer if s == HandState.OPEN)
                self.current_state = HandState.OPEN if open_count >= 2 else HandState.FISTED
            else:
                self.current_state = state
            
            raw_angle = self.calculate_wrist_angle(hand_landmarks.landmark)
            
            if raw_angle is not None:
                self.calibrate_angle(raw_angle)
                
                angle = raw_angle + self.angle_offset
                angle = angle % 360
                if angle > 180:
                    angle = 360 - angle
                
                self.angle_buffer.append(angle)
                if len(self.angle_buffer) >= 3:
                    self.current_angle = np.median(list(self.angle_buffer))
                else:
                    self.current_angle = angle
                
                if self.current_state == HandState.OPEN:
                    new_pos = self.map_angle_to_position(self.current_angle)
                    
                    if new_pos != self.last_position and new_pos != RotationPosition.NONE:
                        if self.last_position != RotationPosition.NONE:
                            self.position_changes += 1
                    
                    self.current_position = new_pos
                    self.last_position = new_pos
                else:
                    self.current_position = RotationPosition.NONE
            
            mp_drawing.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS,
                mp_drawing_styles.get_default_hand_landmarks_style(),
                mp_drawing_styles.get_default_hand_connections_style()
            )
        else:
            self.current_state = HandState.UNKNOWN
            self.current_position = RotationPosition.NONE
        
        return frame, self.current_position, self.current_angle, self.current_state
    
    def reset(self):
        self.calibrated = False
        self.calibration_angles.clear()
        self.angle_offset = 0.0
        self.angle_buffer.clear()
        self.state_buffer.clear()
        self.position_changes = 0
        self.last_position = RotationPosition.NONE
        print("Reset")
    
    def get_state_info(self):
        return {
            'hand_state': self.current_state.name,
            'position': self.current_position.value,
            'position_name': self._get_position_name(),
            'angle': round(self.current_angle, 1),
            'total_changes': self.position_changes,
            'calibrated': self.calibrated,
            'finger_extended': self.finger_extended.copy()
        }
    
    def _get_position_name(self):
        names = {
            RotationPosition.NONE: "NONE",
            RotationPosition.LEFT_FAR: "Position 1 (LEFT FAR)",
            RotationPosition.LEFT_NEAR: "Position 2 (LEFT NEAR)",
            RotationPosition.RIGHT_NEAR: "Position 3 (RIGHT NEAR)",
            RotationPosition.RIGHT_FAR: "Position 4 (RIGHT FAR)",
        }
        return names.get(self.current_position, "NONE")


def main():
    print("="*70)
    print("WRIST ROTATION - DepthAI 3.1.0")
    print("="*70)
    print("Camera: RGB, Distance: 40-100cm")
    print("Position Mapping:")
    print("  Pos 1: 0-60deg LEFT FAR")
    print("  Pos 2: 60-90deg LEFT NEAR")
    print("  Pos 3: 90-120deg RIGHT NEAR")
    print("  Pos 4: 120-180deg RIGHT FAR")
    print("Controls: q=Quit, r=Reset, d=Debug")
    print("="*70)
    
    detector = WristRotationDetector()
    
    # Pipeline using DepthAI 3.1.0 API
    pipeline = dai.Pipeline()
    
    # Use Camera node (not ColorCamera)
    cam = pipeline.createCamera()
    cam.setPreviewSize(640, 480)
    cam.setFps(30)
    
    # Create output
    xout = pipeline.createXLinkOut()
    xout.setStreamName("preview")
    cam.preview.link(xout.input)
    
    print("Connecting...")
    try:
        with dai.Device(pipeline) as device:
            print(f"Connected: {device.getDeviceName()}")
            
            q = device.getOutputQueue("preview", maxSize=4, blocking=False)
            
            print("Hold hand vertical 2sec to calibrate...")
            
            show_debug = True
            
            while True:
                inFrame = q.get()
                frame = inFrame.getCvFrame()
                
                frame, position, angle, state = detector.update(frame)
                info = detector.get_state_info()
                
                h, w = frame.shape[:2]
                
                # Hand state
                color = (0, 255, 0) if state == HandState.OPEN else (0, 0, 255)
                cv2.rectangle(frame, (10, 10), (230, 60), (0, 0, 0), -1)
                cv2.rectangle(frame, (10, 10), (230, 60), color, 2)
                cv2.putText(frame, f"HAND: {state.name}", (20, 45),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Position
                colors = {0: (128, 128, 128), 1: (0, 255, 255), 
                         2: (0, 255, 0), 3: (255, 128, 0), 4: (0, 0, 255)}
                pos_color = colors.get(position.value, (128, 128, 128))
                cv2.putText(frame, str(position.value), (20, h - 80),
                           cv2.FONT_HERSHEY_SIMPLEX, 4.0, pos_color, 10)
                cv2.putText(frame, info['position_name'], (20, h - 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, pos_color, 2)
                
                # Stats
                stats = [
                    f"Pos: {info['position']}",
                    f"Ang: {info['angle']:.1f}",
                    f"State: {info['hand_state']}",
                    f"Chg: {info['total_changes']}",
                    f"Cal: {info['calibrated']}"
                ]
                for i, line in enumerate(stats):
                    cv2.putText(frame, line, (w - 250, 30 + i * 25),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                # Debug
                if show_debug:
                    fingers = info['finger_extended']
                    y = 100
                    cv2.putText(frame, "Fingers:", (10, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    for i, (name, ext) in enumerate(fingers.items()):
                        c = (0, 255, 0) if ext else (0, 0, 255)
                        s = "EXT" if ext else "CURL"
                        cv2.putText(frame, f"{name}: {s}", (10, y + 25 + i * 20),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, c, 1)
                
                cv2.imshow("Wrist Rotation", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    detector.reset()
                elif key == ord('d'):
                    show_debug = not show_debug
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()