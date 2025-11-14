# Implementation Guide: RGB Camera Integration + 3-Area Detection

## Overview

This guide integrates Nakakawa-san's RGB-based HandTracker approach into your existing project and adds a new 3-area detection feature for index finger/fisted hand gestures.

## Part 1: Understanding Nakakawa-san's Approach

### Key Insights from test_hand_data.py

1. **Uses RGB camera** via HandTracker (not IR mono cameras)
2. **Pinch detection** based on thumb-index finger distance
3. **Area detection** using weighted average (80% index finger, 20% thumb)
4. **Event-driven** with state tracking (previous vs current frame)
5. **Grid visualization** with 3 columns × 2 rows (6 areas)

### Core Functions

```python
def get_pinch_area(hand, frame_shape, cols=3, rows=2):
    """Calculate pinch center position and return area number"""
    h, w = frame_shape[:2]
    thumb_tip = hand.landmarks[4]
    index_tip = hand.landmarks[8]
    
    # Weighted average (80% index, 20% thumb)
    pinch_center_x = thumb_tip[0] * 0.2 + index_tip[0] * 0.8
    pinch_center_y = thumb_tip[1] * 0.2 + index_tip[1] * 0.8
    
    # Calculate area
    x = pinch_center_x / w
    y = pinch_center_y / h
    col = min(int(x * cols), cols - 1)
    row = min(int(y * rows), rows - 1)
    area = row * cols + col + 1
    return area, (col, row), (pinch_center_x, pinch_center_y)

def is_pinching(hand, threshold=50):
    """Check if thumb and index finger are pinching"""
    thumb_tip = hand.landmarks[4]
    index_tip = hand.landmarks[8]
    dist = np.linalg.norm(thumb_tip - index_tip)
    return dist < threshold
```

## Part 2: New 3-Area Detection Feature Requirements

### Feature Specification

**Detection Targets:**
- Index finger extended (ONE gesture)
- Fisted hand (ZERO gesture)

**Screen Division:**
```
┌─────────┬─────────┬─────────┐
│ Area 1  │ Area 2  │ Area 3  │
│ 33.33%  │ 33.33%  │ 33.33%  │
└─────────┴─────────┴─────────┘
```

**Detection Logic:**
1. Detect if hand is showing ONE (index extended) or FIST
2. Calculate reference point (index fingertip for ONE, palm center for FIST)
3. Determine which area (1, 2, or 3) the reference point is in
4. Send appropriate UDP messages

## Part 3: Implementation Strategy

### Step 1: Create RGB-Compatible HandTracker Wrapper

Create `src/gesture_oak/detection/rgb_hand_detector.py`:

```python
#!/usr/bin/env python3
"""
RGB Hand Detector - Uses RGB camera like Nakakawa-san's approach
Works with existing HandTracker + HandTrackerRenderer
"""
import sys
from pathlib import Path
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from HandTracker import HandTracker
from HandTrackerRenderer import HandTrackerRenderer
from ..utils.FPS import FPS


class RGBHandDetector:
    """
    RGB-based hand detector using HandTracker
    Compatible with all existing app features
    """
    
    def __init__(self, 
                 fps: int = 30,
                 resolution=(640, 480),
                 pd_score_thresh: float = 0.15,
                 use_gesture: bool = True):
        """
        Initialize RGB hand detector
        
        Args:
            fps: Target FPS
            resolution: Output resolution (width, height)
            pd_score_thresh: Palm detection threshold
            use_gesture: Enable gesture recognition
        """
        self.fps_target = fps
        self.resolution = resolution
        self.img_w, self.img_h = resolution
        
        # Create HandTracker (uses RGB camera)
        self.tracker = HandTracker(
            solo=False,              # Detect multiple hands
            lm_model="lite",         # Use lite model
            lm_nb_threads=2,
            internal_fps=fps,
            resolution="full",       # 1920x1080
            internal_frame_height=resolution[1],
            pd_score_thresh=pd_score_thresh,
            lm_score_thresh=0.6,
            single_hand_tolerance_thresh=10,
            use_gesture=use_gesture
        )
        
        # Create renderer
        self.renderer = HandTrackerRenderer(tracker=self.tracker)
        
        # FPS counter for compatibility
        self.fps_counter = FPS()
        
        print(f"✓ RGB Hand Detector initialized ({resolution[0]}x{resolution[1]} @ {fps}fps)")
    
    def connect(self) -> bool:
        """Connect to camera (already done in __init__)"""
        return True
    
    def get_frame_and_hands(self):
        """
        Get frame and detected hands
        
        Returns:
            frame: RGB frame
            hands: List of detected hands
            depth: None (no depth in RGB mode)
        """
        self.fps_counter.update()
        
        frame, hands, bag = self.tracker.next_frame()
        
        if frame is None:
            return None, [], None
        
        # Resize if needed
        if frame.shape[:2][::-1] != self.resolution:
            frame = cv2.resize(frame, self.resolution)
        
        return frame, hands, None
    
    def close(self):
        """Close tracker and renderer"""
        self.tracker.exit()
        self.renderer.exit()
        print("RGB Hand Detector closed.")
```

