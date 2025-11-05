"""
PRECISION Wrist Rotation Detector
- Robust palm-axis angle (stable under finger motion)
- Temporal debouncing (streak + cooldown)
- One-Euro angle filter (smooth yet responsive)
- Variance gate for stable transitions
- K-frame confirmation for position changes
- Schmitt (hysteresis) bins at 60/90/120
- Distance-aware OPEN/FIST detection
- Writes to result.txt
"""
from enum import Enum, auto
from collections import deque
from typing import Optional, Tuple, List
import os
import numpy as np
import math
import time

__all__ = ["WristRotationDetector", "HandState", "RotationPosition", "__version__"]
__version__ = "0.6.0"

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
    LEFT_FAR = 1    # 0°   to 60°
    LEFT_NEAR = 2   # 60°  to 90°
    RIGHT_NEAR = 3  # 90°  to 120°
    RIGHT_FAR = 4   # 120° to 180°


def _median(seq: List[float]):
    if not seq:
        return None
    return float(np.median(np.asarray(seq, dtype=float)))


# -------- One-Euro filter (for smooth + responsive angle) --------
class OneEuro:
    def __init__(self, freq=30.0, min_cutoff=1.0, beta=0.025, d_cutoff=1.4):
        self.freq = float(freq)
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self._x_prev = None
        self._dx_prev = None

    def _alpha(self, cutoff):
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / self.freq
        return 1.0 / (1.0 + tau / te)

    def filter(self, x):
        x = float(x)
        if self._x_prev is None:
            self._x_prev, self._dx_prev = x, 0.0
            return x
        dx = (x - self._x_prev) * self.freq
        a_d = self._alpha(self.d_cutoff)
        dx_hat = a_d * dx + (1 - a_d) * self._dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(cutoff)
        x_hat = a * x + (1 - a) * self._x_prev
        self._x_prev, self._dx_prev = x_hat, dx_hat
        return float(x_hat)


