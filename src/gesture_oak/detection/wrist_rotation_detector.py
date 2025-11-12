"""
WRIST ROTATION DETECTOR + UDP v2.7
- Sends:
    "gesture/five"   when OPEN
    "gesture/zero"   when FISTED
    "area/menu/1-4"  current position
    "area/menu/0"    NO HAND
- Robust NO_HAND via:
    * Watchdog timeout (stale frames)
    * Tiny/invalid palm guard
"""

import math, socket, time
import numpy as np
from enum import Enum, auto
from collections import deque
from typing import Optional, Tuple, List

__all__ = ["WristRotationDetector", "HandState", "RotationPosition", "__version__", "WRIST"]
__version__ = "2.7.0"

# MediaPipe indices
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

class HandState(Enum):
    UNKNOWN = auto()
    FISTED  = auto()
    OPEN    = auto()

class RotationPosition(Enum):
    NONE       = 0
    LEFT_FAR   = 1
    LEFT_NEAR  = 2
    RIGHT_NEAR = 3
    RIGHT_FAR  = 4

def _dist(a, b): return float(np.linalg.norm(a - b))
def _median(seq): return float(np.median(np.asarray(seq))) if seq else None

class WristRotationDetector:
    def __init__(self, udp_ip="192.168.0.10", udp_port=9000, min_confidence=0.3,
                 min_palm_px=25.0, stale_timeout_ms=400):
        # Config
        self.min_confidence = float(min_confidence)
        self.min_palm_px = float(min_palm_px)              # guard for tiny ghost hands
        self.stale_timeout_ms = int(stale_timeout_ms)      # watchdog

        # Angle smoothing
        self.angle_buffer = deque(maxlen=5)
        self._neutral_angle = None
        self._calib_samples = []
        self._calibrated = False

        # State
        self.state = HandState.UNKNOWN
        self._open_streak = 0
        self._fist_streak = 0
        self._current_angle: Optional[float] = None
        self._current_position: RotationPosition = RotationPosition.NONE
        self._finger_states = {}
        self._hand_detected = False

        # Last-seen watchdog
        self._last_seen_ms = 0

        # Output
        self.result_file = "result.txt"

        # UDP
        self.udp_ip = udp_ip
        self.udp_port = udp_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self._last_sent_state = None
        self._last_sent_pos = None

    # ---------- public ----------
    def heartbeat(self):
        """Call this every loop. If no valid hand for timeout, force NO_HAND."""
        now = int(time.time() * 1000)
        if self._hand_detected and (now - self._last_seen_ms) > self.stale_timeout_ms:
            self.no_hand()

    def no_hand(self):
        self._hand_detected = False
        self.state = HandState.UNKNOWN
        self._current_position = RotationPosition.NONE
        self._current_angle = None
        self._write_result("NO_HAND", 0, 0.0)
        self._send_udp(no_hand=True)
        print("🚫 No hand detected -> area/menu/0")

    def update(self, hand) -> Tuple[RotationPosition, Optional[float], HandState]:
        lms, conf = self._extract_landmarks(hand)
        if (lms is None) or (conf < self.min_confidence):
            self.no_hand()
            return RotationPosition.NONE, None, HandState.UNKNOWN

        # Tiny/ghost hand guard (reject if palm too small)
        palm_w = _dist(lms[INDEX_MCP], lms[PINKY_MCP])
        if not np.isfinite(palm_w) or palm_w < self.min_palm_px:
            self.no_hand()
            return RotationPosition.NONE, None, HandState.UNKNOWN

        # Mark seen
        self._hand_detected = True
        self._last_seen_ms = int(time.time() * 1000)

        # 1) Hand state (for display)
        measured = self._detect_hand_state(lms, palm_w)
        self._update_state(measured)

        # 2) Angle → position (always)
        raw_angle = self._calc_angle(lms)
        if raw_angle is None:
            self.no_hand()
            return RotationPosition.NONE, None, HandState.UNKNOWN

        if not self._calibrated:
            self._calib_samples.append(raw_angle)
            if len(self._calib_samples) >= 10:
                self._neutral_angle = _median(self._calib_samples)
                self._calibrated = True
                print(f"✓ Calibrated neutral angle: {self._neutral_angle:.1f}°")

        if self._neutral_angle is not None:
            angle = float(np.clip(raw_angle + (90.0 - self._neutral_angle), 0.0, 180.0))
        else:
            angle = raw_angle

        self.angle_buffer.append(angle)
        smoothed = _median(self.angle_buffer) or angle
        self._current_angle = smoothed
        self._current_position = self._angle_to_position(smoothed)

        # IO
        self._write_result(self.state.name, self._current_position.value, smoothed)
        self._send_udp()
        print(f"🖐 State: {self.state.name} | Pos: {self._current_position.value} | Angle: {smoothed:.1f}°")
        return self._current_position, smoothed, self.state

    # ---------- internals ----------
    def _detect_hand_state(self, lms: np.ndarray, palm_w: float) -> HandState:
        wrist = lms[WRIST]

        def extended(tip, mcp):
            return _dist(wrist, lms[tip]) / max(_dist(wrist, lms[mcp]), 1e-6) > 1.35

        idx = extended(INDEX_TIP, INDEX_MCP)
        mid = extended(MIDDLE_TIP, MIDDLE_MCP)
        rng = extended(RING_TIP, RING_MCP)
        pky = extended(PINKY_TIP, PINKY_MCP)
        thumb = extended(THUMB_TIP, THUMB_MCP)

        self._finger_states = {
            "thumb": thumb, "index": idx, "middle": mid, "ring": rng, "pinky": pky
        }
        extended_count = sum(self._finger_states.values())

        tips = [lms[INDEX_TIP], lms[MIDDLE_TIP], lms[RING_TIP], lms[PINKY_TIP]]
        total_spread = sum(_dist(tips[i], tips[i+1]) for i in range(3))
        spread_ratio = total_spread / max(palm_w, 1.0)

        return HandState.FISTED if (extended_count <= 1 or spread_ratio < 0.65) else HandState.OPEN

    def _update_state(self, measured: HandState):
        if measured == HandState.OPEN:
            self._open_streak += 1; self._fist_streak = 0
        else:
            self._fist_streak += 1; self._open_streak = 0

        if self.state in (HandState.UNKNOWN, HandState.FISTED) and self._open_streak >= 1:
            self.state = HandState.OPEN
        if self.state in (HandState.UNKNOWN, HandState.OPEN) and self._fist_streak >= 1:
            self.state = HandState.FISTED

    def _calc_angle(self, lms: np.ndarray):
        wrist, mid = lms[WRIST], lms[MIDDLE_MCP]
        v = mid - wrist
        if np.linalg.norm(v) < 1e-3:
            return None
        ang = math.degrees(math.atan2(-v[1], v[0]))
        ang = abs(ang) % 360
        if ang > 180:
            ang = 360 - ang
        ang = 180 - ang
        return float(np.clip(ang, 0, 180))

    def _angle_to_position(self, angle: float) -> RotationPosition:
        if angle < 60:   return RotationPosition.LEFT_FAR
        if angle < 90:   return RotationPosition.LEFT_NEAR
        if angle < 120:  return RotationPosition.RIGHT_NEAR
        return RotationPosition.RIGHT_FAR

    def _write_result(self, state_name, pos, ang):
        try:
            with open(self.result_file, "w", encoding="utf-8") as f:
                f.write(f"State: {state_name}\n")
                f.write(f"Position: {pos}\n")
                f.write(f"Angle: {ang:.1f}°\n")
        except Exception:
            pass

    def _send_udp(self, no_hand=False):
        try:
            if no_hand:
                msg = "area/menu/0"
                self.sock.sendto(msg.encode(), (self.udp_ip, self.udp_port))
                self._last_sent_pos = msg
                self._last_sent_state = None  # force resend on next valid hand
                return

            # State
            state_msg = "gesture/five" if self.state == HandState.OPEN else \
                        "gesture/zero" if self.state == HandState.FISTED else None
            if state_msg and state_msg != self._last_sent_state:
                self.sock.sendto(state_msg.encode(), (self.udp_ip, self.udp_port))
                self._last_sent_state = state_msg

            # Position
            area_msg = f"area/menu/{int(self._current_position.value)}"
            if area_msg != self._last_sent_pos:
                self.sock.sendto(area_msg.encode(), (self.udp_ip, self.udp_port))
                self._last_sent_pos = area_msg
        except Exception as e:
            print("UDP Error:", e)

    def _extract_landmarks(self, hand):
        lms, conf = None, 1.0
        if hand is None:
            return None, 0.0

        if isinstance(hand, dict):
            lms = hand.get("landmarks")
            conf = float(hand.get("lm_score", 1.0))
        elif hasattr(hand, "landmarks"):
            lms = np.array(hand.landmarks)
            conf = float(getattr(hand, "lm_score", 1.0))
        else:
            return None, 0.0

        if lms is None: return None, 0.0
        lms = np.asarray(lms, dtype=float)
        if lms.shape == (21, 3): lms = lms[:, :2]
        if lms.shape != (21, 2): return None, 0.0
        if not np.isfinite(lms).all(): return None, 0.0
        if np.allclose(lms, 0.0, atol=1e-9): return None, 0.0
        return lms, conf

    def get_state_info(self):
        return {
            "state": self.state.name,
            "hand_state": self.state.name,
            "angle": self._current_angle,
            "position": int(self._current_position.value),
            "position_name": self._position_name(self._current_position),
            "calibrated": self._calibrated,
            "finger_states": self._finger_states.copy(),
            "hand_detected": self._hand_detected,
        }

    def _position_name(self, pos: RotationPosition) -> str:
        names = {
            RotationPosition.NONE: "NONE",
            RotationPosition.LEFT_FAR: "Position 1 (LEFT)",
            RotationPosition.LEFT_NEAR: "Position 2 (LEFT-CENTER)",
            RotationPosition.RIGHT_NEAR: "Position 3 (RIGHT-CENTER)",
            RotationPosition.RIGHT_FAR: "Position 4 (RIGHT)",
        }
        return names.get(pos, "NONE")

    def reset(self):
        self.angle_buffer.clear()
        self.state = HandState.UNKNOWN
        self._open_streak = self._fist_streak = 0
        self._current_angle = None
        self._current_position = RotationPosition.NONE
        self._neutral_angle = None
        self._calib_samples.clear()
        self._calibrated = False
        self._finger_states.clear()
        self._last_sent_state = None
        self._last_sent_pos = None
        self._hand_detected = False
        self._last_seen_ms = 0
        print("Reset complete!")