### Step 2: Create 3-Area Gesture Detector

Create `src/gesture_oak/detection/three_area_detector.py`:

```python
#!/usr/bin/env python3
"""
3-Area Gesture Detector
Detects index finger (ONE) or fisted hand in 3 horizontal areas
"""
import numpy as np
import socket
import time
from enum import Enum, auto
from typing import Optional, Tuple


class GestureType(Enum):
    """Detected gesture types"""
    NONE = 0
    ONE = 1      # Index finger extended
    FIST = 2     # Fisted hand


class ThreeAreaDetector:
    """
    Detects index finger or fist in 3 horizontal areas
    
    Screen Layout:
    ┌─────────┬─────────┬─────────┐
    │ Area 1  │ Area 2  │ Area 3  │
    └─────────┴─────────┴─────────┘
    """
    
    # MediaPipe landmark indices
    WRIST = 0
    THUMB_TIP = 4
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
    MIDDLE_MCP, MIDDLE_TIP = 9, 12
    RING_MCP, RING_TIP = 13, 16
    PINKY_MCP, PINKY_TIP = 17, 20
    
    def __init__(self, udp_ip="192.168.0.10", udp_port=9000):
        """
        Initialize 3-area detector
        
        Args:
            udp_ip: UDP destination IP
            udp_port: UDP destination port
        """
        # UDP setup
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            print(f"✓ UDP enabled: {udp_ip}:{udp_port}")
        except Exception as e:
            print(f"⚠ UDP socket error: {e}")
            self.sock = None
        
        # State tracking
        self._last_sent_gesture = None
        self._last_sent_area = None
        self._current_gesture = GestureType.NONE
        self._current_area = 0
        
        # NO HAND delay
        self._no_hand_start_time = None
        self._no_hand_delay_seconds = 3.0
        self._no_hand_sent = False
        
        # Detection thresholds
        self.fist_threshold = 0.8  # Ratio for fist detection
        self.one_threshold = 1.2   # Ratio for ONE detection
    
    def update(self, hand, frame_shape) -> Tuple[GestureType, int]:
        """
        Update detector with new hand data
        
        Args:
            hand: Hand object with landmarks
            frame_shape: (height, width) of frame
            
        Returns:
            (gesture_type, area_number)
        """
        if hand is None or not hasattr(hand, 'landmarks') or hand.landmarks is None:
            # NO HAND detected
            if self._no_hand_start_time is None:
                self._no_hand_start_time = time.time()
                print("⏳ Hand lost, waiting 3 seconds...")
            
            elapsed = time.time() - self._no_hand_start_time
            if elapsed >= self._no_hand_delay_seconds and not self._no_hand_sent:
                self._send_udp(no_hand=True)
                self._no_hand_sent = True
            
            return GestureType.NONE, 0
        
        # HAND DETECTED - reset NO HAND timer
        if self._no_hand_start_time is not None:
            print("✓ Hand back in view")
        self._no_hand_start_time = None
        self._no_hand_sent = False
        
        # Extract landmarks
        lms = hand.landmarks
        if len(lms.shape) == 2 and lms.shape[1] >= 2:
            lms_2d = lms[:, :2]
        else:
            lms_2d = lms
        
        # Detect gesture type
        gesture = self._detect_gesture(lms_2d)
        self._current_gesture = gesture
        
        # Calculate reference point based on gesture
        if gesture == GestureType.ONE:
            # Use index fingertip
            ref_point = lms_2d[self.INDEX_TIP]
        elif gesture == GestureType.FIST:
            # Use palm center (average of MCP joints)
            palm_points = [lms_2d[self.INDEX_MCP], 
                          lms_2d[self.MIDDLE_MCP],
                          lms_2d[self.RING_MCP], 
                          lms_2d[self.PINKY_MCP]]
            ref_point = np.mean(palm_points, axis=0)
        else:
            ref_point = None
        
        # Determine area
        if ref_point is not None:
            area = self._point_to_area(ref_point, frame_shape)
            self._current_area = area
        else:
            area = 0
            self._current_area = 0
        
        # Send UDP messages
        self._send_udp()
        
        return gesture, area
    
    def _detect_gesture(self, lms: np.ndarray) -> GestureType:
        """
        Detect if hand is showing ONE (index extended) or FIST
        
        Args:
            lms: 21x2 array of landmark positions
            
        Returns:
            GestureType
        """
        wrist = lms[self.WRIST]
        
        # Helper function to check if finger is extended
        def is_extended(tip_idx, mcp_idx):
            tip_dist = np.linalg.norm(lms[tip_idx] - wrist)
            mcp_dist = np.linalg.norm(lms[mcp_idx] - wrist)
            if mcp_dist < 1e-6:
                return False
            return (tip_dist / mcp_dist) > self.one_threshold
        
        # Check each finger
        index_extended = is_extended(self.INDEX_TIP, self.INDEX_MCP)
        middle_extended = is_extended(self.MIDDLE_TIP, self.MIDDLE_MCP)
        ring_extended = is_extended(self.RING_TIP, self.RING_MCP)
        pinky_extended = is_extended(self.PINKY_TIP, self.PINKY_MCP)
        
        # ONE gesture: Only index extended, others not
        if index_extended and not middle_extended and not ring_extended and not pinky_extended:
            return GestureType.ONE
        
        # FIST: No fingers extended (or all very close)
        # Alternative check: all fingertips close to palm
        palm_center = np.mean([lms[self.INDEX_MCP], lms[self.MIDDLE_MCP], 
                              lms[self.RING_MCP], lms[self.PINKY_MCP]], axis=0)
        palm_size = np.linalg.norm(lms[self.INDEX_MCP] - lms[self.PINKY_MCP])
        
        tips_near_palm = 0
        for tip_idx in [self.INDEX_TIP, self.MIDDLE_TIP, self.RING_TIP, self.PINKY_TIP]:
            dist = np.linalg.norm(lms[tip_idx] - palm_center)
            if dist < palm_size * self.fist_threshold:
                tips_near_palm += 1
        
        if tips_near_palm >= 3:
            return GestureType.FIST
        
        return GestureType.NONE
    
    def _point_to_area(self, point, frame_shape) -> int:
        """
        Convert point to area number (1, 2, or 3)
        
        Args:
            point: (x, y) coordinates
            frame_shape: (height, width)
            
        Returns:
            Area number (1-3)
        """
        h, w = frame_shape[:2]
        x, y = point
        
        # Normalize x coordinate
        x_norm = x / w
        
        # Determine area (3 equal horizontal sections)
        if x_norm < 1.0 / 3.0:
            return 1
        elif x_norm < 2.0 / 3.0:
            return 2
        else:
            return 3
    
    def _send_udp(self, no_hand=False):
        """
        Send UDP messages:
        - "gesture/one" for ONE finger
        - "gesture/zero" for FIST
        - "area/3section/1-3" for area
        - "area/3section/0" for NO HAND
        """
        if self.sock is None:
            return
        
        try:
            if no_hand:
                msg = "area/3section/0"
                self.sock.sendto(msg.encode(), (self.udp_ip, self.udp_port))
                self._last_sent_area = msg
                self._last_sent_gesture = None
                print(f"📡 UDP: {msg}")
                return
            
            # Send gesture (only when it changes)
            if self._current_gesture == GestureType.ONE:
                gesture_msg = "gesture/one"
            elif self._current_gesture == GestureType.FIST:
                gesture_msg = "gesture/zero"
            else:
                gesture_msg = None
            
            if gesture_msg and gesture_msg != self._last_sent_gesture:
                self.sock.sendto(gesture_msg.encode(), (self.udp_ip, self.udp_port))
                self._last_sent_gesture = gesture_msg
                print(f"📡 UDP: {gesture_msg}")
            
            # Send area (only when it changes)
            if self._current_area > 0:
                area_msg = f"area/3section/{self._current_area}"
                if area_msg != self._last_sent_area:
                    self.sock.sendto(area_msg.encode(), (self.udp_ip, self.udp_port))
                    self._last_sent_area = area_msg
                    print(f"📡 UDP: {area_msg}")
        
        except Exception as e:
            print(f"⚠ UDP send error: {e}")
    
    def get_state_info(self):
        """Get current state information"""
        return {
            "gesture": self._current_gesture.name,
            "area": self._current_area
        }
    
    def reset(self):
        """Reset detector state"""
        self._current_gesture = GestureType.NONE
        self._current_area = 0
        self._no_hand_start_time = None
        self._no_hand_sent = False
        self._last_sent_gesture = None
        self._last_sent_area = None
        print("3-Area Detector reset!")
```