class WristRotationDetector:
    """
    Wrist Rotation Detector (precision/stability focused)
    Position mapping (NO DEAD ZONE):
    - Position 1: 0° to 60°
    - Position 2: 60° to 90°
    - Position 3: 90° to 120°
    - Position 4: 120° to 180°
    """

    def __init__(
        self,
        buffer_size: int = 12,
        angle_smoothing: int = 5,
        ema_alpha: float = 0.3,
        open_frames: int = 2,
        fist_frames: int = 3,
        min_lm_score: float = 0.3,
        max_angle_jump: float = 30.0,
        neutral_calibration_frames: int = 10,
        finger_extension_threshold: float = 0.65,
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

        # --- Transition controls (debounce) ---
        self._cooldown_ms = 450     # block rapid OPEN<->FIST toggles
        self._min_open_streak = 4   # frames to confirm OPEN
        self._min_fist_streak = 4   # frames to confirm FIST
        self._last_change_ms = 0

        # --- Angle filter (One-Euro) ---
        self._euro = OneEuro(freq=30.0, min_cutoff=1.0, beta=0.025, d_cutoff=1.4)

        # --- Schmitt hysteresis for position bins (deg margin around 60/90/120) ---
        self._schmitt = 7.0

        # --- Precision gate (accept updates only when stable) ---
        self._var_window = 8          # frames to compute variance
        self._max_var_open = 14.0     # deg^2 variance allowed to change OPEN position
        self._max_var_state = 24.0    # deg^2 variance allowed to flip OPEN<->FIST

        # --- K-frame confirmation for position updates ---
        self._pos_confirm_frames = 4
        self._pos_pending = None
        self._pos_pending_streak = 0

        # --- Optional preset via env (strict|normal|loose) ---
        self._apply_preset(os.environ.get("WRIST_PRECISION", "strict").lower())

    # ------------------------ Public API ------------------------

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

        # Calculate wrist angle (robust palm-axis)
        angle_raw = self._compute_wrist_angle(lms)
        if angle_raw is None:
            return self._finalize(None)

        # Motion-adaptive smoothing first (One-Euro)
        angle_raw = self._euro.filter(angle_raw)

        # Spike rejection
        if self.angles and abs(angle_raw - self.angles[-1]) > self.max_angle_jump:
            angle_raw = self.angles[-1]

        self.angles_raw.append(angle_raw)

        # Median + EMA smoothing
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

        # -------- Position mapping with Schmitt + variance gate + K-frame confirm --------
        cand_pos = self._angle_to_position(angle)

        var_ok = True
        var = self._angle_variance(self._var_window)
        if var is not None:
            var_ok = (var <= self._max_var_open)

        prev_pos = self._last_position
        pos = prev_pos

        if self.state == HandState.OPEN and var_ok:
            if self._pos_pending is None or self._pos_pending != cand_pos:
                self._pos_pending = cand_pos
                self._pos_pending_streak = 1
            else:
                self._pos_pending_streak += 1

            if self._pos_pending_streak >= self._pos_confirm_frames:
                pos = self._pos_pending
                self._selected_position = pos.value
        else:
            pos = RotationPosition.NONE  # on fist/unstable, hide live pos (keep selected_position)

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
        self._pos_pending = None
        self._pos_pending_streak = 0

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

    # ------------------------ Internals ------------------------

    def _apply_preset(self, preset: str):
        if preset == "strict":
            self._cooldown_ms = 450
            self._min_open_streak = 4
            self._min_fist_streak = 4
            self._schmitt = 7.0
            self._pos_confirm_frames = 4
            self._max_var_open = 14.0
            self._max_var_state = 24.0
        elif preset == "loose":
            self._cooldown_ms = 200
            self._min_open_streak = 2
            self._min_fist_streak = 2
            self._schmitt = 3.0
            self._pos_confirm_frames = 2
            self._max_var_open = 35.0
            self._max_var_state = 50.0
        # else "normal" == keep defaults

    def _position_name(self, pos: RotationPosition) -> str:
        mapping = {
            RotationPosition.NONE: "NONE",
            RotationPosition.LEFT_FAR: "Position 1 (LEFT)",
            RotationPosition.LEFT_NEAR: "Position 2 (LEFT-CENTER)",
            RotationPosition.RIGHT_NEAR: "Position 3 (RIGHT-CENTER)",
            RotationPosition.RIGHT_FAR: "Position 4 (RIGHT)",
        }
        return mapping.get(pos, "NONE")

    def _finalize(self, angle: Optional[float]) -> Tuple[RotationPosition, Optional[float], HandState]:
        if angle is None and self.angles:
            angle = self.angles[-1]
        pos = self._angle_to_position(angle) if (angle is not None and self.state == HandState.OPEN) else RotationPosition.NONE
        return pos, angle, self.state

    def _write_result(self, state_name: str, position: int, angle: float):
        """Write result to result.txt"""
        try:
            with open(self.result_file, 'w', encoding='utf-8') as f:
                f.write(f"State: {state_name}\n")
                if self.state == HandState.FISTED:
                    f.write(f"Selected Position: {self._selected_position}\n")
                else:
                    f.write(f"Current Position: {position}\n")
                f.write(f"Angle: {angle:.1f}°\n")
        except Exception:
            pass  # Ignore file write errors

    # --------- Debounce (streak + cooldown + variance) ---------
    def _now_ms(self):
        return int(time.time() * 1000)

    def _angle_variance(self, k: int) -> Optional[float]:
        if len(self.angles_raw) < max(2, k):
            return None
        a = np.array(list(self.angles_raw)[-k:], dtype=float)
        return float(np.var(a))

    def _apply_hysteresis(self, measured: HandState):
        """Streak + cooldown based debouncer, gated by variance for state flips."""
        now = self._now_ms()
        in_cooldown = (now - getattr(self, "_last_change_ms", 0)) < self._cooldown_ms

        if measured == HandState.OPEN:
            self._open_streak += 1
            self._fist_streak = 0
        elif measured == HandState.FISTED:
            self._fist_streak += 1
            self._open_streak = 0
        else:
            self._open_streak = self._fist_streak = 0

        new_state = self.state
        if not in_cooldown:
            if self.state in (HandState.UNKNOWN, HandState.FISTED) and self._open_streak >= self._min_open_streak:
                new_state = HandState.OPEN
            elif self.state in (HandState.UNKNOWN, HandState.OPEN) and self._fist_streak >= self._min_fist_streak:
                new_state = HandState.FISTED

        if new_state != self.state:
            # Precision gate for OPEN<->FIST switch
            var_ok = True
            var = self._angle_variance(self._var_window)
            if var is not None:
                var_ok = (var <= self._max_var_state)

            if var_ok:
                self.state = new_state
                self._last_change_ms = now

    # --------- Hand state (distance-aware ensemble) ---------
    def _detect_hand_state_simple(self, lms: np.ndarray) -> HandState:
        """
        OPEN vs FIST robust to rotation & mild bend, distance-aware.
        OPEN if enough per-finger votes and spread are satisfied.
        """
        wrist = lms[WRIST]

        # Distance-aware scaling using palm width
        palm_width = np.linalg.norm(lms[INDEX_MCP] - lms[PINKY_MCP])
        if palm_width < 1e-6:
            palm_width = np.linalg.norm(lms[MIDDLE_MCP] - wrist) * 2.0 + 1e-6

        base_mcp = 70.0     # deg (smaller = stricter straightness)
        base_reach = 1.03
        SPREAD_MIN = 1.55
        STAY_OPEN_NON_THUMB_MIN = 2

        # scale: nearer hands stricter, far hands looser (but capped)
        scale = np.clip(80.0 / max(palm_width, 1.0), 0.85, 1.20)
        MCP_ANGLE_MAX = base_mcp * (1.0 / scale)
        REACH_RATIO   = base_reach * (1.0 - (scale - 1.0) * 0.25)

        def ang_at_mcp(mcp_idx, tip_idx):
            mcp = lms[mcp_idx]; tip = lms[tip_idx]
            v1 = mcp - wrist
            v2 = tip - mcp
            n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
            if n1 < 1e-6 or n2 < 1e-6:
                return 180.0
            cosang = np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)
            return float(np.degrees(np.arccos(cosang)))

        def reach_ok(tip_idx, ref_mcp_idx):
            tip_dist = np.linalg.norm(lms[tip_idx] - wrist)
            mcp_dist = np.linalg.norm(lms[ref_mcp_idx] - wrist)
            return bool(mcp_dist > 1e-6 and tip_dist >= REACH_RATIO * mcp_dist)

        def finger_extended(tip, mcp):
            a_ok = ang_at_mcp(mcp, tip) <= MCP_ANGLE_MAX
            b_ok = reach_ok(tip, mcp)
            return a_ok, b_ok

        idxA, idxB = finger_extended(INDEX_TIP, INDEX_MCP)
        midA, midB = finger_extended(MIDDLE_TIP, MIDDLE_MCP)
        rngA, rngB = finger_extended(RING_TIP,   RING_MCP)
        pkyA, pkyB = finger_extended(PINKY_TIP,  PINKY_MCP)

        # Thumb reach vs index MCP; thumb MCP angle not used
        thumb_reach = np.linalg.norm(lms[THUMB_TIP] - wrist) >= 0.85 * np.linalg.norm(lms[INDEX_MCP] - wrist)
        thumb_ext = thumb_reach

        idx_ext = (idxA + idxB) >= 1
        mid_ext = (midA + midB) >= 1
        rng_ext = (rngA + rngB) >= 1
        pky_ext = (pkyA + pkyB) >= 1

        tips = [lms[INDEX_TIP], lms[MIDDLE_TIP], lms[RING_TIP], lms[PINKY_TIP]]
        spread = (np.linalg.norm(tips[1]-tips[0]) +
                  np.linalg.norm(tips[2]-tips[1]) +
                  np.linalg.norm(tips[3]-tips[2])) / max(palm_width, 1e-6)
        spread_ok = spread >= SPREAD_MIN

        non_thumb_ext_count = int(idx_ext) + int(mid_ext) + int(rng_ext) + int(pky_ext)
        votes_pass = ((non_thumb_ext_count >= 2) + int(spread_ok))
        open_now = (votes_pass >= 2) or (non_thumb_ext_count >= 3) or (non_thumb_ext_count >= 2 and thumb_ext)

        if getattr(self, "_prev_state", None) == HandState.OPEN:
            if non_thumb_ext_count >= STAY_OPEN_NON_THUMB_MIN:
                open_now = True

        self._finger_states = {
            'thumb': thumb_ext, 'index': idx_ext, 'middle': mid_ext,
            'ring': rng_ext, 'pinky': pky_ext
        }

        state = HandState.OPEN if open_now else HandState.FISTED
        self._prev_state = state
        return state

    # --------- Angle + position mapping ---------
    def _compute_wrist_angle(self, lms: np.ndarray) -> Optional[float]:
        """
        Angle defined by the *finger direction* (wrist -> middle MCP),
        aligned with the mirrored preview, and scaled so that:
            - Fingers pointing RIGHT  -> ~180°
            - Fingers pointing UP     -> ~90°
            - Fingers pointing LEFT   -> ~0°
        This often matches human intuition better for UI.
        """
        wrist = lms[WRIST]
        middle_mcp = lms[MIDDLE_MCP]

        vec = middle_mcp - wrist
        n = np.linalg.norm(vec)
        if n < 1e-3:
            return None

        # Base angle vs +X axis; use -y because image coords have y downward.
        ang = math.degrees(math.atan2(-vec[1], vec[0]))  # 0..±180
        if ang < 0.0:
            ang += 360.0                                 # 0..360

        # Fold to acute 0..180 (orientation, not direction)
        if ang > 180.0:
            ang = 360.0 - ang

        # Invert so RIGHT ≈ 180°, LEFT ≈ 0°
        ang = 180.0 - ang

        # Clamp
        return float(np.clip(ang, 0.0, 180.0))

    def _angle_to_position(self, angle: float) -> RotationPosition:
        """
        Map angle to position with Schmitt hysteresis to avoid bin ping-pong at 60/90/120.
        - Position 1: 0° to 60°
        - Position 2: 60° to 90°
        - Position 3: 90° to 120°
        - Position 4: 120° to 180°
        """
        h = self._schmitt
        t1, t2, t3 = 60.0, 90.0, 120.0
        prev = self._last_position

        if prev in (RotationPosition.NONE, RotationPosition.LEFT_FAR):
            return RotationPosition.LEFT_NEAR if angle >= t1 + h else RotationPosition.LEFT_FAR

        if prev == RotationPosition.LEFT_NEAR:
            if angle < t1 - h: return RotationPosition.LEFT_FAR
            return RotationPosition.RIGHT_NEAR if angle >= t2 + h else RotationPosition.LEFT_NEAR

        if prev == RotationPosition.RIGHT_NEAR:
            if angle < t2 - h: return RotationPosition.LEFT_NEAR
            return RotationPosition.RIGHT_FAR if angle >= t3 + h else RotationPosition.RIGHT_NEAR

        if prev == RotationPosition.RIGHT_FAR:
            return RotationPosition.RIGHT_NEAR if angle < t3 - h else RotationPosition.RIGHT_FAR

        # Fallback for first frame
        if angle < t1: return RotationPosition.LEFT_FAR
        if angle < t2: return RotationPosition.LEFT_NEAR
        if angle < t3: return RotationPosition.RIGHT_NEAR
        return RotationPosition.RIGHT_FAR

    # --------- Landmarks extraction ---------
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
