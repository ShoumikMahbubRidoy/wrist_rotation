# src/gesture_oak/detection/wrist_rotation_detector.py
"""
FIXED Wrist Rotation Detector
- Better fist detection (ANY finger open = OPEN)
- Simplified position ranges (no dead zone)
- Writes to result.txt
"""
from enum import Enum, auto
from collections import deque
from typing import Optional, Tuple, List
import numpy as np
import math

__all__ = ["WristRotationDetector", "HandState", "RotationPosition", "__version__"]
__version__ = "0.4.0"

# MediaPipe Hands landmark indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

class HandState(Enum):
    UNKNOWN = auto()
    FISTED = auto()
    OPEN = auto()

class RotationPosition(Enum):
    NONE = 0
    LEFT_FAR = 4    # 0° to 60°
    LEFT_NEAR = 3   # 60° to 90°
    RIGHT_NEAR = 2  # 90° to 120°
    RIGHT_FAR = 1   # 120° to 180°

def _distance(p1, p2):
    """Euclidean distance"""
    return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def _median(seq: List[float]):
    if not seq:
        return None
    return float(np.median(np.asarray(seq, dtype=float)))

class WristRotationDetector:
    """
    FIXED Wrist Rotation Detector
    Position mapping (NO DEAD ZONE):
    - Position 1: 0° to 60°
    - Position 2: 60° to 90°
    - Position 3: 90° to 120°
    - Position 4: 120° to 180°
    """

    def __init__(
        self,
        buffer_size: int = 10,
        angle_smoothing: int = 5,
        ema_alpha: float = 0.3,
        open_frames: int = 2,
        fist_frames: int = 3,
        min_lm_score: float = 0.3,
        max_angle_jump: float = 40.0,
        neutral_calibration_frames: int = 10,
        finger_extension_threshold: float = 0.65,  # INCREASED for better fist detection
    ):
        # Configuration
        self.buffer_size = int(buffer_size)
        self.angle_smoothing = max(1, int(angle_smoothing))
        self.ema_alpha = float(ema_alpha)
        self.open_frames_req = int(open_frames)
        self.fist_frames_req = int(fist_frames)
        self.min_lm_score = float(min_lm_score)
        self.max_angle_jump = float(max_angle_jump)
        self.finger_extension_threshold = float(finger_extension_threshold)

        # Buffers
        self.angles = deque(maxlen=self.buffer_size)
        self.angles_raw = deque(maxlen=self.buffer_size)

        # State
        self.state = HandState.UNKNOWN
        self._open_streak = 0
        self._fist_streak = 0

        # Smoothing
        self._ema_angle: Optional[float] = None

        # Calibration
        self._need_calibration = True
        self._calib_left = int(neutral_calibration_frames)
        self._neutral_pool: List[float] = []

        # Current state
        self._last_angle: Optional[float] = None
        self._last_position: RotationPosition = RotationPosition.NONE
        self._selected_position: int = 0  # Position when fist

        # Statistics
        self._change_count: int = 0
        
        # Debug
        self._finger_states = {
            'thumb': False,
            'index': False,
            'middle': False,
            'ring': False,
            'pinky': False
        }
        
        # Output file
        self.result_file = "result.txt"

    def update(self, hand) -> Tuple[RotationPosition, Optional[float], HandState]:
        """
        Main update function
        Returns: (RotationPosition, angle_degrees|None, HandState)
        """
        # Extract landmarks
        lms, lm_score = self._extract_landmarks(hand)
        if lms is None:
            self._write_result("NO_HAND", 0, 0)
            return RotationPosition.NONE, None, self.state

        # Check confidence
        if float(lm_score) < self.min_lm_score:
            return self._finalize(None)

        # Detect hand state (FISTED or OPEN)
        measured_state = self._detect_hand_state_simple(lms)
        self._apply_hysteresis(measured_state)

        # Calculate wrist angle
        angle_raw = self._compute_wrist_angle(lms)
        if angle_raw is None:
            return self._finalize(None)

        # Spike rejection
        if self.angles and abs(angle_raw - self.angles[-1]) > self.max_angle_jump:
            angle_raw = self.angles[-1]

        self.angles_raw.append(angle_raw)

        # Smooth angle
        smoothed = _median(list(self.angles_raw)[-self.angle_smoothing:]) or angle_raw
        if self._ema_angle is None:
            self._ema_angle = smoothed
        else:
            self._ema_angle = self.ema_alpha * smoothed + (1 - self.ema_alpha) * self._ema_angle
        
        angle = float(np.clip(self._ema_angle, 0.0, 180.0))

        # Neutral calibration
        if self._need_calibration:
            self._neutral_pool.append(angle)
            self._calib_left -= 1
            if self._calib_left <= 0:
                neutral = _median(self._neutral_pool) or angle
                shift = 90.0 - neutral
                self.angles_raw = deque([a + shift for a in self.angles_raw], maxlen=self.buffer_size)
                self._ema_angle = (self._ema_angle + shift) if self._ema_angle is not None else None
                angle = float(np.clip((angle + shift), 0.0, 180.0))
                self._need_calibration = False

        self.angles.append(angle)

        # Map angle to position
        prev_pos = self._last_position
        
        if self.state == HandState.OPEN:
            # Hand is OPEN - update position dynamically
            pos = self._angle_to_position(angle)
            self._selected_position = pos.value  # Save current position
        else:
            # Hand is FISTED - keep selected position
            pos = RotationPosition.NONE

        # Count changes
        if self.state == HandState.OPEN and pos != prev_pos:
            if pos != RotationPosition.NONE and prev_pos != RotationPosition.NONE:
                self._change_count += 1

        # Save state
        self._last_position = pos
        self._last_angle = angle

        # Write to result.txt
        self._write_result(self.state.name, pos.value, angle)

        return pos, angle, self.state

    def _detect_hand_state_simple(self, lms: np.ndarray) -> HandState:
        """
        FIXED: Better fist detection
        Need at least 2 fingers extended to be OPEN
        0-1 fingers = FISTED
        """
        wrist = lms[WRIST]
        
        def is_finger_extended(tip_idx, mcp_idx):
            tip = lms[tip_idx]
            mcp = lms[mcp_idx]
            
            tip_dist = _distance(wrist, tip)
            mcp_dist = _distance(wrist, mcp)
            
            if mcp_dist < 1e-6:
                return False
            
            ratio = tip_dist / mcp_dist
            # INCREASED threshold for stricter detection
            return ratio > 0.65  # Was 0.45, now 0.65 for better fist detection
        
        # Check all 5 fingers
        thumb_extended = is_finger_extended(THUMB_TIP, THUMB_MCP)
        index_extended = is_finger_extended(INDEX_TIP, INDEX_MCP)
        middle_extended = is_finger_extended(MIDDLE_TIP, MIDDLE_MCP)
        ring_extended = is_finger_extended(RING_TIP, RING_MCP)
        pinky_extended = is_finger_extended(PINKY_TIP, PINKY_MCP)
        
        # Store for debugging
        self._finger_states = {
            'thumb': thumb_extended,
            'index': index_extended,
            'middle': middle_extended,
            'ring': ring_extended,
            'pinky': pinky_extended
        }
        
        # Count extended fingers
        extended_count = sum([thumb_extended, index_extended, middle_extended, 
                             ring_extended, pinky_extended])
        
        # Need at least 2 fingers to be considered OPEN
        return HandState.OPEN if extended_count >= 2 else HandState.FISTED

    def _apply_hysteresis(self, measured: HandState):
        """Apply hysteresis"""
        if measured == HandState.OPEN:
            self._open_streak += 1
            self._fist_streak = 0
        else:
            self._fist_streak += 1
            self._open_streak = 0

        if self.state in (HandState.UNKNOWN, HandState.FISTED):
            if self._open_streak >= self.open_frames_req:
                self.state = HandState.OPEN

        if self.state in (HandState.UNKNOWN, HandState.OPEN):
            if self._fist_streak >= self.fist_frames_req:
                self.state = HandState.FISTED

    def _compute_wrist_angle(self, lms: np.ndarray) -> Optional[float]:
        """Calculate wrist rotation angle"""
        wrist = lms[WRIST]
        middle_mcp = lms[MIDDLE_MCP]
        
        vec = middle_mcp - wrist
        if np.linalg.norm(vec) < 1e-3:
            return None
        
        angle = math.degrees(math.atan2(-vec[1], vec[0]))
        angle = abs(angle) % 360.0
        if angle > 180.0:
            angle = 360.0 - angle
        
        return float(angle)

    def _angle_to_position(self, angle: float) -> RotationPosition:
        """
        Map angle to position (NO DEAD ZONE)
        - Position 1: 0° to 60°
        - Position 2: 60° to 90°
        - Position 3: 90° to 120°
        - Position 4: 120° to 180°
        """
        if angle < 60.0:
            return RotationPosition.LEFT_FAR
        elif angle < 90.0:
            return RotationPosition.LEFT_NEAR
        elif angle < 120.0:
            return RotationPosition.RIGHT_NEAR
        else:
            return RotationPosition.RIGHT_FAR

    def _write_result(self, state_name: str, position: int, angle: float):
        """Write result to result.txt"""
        try:
            with open(self.result_file, 'w') as f:
                f.write(f"State: {state_name}\n")
                if self.state == HandState.FISTED:
                    f.write(f"Selected Position: {self._selected_position}\n")
                else:
                    f.write(f"Current Position: {position}\n")
                f.write(f"Angle: {angle:.1f}°\n")
        except Exception as e:
            pass  # Ignore file write errors

    def reset(self):
        """Reset all state"""
        self.angles.clear()
        self.angles_raw.clear()
        self._ema_angle = None
        self._neutral_pool.clear()
        self._need_calibration = True
        self._calib_left = 10
        self._open_streak = 0
        self._fist_streak = 0
        self.state = HandState.UNKNOWN
        self._last_angle = None
        self._last_position = RotationPosition.NONE
        self._selected_position = 0
        self._change_count = 0
        self._finger_states = {k: False for k in self._finger_states}

    def get_state_info(self):
        """Return state dictionary"""
        state_name = self.state.name
        return {
            "state": state_name,
            "hand_state": state_name,
            "angle": self._last_angle,
            "position": int(self._last_position.value),
            "selected_position": self._selected_position,
            "position_name": self._position_name(self._last_position),
            "calibrated": (not self._need_calibration),
            "open_streak": self._open_streak,
            "fist_streak": self._fist_streak,
            "total_changes": int(self._change_count),
            "finger_states": self._finger_states.copy(),
        }

    def _extract_landmarks(self, hand):
        """Extract landmarks from hand object"""
        lms = None
        lm_score = 1.0

        if isinstance(hand, dict):
            lms = hand.get('landmarks')
            lm_score = float(hand.get('lm_score', 1.0))
        else:
            if hasattr(hand, 'landmarks'):
                lms = getattr(hand, 'landmarks')
            elif hasattr(hand, 'lm'):
                lms = getattr(hand, 'lm')
            
            if hasattr(hand, 'lm_score'):
                lm_score = float(getattr(hand, 'lm_score'))
            elif hasattr(hand, 'score'):
                lm_score = float(getattr(hand, 'score'))

        if lms is None:
            return None, 0.0

        lms = np.asarray(lms, dtype=float)
        if lms.shape == (21, 3):
            lms = lms[:, :2]
        if lms.shape != (21, 2):
            return None, 0.0

        return lms, lm_score

    def _position_name(self, pos: RotationPosition) -> str:
        """Get position name"""
        mapping = {
            RotationPosition.NONE: "NONE",
            RotationPosition.LEFT_FAR: "Position 1 (LEFT)",
            RotationPosition.LEFT_NEAR: "Position 2 (LEFT-CENTER)",
            RotationPosition.RIGHT_NEAR: "Position 3 (RIGHT-CENTER)",
            RotationPosition.RIGHT_FAR: "Position 4 (RIGHT)",
        }
        return mapping.get(pos, "NONE")

    def _finalize(self, angle: Optional[float]) -> Tuple[RotationPosition, Optional[float], HandState]:
        """Finalize state"""
        if angle is None and self.angles:
            angle = self.angles[-1]
        pos = self._angle_to_position(angle) if (angle is not None and self.state == HandState.OPEN) else RotationPosition.NONE
        return pos, angle, self.state