### Step 3: Create 3-Area Detection App

Create `src/gesture_oak/apps/three_area_app.py`:

```python
#!/usr/bin/env python3
"""
3-Area Detection Application
Detects index finger (ONE) or fist in 3 horizontal screen areas
"""
import os, sys, cv2, numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gesture_oak.detection.rgb_hand_detector import RGBHandDetector
from gesture_oak.detection.three_area_detector import ThreeAreaDetector, GestureType


def draw_hand_skeleton(img, hand):
    """Draw hand skeleton"""
    if not hasattr(hand, 'landmarks') or hand.landmarks is None:
        return
    
    lm = hand.landmarks
    if len(lm.shape) == 2 and lm.shape[1] >= 2:
        lm = lm[:, :2]
    
    # Hand skeleton connections
    connections = [
        (0,1),(1,2),(2,3),(3,4),  # Thumb
        (0,5),(5,6),(6,7),(7,8),  # Index
        (0,9),(9,10),(10,11),(11,12),  # Middle
        (0,13),(13,14),(14,15),(15,16),  # Ring
        (0,17),(17,18),(18,19),(19,20),  # Pinky
        (5,9),(9,13),(13,17)  # Palm
    ]
    
    # Draw lines
    for a, b in connections:
        pt1 = tuple(lm[a].astype(int))
        pt2 = tuple(lm[b].astype(int))
        cv2.line(img, pt1, pt2, (0, 255, 0), 2)
    
    # Draw points
    for i, pt in enumerate(lm):
        radius = 6 if i in [0, 4, 8, 12, 16, 20] else 4
        color = (0, 0, 255) if i in [0, 4, 8, 12, 16, 20] else (255, 255, 255)
        cv2.circle(img, tuple(pt.astype(int)), radius, color, -1)


def draw_area_grid(img, current_area, gesture_type):
    """
    Draw 3-area grid with highlighting
    
    Args:
        img: Image to draw on
        current_area: Currently active area (1-3)
        gesture_type: Current gesture type
    """
    h, w = img.shape[:2]
    
    # Area colors
    area_colors = {
        1: (0, 255, 255),    # Yellow
        2: (0, 255, 0),      # Green
        3: (0, 0, 255)       # Red
    }
    
    # Draw vertical dividing lines
    third = w // 3
    cv2.line(img, (third, 0), (third, h), (255, 255, 255), 3)
    cv2.line(img, (third * 2, 0), (third * 2, h), (255, 255, 255), 3)
    
    # Highlight active area
    if current_area > 0 and gesture_type != GestureType.NONE:
        overlay = img.copy()
        x_start = (current_area - 1) * third
        x_end = current_area * third
        color = area_colors.get(current_area, (255, 255, 255))
        cv2.rectangle(overlay, (x_start, 0), (x_end, h), color, -1)
        cv2.addWeighted(overlay, 0.2, img, 0.8, 0, img)
    
    # Draw area numbers
    for i in range(1, 4):
        x_pos = int((i - 0.5) * third)
        y_pos = h // 2
        color = area_colors.get(i, (255, 255, 255))
        
        # Large number
        cv2.putText(img, str(i), (x_pos - 30, y_pos),
                   cv2.FONT_HERSHEY_SIMPLEX, 3, color, 6)
        
        # Thicker outline if active
        if i == current_area and gesture_type != GestureType.NONE:
            x_start = (i - 1) * third
            x_end = i * third
            cv2.rectangle(img, (x_start, 0), (x_end, h), color, 5)


def main():
    print("="*70)
    print("3-AREA GESTURE DETECTION")
    print("="*70)
    print("Detects: ONE (index finger) or FIST")
    print("Screen divided into 3 areas:")
    print("┌─────────┬─────────┬─────────┐")
    print("│ Area 1  │ Area 2  │ Area 3  │")
    print("└─────────┴─────────┴─────────┘")
    print()
    print("UDP Messages:")
    print("  - gesture/one  : Index finger extended")
    print("  - gesture/zero : Fisted hand")
    print("  - area/3section/1-3 : Area number")
    print("  - area/3section/0   : No hand")
    print()
    print("Controls: q=Quit | r=Reset | s=Save")
    print("="*70)
    
    # Initialize detector (RGB mode)
    hd = RGBHandDetector(fps=30, resolution=(1280, 720), pd_score_thresh=0.6)
    if not hd.connect():
        print("❌ Failed to connect!")
        return
    
    # Initialize 3-area detector
    detector = ThreeAreaDetector()
    print("✓ Ready!")
    
    saved = 0
    
    try:
        while True:
            # Get frame and hands
            frame, hands, _ = hd.get_frame_and_hands()
            if frame is None:
                continue
            
            # Mirror frame for natural interaction
            frame = cv2.flip(frame, 1)
            h, w = frame.shape[:2]
            
            # Mirror landmarks
            for hand in hands:
                if hasattr(hand, 'landmarks') and hand.landmarks is not None:
                    hand.landmarks[:, 0] = w - hand.landmarks[:, 0]
            
            disp = frame.copy()
            
            # Process first hand
            if hands:
                hand = hands[0]
                gesture, area = detector.update(hand, frame.shape[:2])
                
                # Draw area grid
                draw_area_grid(disp, area, gesture)
                
                # Draw hand skeleton on top
                draw_hand_skeleton(disp, hand)
                
                # Info panel
                overlay = disp.copy()
                cv2.rectangle(overlay, (10, 10), (450, 150), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, disp, 0.3, 0, disp)
                
                y = 45
                
                # Gesture
                if gesture == GestureType.ONE:
                    txt, col = "GESTURE: ONE ☝", (0, 255, 255)
                elif gesture == GestureType.FIST:
                    txt, col = "GESTURE: FIST ✊", (0, 0, 255)
                else:
                    txt, col = "GESTURE: NONE", (128, 128, 128)
                
                cv2.putText(disp, txt, (20, y), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, col, 2)
                y += 50
                
                # Area
                if area > 0:
                    area_colors = {1: (0, 255, 255), 2: (0, 255, 0), 3: (0, 0, 255)}
                    cv2.putText(disp, f"AREA: {area}", (20, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, 
                               area_colors.get(area, (255, 255, 255)), 2)
                else:
                    cv2.putText(disp, "AREA: -", (20, y),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.9, (128, 128, 128), 2)
                
            else:
                # No hand
                detector.update(None, frame.shape[:2])
                draw_area_grid(disp, 0, GestureType.NONE)
                
                cv2.putText(disp, "SHOW YOUR HAND", (w//2 - 200, h//2),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            
            # FPS
            fps = hd.fps_counter.get_global()
            cv2.putText(disp, f"FPS: {fps:.1f}", (w - 150, 35),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Show
            cv2.imshow("3-Area Detection", disp)
            
            # Keys
            k = cv2.waitKey(1) & 0xFF
            if k == ord('q'):
                break
            elif k == ord('r'):
                detector.reset()
            elif k == ord('s'):
                fname = f"3area_{saved:04d}.jpg"
                cv2.imwrite(fname, disp)
                print(f"Saved {fname}")
                saved += 1
    
    except KeyboardInterrupt:
        print("\nStopped")
    finally:
        hd.close()
        cv2.destroyAllWindows()
        print("Done!")


if __name__ == "__main__":
    main()
```

