"""Gamepad input helpers for the PadRelay"""
import pygame
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..core.logging_utils import get_logger
from ..protocol.constants import PROTOCOL_VERSION

logger = get_logger(__name__)

class GamepadInput:
    """Collects input from a local gamepad"""
    
    def __init__(self, joystick_index: int = 0) -> None:
        """Set up input polling for the given joystick index"""
        self.joystick_index = joystick_index
        self.joystick = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """Initialize pygame and open the joystick"""
        try:
            pygame.init()
            pygame.joystick.init()
            
            if pygame.joystick.get_count() == 0:
                logger.error("No gamepad detected! Please connect a gamepad and try again.")
                return False
                
            self.joystick = pygame.joystick.Joystick(self.joystick_index)
            self.joystick.init()
            logger.info(f"Gamepad initialized: {self.joystick.get_name()}")
            
            # Log detailed controller information
            logger.info(f"Controller details:")
            logger.info(f"  - Number of axes: {self.joystick.get_numaxes()}")
            logger.info(f"  - Number of buttons: {self.joystick.get_numbuttons()}")
            logger.info(f"  - Number of hats: {self.joystick.get_numhats()}")
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing gamepad: {e}")
            return False
    
    def poll(self) -> Optional[Dict[str, Any]]:
        """Return the current gamepad state or ``None`` on error"""
        if not self.initialized or not self.joystick:
            return None
            
        pygame.event.pump()
        try:
            # Get buttons state (true if pressed)
            buttons = [bool(self.joystick.get_button(i)) for i in range(self.joystick.get_numbuttons())]
            
            # Get axes values (between -1.0 and 1.0)
            axes = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]
            
            # Get hat values (directions)
            hats = [self.joystick.get_hat(i) for i in range(self.joystick.get_numhats())]
            
            # Calculate trigger values if this is an Xbox-like controller
            # Typically, Xbox controllers use axis 2 for left trigger and axis 5 for right trigger
            trigger_left = None
            trigger_right = None
            if self.joystick.get_numaxes() > 2:
                trigger_left = (axes[2] + 1) / 2.0
            if self.joystick.get_numaxes() > 5:
                trigger_right = (axes[5] + 1) / 2.0
            
            message = {
                "type": "input",
                "protocol_version": PROTOCOL_VERSION,
                "timestamp": datetime.now().isoformat(),
                "buttons": buttons,
                "axes": axes,
                "hats": hats
            }
            
            # Add triggers if available
            if trigger_left is not None and trigger_right is not None:
                message["triggers"] = [trigger_left, trigger_right]
                
            return message
        except Exception as e:
            logger.error(f"Error polling gamepad: {e}")
            return None
    
    def cleanup(self) -> None:
        """Release Pygame resources"""
        try:
            pygame.quit()
            self.initialized = False
            self.joystick = None
        except Exception as e:
            logger.error(f"Error during pygame cleanup: {e}")
