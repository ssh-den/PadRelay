"""Virtual gamepad wrapper for the server."""
from typing import Dict, Optional
from ..core.logging_utils import get_logger

logger = get_logger(__name__)

class VirtualGamepad:
    """Wraps ``vgamepad`` to provide a unified API"""
    
    def __init__(self, gamepad_type: str = 'xbox360', config: Optional[object] = None) -> None:
        """Create the virtual gamepad"""
        self.gamepad_type = gamepad_type.lower()
        self.config = config
        self.gamepad = None
        self.button_mapping = None
        
        # I'll import vgamepad here to allow the module to load even if vgamepad isn't installed
        try:
            import vgamepad as vg
            self.vg = vg
        except ImportError:
            logger.critical("vgamepad module not found. Please install it using: pip install vgamepad")
            raise ImportError("vgamepad module not found")
        
        # Create the virtual gamepad
        self.setup_gamepad()
        
        # Load button mappings
        self.button_mapping = self.load_button_mapping()
        
        logger.info(f"Virtual gamepad initialized: {gamepad_type}")
    
    def setup_gamepad(self) -> bool:
        """Setup the requested gamepad type"""
        try:
            if self.gamepad_type == 'ds4':
                self.gamepad = self.vg.VDS4Gamepad()
                logger.info("Virtual DualShock4 gamepad created successfully.")
            else:
                self.gamepad = self.vg.VX360Gamepad()
                logger.info("Virtual Xbox360 gamepad created successfully.")
                
            # Reset gamepad to default state
            self.reset_gamepad_state()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create virtual gamepad: {e}")
            return False
    
    def reset_gamepad_state(self) -> bool:
        """Return the gamepad to its default state"""
        try:
            self.gamepad.reset()
            self.gamepad.update()
            logger.info("Gamepad state reset to default")
            return True
        except Exception as e:
            logger.error(f"Failed to reset gamepad state: {e}")
            return False
    
    def load_button_mapping(self) -> Dict[int, int]:
        """Load button mapping, falling back to defaults."""
        if self.config:
            mapping = self._load_mapping_from_config()
            if mapping:
                return mapping
                
        logger.info("Using default button mapping")
        return self._default_button_mapping()
    
    def _load_mapping_from_config(self) -> Optional[Dict[int, int]]:
        """Read mapping from the configuration"""
        mapping = {}
        section_name = f"button_mapping_{self.gamepad_type.lower()}"
        
        if self.config and self.config.has_section(section_name):
            try:
                for key, value in self.config.items(section_name):
                    index = int(key)
                    if self.gamepad_type == 'ds4':
                        mapping[index] = getattr(self.vg.DS4_BUTTONS, value)
                    else:
                        mapping[index] = getattr(self.vg.XUSB_BUTTON, value)
                logger.info(f"Button mapping loaded from configuration")
                return mapping
            except Exception as e:
                logger.error(f"Error processing button mapping from config: {e}")
                
        return None
    
    def _default_button_mapping(self) -> Dict[int, int]:
        """Return the built-in button mapping"""
        if self.gamepad_type == "ds4":
            return {
                0: self.vg.DS4_BUTTONS.DS4_BUTTON_CROSS,          # X/Cross
                1: self.vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,         # Circle
                2: self.vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,         # Square
                3: self.vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,       # Triangle
                4: self.vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,  # L1
                5: self.vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT, # R1
                6: self.vg.DS4_BUTTONS.DS4_BUTTON_SHARE,          # Share
                7: self.vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,        # Options
                8: self.vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,     # L3
                9: self.vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,    # R3
                10: self.vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_LEFT,  # L2 button
                11: self.vg.DS4_BUTTONS.DS4_BUTTON_TRIGGER_RIGHT, # R2 button
            }
        else:
            return {
                0: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_A,              # A
                1: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_B,              # B
                2: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_X,              # X
                3: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,              # Y
                4: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,  # LB
                5: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER, # RB
                6: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,           # Back
                7: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_START,          # Start
                8: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,     # Left stick click
                9: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,    # Right stick click
                10: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,       # D-pad up
                11: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,     # D-pad down
                12: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,     # D-pad left
                13: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,    # D-pad right
                14: self.vg.XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,         # Guide button
            }
    
    def get_button_mapping(self) -> Dict[int, int]:
        """Return the current button mapping"""
        return self.button_mapping

    # ------------------------------------------------------------------
    # Wrapper methods used by GamepadHandler
    # ------------------------------------------------------------------

    def press_button(self, *args, **kwargs) -> None:
        self.gamepad.press_button(*args, **kwargs)

    def release_button(self, *args, **kwargs) -> None:
        self.gamepad.release_button(*args, **kwargs)

    def left_joystick_float(self, *args, **kwargs) -> None:
        self.gamepad.left_joystick_float(*args, **kwargs)

    def right_joystick_float(self, *args, **kwargs) -> None:
        self.gamepad.right_joystick_float(*args, **kwargs)

    def left_trigger_float(self, *args, **kwargs) -> None:
        self.gamepad.left_trigger_float(*args, **kwargs)

    def right_trigger_float(self, *args, **kwargs) -> None:
        self.gamepad.right_trigger_float(*args, **kwargs)

    def update(self) -> None:
        self.gamepad.update()