### Step 4: Update Main Menu

Update `main.py` to add new options:

```python
#!/usr/bin/env python3
"""
TG_25_GestureOAK-D Main Menu
Updated with RGB and 3-Area Detection
"""
import sys
from pathlib import Path

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
    print("7. Run wrist rotation with RGB (NEW)")
    print("8. Exit")
    print("="*60)


def main():
    """Main menu loop"""
    while True:
        print_menu()
        choice = input("Enter your choice (1-8): ").strip()
        
        if choice == '1':
            print("\nTesting camera connection...")
            from gesture_oak.core.oak_camera import test_camera_connection
            test_camera_connection()
        
        elif choice == '2':
            print("\nStarting hand tracking application...")
            from gesture_oak.apps.hand_tracking_app import main as hand_main
            hand_main()
        
        elif choice == '3':
            print("\nStarting swipe detection application...")
            from gesture_oak.apps.swipe_detection_app import main as swipe_main
            swipe_main()
        
        elif choice == '4':
            print("\nStarting motion-based swipe application...")
            from gesture_oak.apps.motion_swipe_app import main as motion_main
            motion_main()
        
        elif choice == '5':
            print("\nStarting wrist rotation detection...")
            from gesture_oak.apps.wrist_rotation_app import main as rotation_main
            rotation_main()
        
        elif choice == '6':
            print("\nStarting 3-area detection (RGB mode)...")
            from gesture_oak.apps.three_area_app import main as area_main
            area_main()
        
        elif choice == '7':
            print("\nStarting wrist rotation with RGB...")
            from gesture_oak.apps.wrist_rotation_rgb_app import main as wrist_rgb_main
            wrist_rgb_main()
        
        elif choice == '8':
            print("\nExiting...")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-8.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
```

