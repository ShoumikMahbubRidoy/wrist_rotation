#!/usr/bin/env python3
"""
Wrist Rotation Detector
Detects wrist rotation angle from palm-facing camera (40-100cm distance)
Only tracks rotation when hand is open (not fisted)
Maps rotation to 4 positions based on angle ranges
"""
import numpy as np
from collections import deque
from enum import Enum
import math


class HandState(Enum):
    """Hand state classification"""
    FISTED = 0
    OPEN = 1


class RotationPosition(Enum):
    """Wrist rotation position zones"""
    NONE = 0      # No valid detection
    LEFT_FAR = 1  # 0° to 60°
    LEFT_NEAR = 2 # 60° to 90°
    RIGHT_NEAR = 3 # 90° to 120°
    RIGHT_FAR = 4  # 120° to 180°


class WristRotationDetector:
    """
    Detects wrist rotation angle and maps to 4 position zones.
    
    Detection flow:
    1. Check if hand is open (any finger extended)
    2. If open, calculate wrist rotation angle
    3. Map angle to position (1-4)
    4. Store and display position
    
    Angle ranges (from vertical 90°):
    - Position 1: 0° to 60° (left rotation, far)
    - Position 2: 60° to 90° (left rotation, near)
    - Position 3: 90° to 120° (right rotation, near)
    - Position 4: 120° to 180° (right rotation, far)
    """
    
    def __init__(self, buffer_size=10, angle_smoothing=5):
        """
        Initialize wrist rotation detector.
        
        Args:
            buffer_size: Number of hand states to buffer for stability
            angle_smoothing: Number of angle samples to average
        """
        self.buffer_size = buffer_size
        self.angle_smoothing = angle_smoothing
        
        # State buffers
        self.hand_state_buffer = deque(maxlen=buffer_size)
        self.angle_buffer = deque(maxlen=angle_smoothing)
        
        # Current state
        self.current_hand_state = HandState.FISTED
        self.current_position = RotationPosition.NONE
        self.current_angle = 90.0  # Baseline vertical
        
        # Statistics
        self.total_position_changes = 0
        self.position_history = []
        
    def classify_hand_state(self, hand_region) -> HandState:
        """
        Classify if hand is fisted or open based on finger extension.
        
        Args:
            hand_region: HandRegion object with landmarks
            
        Returns:
            HandState.FISTED or HandState.OPEN
        """
        if not hasattr(hand_region, 'landmarks') or hand_region.landmarks is None:
            return HandState.FISTED
        
        # Get finger tip and base landmarks
        # MediaPipe hand landmarks: 0=wrist, 4=thumb_tip, 8=index_tip, 
        # 12=middle_tip, 16=ring_tip, 20=pinky_tip
        try:
            landmarks = hand_region.landmarks
            
            # Index finger: tip (8) vs MCP base (5)
            index_tip = landmarks[8]
            index_mcp = landmarks[5]
            index_extended = index_tip[1] < index_mcp[1]  # Y decreases upward
            
            # Middle finger: tip (12) vs MCP base (9)
            middle_tip = landmarks[12]
            middle_mcp = landmarks[9]
            middle_extended = middle_tip[1] < middle_mcp[1]
            
            # Ring finger: tip (16) vs MCP base (13)
            ring_tip = landmarks[16]
            ring_mcp = landmarks[13]
            ring_extended = ring_tip[1] < ring_mcp[1]
            
            # Pinky finger: tip (20) vs MCP base (17)
            pinky_tip = landmarks[20]
            pinky_mcp = landmarks[17]
            pinky_extended = pinky_tip[1] < pinky_mcp[1]
            
            # Thumb: tip (4) vs MCP base (2)
            thumb_tip = landmarks[4]
            thumb_mcp = landmarks[2]
            # Thumb extends horizontally, check X distance
            thumb_extended = abs(thumb_tip[0] - thumb_mcp[0]) > 30
            
            # Any finger extended = OPEN
            any_extended = (index_extended or middle_extended or 
                          ring_extended or pinky_extended or thumb_extended)
            
            return HandState.OPEN if any_extended else HandState.FISTED
            
        except (IndexError, TypeError):
            return HandState.FISTED
    
    def calculate_wrist_angle(self, hand_region) -> float:
        """
        Calculate wrist rotation angle from hand landmarks.
        
        Uses wrist (0) to middle finger MCP (9) vector to determine rotation.
        Returns angle in degrees where:
        - 90° = vertical (baseline)
        - 0° = horizontal left
        - 180° = horizontal right
        
        Args:
            hand_region: HandRegion object with landmarks
            
        Returns:
            Angle in degrees (0-180)
        """
        if not hasattr(hand_region, 'landmarks') or hand_region.landmarks is None:
            return 90.0  # Default vertical
        
        try:
            landmarks = hand_region.landmarks
            
            # Wrist position (landmark 0)
            wrist = landmarks[0]
            
            # Middle finger MCP (landmark 9) - stable reference point
            middle_mcp = landmarks[9]
            
            # Calculate vector from wrist to middle MCP
            dx = middle_mcp[0] - wrist[0]
            dy = middle_mcp[1] - wrist[1]
            
            # Calculate angle in radians, then convert to degrees
            angle_rad = math.atan2(-dy, dx)  # -dy because Y increases downward
            angle_deg = math.degrees(angle_rad)
            
            # Normalize to 0-180 range (right side)
            # 0° = horizontal right, 90° = vertical up, 180° = horizontal left
            if angle_deg < 0:
                angle_deg += 180
            elif angle_deg > 180:
                angle_deg = 180
            
            # Flip to match expected: 0° = left, 90° = vertical, 180° = right
            angle_deg = 180 - angle_deg
            
            return angle_deg
            
        except (IndexError, TypeError):
            return 90.0  # Default vertical
    
    def angle_to_position(self, angle: float) -> RotationPosition:
        """
        Map angle to rotation position zone.
        
        Position mapping:
        - Position 1: 0° to 60° (left far)
        - Position 2: 60° to 90° (left near)
        - Position 3: 90° to 120° (right near)
        - Position 4: 120° to 180° (right far)
        
        Args:
            angle: Angle in degrees (0-180)
            
        Returns:
            RotationPosition enum value
        """
        if angle < 60:
            return RotationPosition.LEFT_FAR
        elif angle < 90:
            return RotationPosition.LEFT_NEAR
        elif angle < 120:
            return RotationPosition.RIGHT_NEAR
        else:
            return RotationPosition.RIGHT_FAR
    
    def update(self, hand_region):
        """
        Update wrist rotation state with new hand detection.
        
        Args:
            hand_region: HandRegion object from hand detector
            
        Returns:
            tuple: (current_position, current_angle, hand_state)
        """
        # Classify hand state
        hand_state = self.classify_hand_state(hand_region)
        self.hand_state_buffer.append(hand_state)
        
        # Determine stable hand state (majority vote)
        if len(self.hand_state_buffer) >= 3:
            open_count = sum(1 for s in list(self.hand_state_buffer)[-3:] 
                           if s == HandState.OPEN)
            self.current_hand_state = (HandState.OPEN if open_count >= 2 
                                      else HandState.FISTED)
        else:
            self.current_hand_state = hand_state
        
        # Only track rotation if hand is open
        if self.current_hand_state == HandState.OPEN:
            # Calculate wrist angle
            angle = self.calculate_wrist_angle(hand_region)
            self.angle_buffer.append(angle)
            
            # Smooth angle using moving average
            if len(self.angle_buffer) >= 3:
                self.current_angle = np.mean(list(self.angle_buffer)[-3:])
            else:
                self.current_angle = angle
            
            # Map to position
            new_position = self.angle_to_position(self.current_angle)
            
            # Track position changes
            if new_position != self.current_position and new_position != RotationPosition.NONE:
                self.current_position = new_position
                self.total_position_changes += 1
                self.position_history.append(new_position)
                
                # Keep history limited
                if len(self.position_history) > 100:
                    self.position_history.pop(0)
        else:
            # Hand fisted - no position tracking
            self.current_position = RotationPosition.NONE
            self.current_angle = 90.0
        
        return self.current_position, self.current_angle, self.current_hand_state
    
    def get_position_name(self) -> str:
        """Get human-readable position name"""
        if self.current_position == RotationPosition.NONE:
            return "No Detection"
        elif self.current_position == RotationPosition.LEFT_FAR:
            return "Position 1 (Left Far)"
        elif self.current_position == RotationPosition.LEFT_NEAR:
            return "Position 2 (Left Near)"
        elif self.current_position == RotationPosition.RIGHT_NEAR:
            return "Position 3 (Right Near)"
        else:
            return "Position 4 (Right Far)"
    
    def get_state_info(self) -> dict:
        """Get current detector state as dictionary"""
        return {
            'hand_state': self.current_hand_state.name,
            'hand_state_value': self.current_hand_state.value,
            'position': self.current_position.value,
            'position_name': self.get_position_name(),
            'angle': round(self.current_angle, 1),
            'total_changes': self.total_position_changes,
        }
    
    def reset(self):
        """Reset detector state"""
        self.hand_state_buffer.clear()
        self.angle_buffer.clear()
        self.current_hand_state = HandState.FISTED
        self.current_position = RotationPosition.NONE
        self.current_angle = 90.0
        self.total_position_changes = 0
        self.position_history.clear()