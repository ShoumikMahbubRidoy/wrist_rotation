# src/gesture_oak/detection/wrist_rotation_detector.py
"""
FIXED: Better fist detection + Original working rotation logic
"""
from enum import Enum, auto
from collections import deque
from typing import Optional, Tuple, List
import numpy as np
import math

__all__ = ["WristRotationDetector", "HandState", "RotationPosition", "__version__"]
__version__ = "0.3.1-fixed"

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
    """
    ORIGINAL MAPPING - NO DEAD ZONE
    Position 1: 0° to 60° (left far)
    Position 2: 60° to 90° (left near)
    Position 3: 90° to 120° (right near)
    Position 4: 120° to 180° (right far)
    """
    NONE = 0
    LEFT_FAR = 1
    LEFT_NEAR = 2
    RIGHT_NEAR = 3
    RIGHT_FAR = 4

# ========== IMPROVED FIST DETECTION HELPERS ==========

def _distance(p1, p2):
    """Euclidean distance between two points"""
    return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def _median(seq: List[float]):
    if not seq:
        return None
    return float(np.median(np.asarray(seq, dtype=float)))

# ========== MAIN DETECTOR ==========

class WristRotationDetector:
    """
    Wrist Rotation Detector
    - IMPROVED fist detection (distance-based method)
    - ORIGINAL rotation logic (no dead zone)
    - Simple and reliable
    """

    def __init__(
        self,
        buffer_size: int = 15,
        angle_smoothing: int = 7,
        ema_alpha: float = 0.35,
        open_frames: int = 3,
        fist_frames: int = 5,
        min_lm_score: float = 0.3,
        max_angle_jump: float = 40.0,
        neutral_calibration_frames: int = 12,
        # NEW: Fist detection threshold
        curl_threshold: float = 0.70,  # Higher = stricter (fingers must be MORE curled for FISTED)
    ):
        self.buffer_size = int(buffer_size)
        self.angle_smoothing = max(1, int(angle_smoothing))
        self.ema_alpha = float(ema_alpha)
        self.open_frames_req = int(open_frames)
        self.fist_frames_req = int(fist_frames)
        self.min_lm_score = float(min_lm_score)
        self.max_angle_jump = float(max_angle_jump)
        self.curl_threshold = float(curl_threshold)  # NEW

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

        # Statistics
        self._change_count: int = 0
        
        # Debug
        self._finger_ratios = {
            'thumb': 0.0,
            'index': 0.0,
            'middle': 0.0,
            'ring': 0.0,
            'pinky': 0.0
        }

    # ============= PUBLIC API =============

    def update(self, hand) -> Tuple[RotationPosition, Optional[float], HandState]:
        """
        Update detector with new hand detection
        Returns: (RotationPosition, angle|None, HandState)
        """
        # 1) Extract landmarks
        lms, lm_score = self._extract_landmarks(hand)
        if lms is None:
            return RotationPosition.NONE, None, self.state

        # 2) Check confidence
        if float(lm_score) < self.min_lm_score:
            return self._finalize(None)

        # 3) IMPROVED fist detection
        measured_state = self._detect_fist_improved(lms)
        self._apply_hysteresis(measured_state)

        # 4) Calculate angle
        angle_raw = self._compute_wrist_angle(lms)
        if angle_raw is None:
            return self._finalize(None)

        # 5) Spike rejection
        if self.angles and abs(angle_raw - self.angles[-1]) > self.max_angle_jump:
            angle_raw = self.angles[-1]

        self.angles_raw.append(angle_raw)

        # 6) Smooth angle
        smoothed = _median(list(self.angles_raw)[-self.angle_smoothing:]) or angle_raw
        if self._ema_angle is None:
            self._ema_angle = smoothed
        else:
            self._ema_angle = self.ema_alpha * smoothed + (1 - self.ema_alpha) * self._ema_angle
        
        angle = float(np.clip(self._ema_angle, 0.0, 180.0))

        # 7) Calibration
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

        # 8) ORIGINAL position mapping (NO DEAD ZONE)
        prev_pos = self._last_position
        pos = self._angle_to_position_original(angle) if self.state == HandState.OPEN else RotationPosition.NONE

        # 9) Count changes
        if self.state == HandState.OPEN and pos != prev_pos:
            if pos != RotationPosition.NONE:
                if prev_pos == RotationPosition.NONE:
                    self._change_count += 1  # First valid position
                elif prev_pos != RotationPosition.NONE:
                    self._change_count += 1  # Position changed

        # 10) Save state
        self._last_position = pos
        self._last_angle = angle

        return pos, angle, self.state

    def reset(self):
        """Reset all state"""
        self.angles.clear()
        self.angles_raw.clear()
        self._ema_angle = None
        self._neutral_pool.clear()
        self._need_calibration = True
        self._calib_left = 12
        self._open_streak = 0
        self._fist_streak = 0
        self.state = HandState.UNKNOWN
        self._last_angle = None
        self._last_position = RotationPosition.NONE
        self._change_count = 0
        self._finger_ratios = {k: 0.0 for k in self._finger_ratios}

    def get_state_info(self):
        """Return state for UI"""
        state_name = self.state.name
        return {
            "state": state_name,
            "hand_state": state_name,
            "angle": self._last_angle,
            "position": int(self._last_position.value),
            "position_name": self._position_name(self._last_position),
            "calibrated": (not self._need_calibration),
            "open_streak": self._open_streak,
            "fist_streak": self._fist_streak,
            "total_changes": int(self._change_count),
            "finger_ratios": self._finger_ratios.copy(),  # Debug
        }

    # ============= INTERNAL METHODS =============

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

    def _detect_fist_improved(self, lms: np.ndarray) -> HandState:
        """
        IMPROVED fist detection using distance ratio method
        
        Logic:
        - Calculate ratio: (tip to wrist distance) / (MCP to wrist distance)
        - If ratio > curl_threshold → finger is EXTENDED (curled finger has lower ratio)
        - ANY finger extended → OPEN
        - ALL fingers curled → FISTED
        
        Higher curl_threshold = stricter (need more extension to be OPEN)
        """
        wrist = lms[WRIST]
        
        def get_curl_ratio(tip_idx, mcp_idx):
            """
            Returns ratio of tip-to-wrist vs mcp-to-wrist distance
            Extended finger: ratio > 1.5
            Curled finger: ratio < 1.2
            """
            tip = lms[tip_idx]
            mcp = lms[mcp_idx]
            
            tip_dist = _distance(wrist, tip)
            mcp_dist = _distance(wrist, mcp)
            
            if mcp_dist < 1e-6:
                return 0.0
            
            return tip_dist / mcp_dist
        
        # Calculate curl ratio for each finger
        thumb_ratio = get_curl_ratio(THUMB_TIP, THUMB_MCP)
        index_ratio = get_curl_ratio(INDEX_TIP, INDEX_MCP)
        middle_ratio = get_curl_ratio(MIDDLE_TIP, MIDDLE_MCP)
        ring_ratio = get_curl_ratio(RING_TIP, RING_MCP)
        pinky_ratio = get_curl_ratio(PINKY_TIP, PINKY_MCP)
        
        # Store for debug
        self._finger_ratios = {
            'thumb': round(thumb_ratio, 2),
            'index': round(index_ratio, 2),
            'middle': round(middle_ratio, 2),
            'ring': round(ring_ratio, 2),
            'pinky': round(pinky_ratio, 2)
        }
        
        # Check if fingers are extended
        # Higher ratio = more extended
        thumb_extended = thumb_ratio > self.curl_threshold
        index_extended = index_ratio > self.curl_threshold
        middle_extended = middle_ratio > self.curl_threshold
        ring_extended = ring_ratio > self.curl_threshold
        pinky_extended = pinky_ratio > self.curl_threshold
        
        # ANY finger extended = OPEN
        any_extended = (thumb_extended or index_extended or middle_extended or 
                       ring_extended or pinky_extended)
        
        return HandState.OPEN if any_extended else HandState.FISTED

    def _apply_hysteresis(self, measured: HandState):
        """Apply hysteresis to prevent rapid state changes"""
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

    def _angle_to_position_original(self, angle: float) -> RotationPosition:
        """
        ORIGINAL position mapping - NO DEAD ZONE
        
        Position 1: 0° to 60° (left far)
        Position 2: 60° to 90° (left near)
        Position 3: 90° to 120° (right near)
        Position 4: 120° to 180° (right far)
        """
        if angle < 60.0:
            return RotationPosition.LEFT_FAR
        elif angle < 90.0:
            return RotationPosition.LEFT_NEAR
        elif angle < 120.0:
            return RotationPosition.RIGHT_NEAR
        else:
            return RotationPosition.RIGHT_FAR

    def _position_name(self, pos: RotationPosition) -> str:
        """Get position name"""
        mapping = {
            RotationPosition.NONE: "NONE",
            RotationPosition.LEFT_FAR: "Position 1 (LEFT FAR)",
            RotationPosition.LEFT_NEAR: "Position 2 (LEFT NEAR)",
            RotationPosition.RIGHT_NEAR: "Position 3 (RIGHT NEAR)",
            RotationPosition.RIGHT_FAR: "Position 4 (RIGHT FAR)",
        }
        return mapping.get(pos, "NONE")

    def _finalize(self, angle: Optional[float]) -> Tuple[RotationPosition, Optional[float], HandState]:
        """Finalize when no valid angle"""
        if angle is None and self.angles:
            angle = self.angles[-1]
        pos = self._angle_to_position_original(angle) if (angle is not None and self.state == HandState.OPEN) else RotationPosition.NONE
        return pos, angle, self.state