## Part 4: Integration Steps

### Priority Order

1. **Test RGB detector separately first**
   - Create and test `rgb_hand_detector.py`
   - Verify it works with RGB camera
   - Check HandTracker compatibility

2. **Test 3-area detection**
   - Create `three_area_detector.py`
   - Create `three_area_app.py`
   - Test gesture detection (ONE vs FIST)
   - Test area division and UDP messages

3. **Create RGB version of wrist rotation**
   - Copy `wrist_rotation_app.py` to `wrist_rotation_rgb_app.py`
   - Replace `HandDetector` with `RGBHandDetector`
   - Test all features work with RGB

4. **Update all existing apps**
   - Add RGB camera option to each app
   - Keep IR version as default for dark environments
   - Add menu option to switch camera modes

## Part 5: Testing Checklist

### RGB Hand Detector
- [ ] RGB camera initializes correctly
- [ ] Hand landmarks detected accurately
- [ ] FPS is acceptable (>15 fps)
- [ ] Multiple hands can be detected
- [ ] Gesture recognition works

### 3-Area Detection
- [ ] ONE gesture detected correctly
- [ ] FIST gesture detected correctly
- [ ] Area boundaries correct (33.33% each)
- [ ] Reference point calculation correct
- [ ] UDP messages sent properly
- [ ] Visual feedback clear

### Wrist Rotation (RGB)
- [ ] All 4 positions detected
- [ ] FIST/OPEN states work
- [ ] Angle calculation accurate
- [ ] UDP messages correct
- [ ] Visual zones display properly

### Integration
- [ ] All apps accessible from menu
- [ ] Switching between apps works
- [ ] No conflicts between features
- [ ] Documentation updated
- [ ] README reflects new features

## Part 6: UDP Message Summary

### Original Features
- `gesture/five` - Open hand
- `gesture/zero` - Fisted hand
- `area/menu/1-4` - Wrist rotation positions
- `area/menu/0` - No hand

### New 3-Area Feature
- `gesture/one` - Index finger extended
- `gesture/zero` - Fisted hand (reused)
- `area/3section/1-3` - Area numbers
- `area/3section/0` - No hand

## Part 7: File Structure Summary

```
wrist_rotation/
├── main.py (UPDATED - new menu options)
├── src/
│   └── gesture_oak/
│       ├── detection/
│       │   ├── HandTracker.py (Nakakawa-san's)
│       │   ├── HandTrackerRenderer.py (Nakakawa-san's)
│       │   ├── test_hand_data.py (Nakakawa-san's reference)
│       │   ├── hand_detector.py (existing IR)
│       │   ├── rgb_hand_detector.py (NEW - RGB wrapper)
│       │   ├── wrist_rotation_detector.py (existing)
│       │   └── three_area_detector.py (NEW)
│       └── apps/
│           ├── wrist_rotation_app.py (existing IR)
│           ├── wrist_rotation_rgb_app.py (NEW - RGB version)
│           └── three_area_app.py (NEW)
└── README.md (UPDATE with new features)
```

## Conclusion

This implementation:
1. ✅ Integrates Nakakawa-san's RGB HandTracker approach
2. ✅ Maintains compatibility with existing IR-based features
3. ✅ Adds new 3-area detection feature
4. ✅ Provides clean abstraction for camera switching
5. ✅ Follows existing code patterns and style
6. ✅ Includes comprehensive testing checklist
