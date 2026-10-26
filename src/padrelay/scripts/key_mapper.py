#!/usr/bin/env python3
"""
Xbox360/DS4 Controller Key Mapper

This script helps map your physical gamepad buttons to virtual gamepad buttons
"""

import sys
import os
import time
import pygame
import argparse
import configparser

# Define constants for Xbox360 and DS4 buttons from vgamepad
XBOX360_BUTTONS = [
    "XUSB_GAMEPAD_A",
    "XUSB_GAMEPAD_B", 
    "XUSB_GAMEPAD_X",
    "XUSB_GAMEPAD_Y",
    "XUSB_GAMEPAD_DPAD_UP",
    "XUSB_GAMEPAD_DPAD_DOWN",
    "XUSB_GAMEPAD_DPAD_LEFT",
    "XUSB_GAMEPAD_DPAD_RIGHT",
    "XUSB_GAMEPAD_LEFT_SHOULDER",
    "XUSB_GAMEPAD_RIGHT_SHOULDER",
    "XUSB_GAMEPAD_LEFT_THUMB",
    "XUSB_GAMEPAD_RIGHT_THUMB",
    "XUSB_GAMEPAD_START",
    "XUSB_GAMEPAD_BACK",
    "XUSB_GAMEPAD_GUIDE"
]

DS4_BUTTONS = [
    "DS4_BUTTON_CROSS",
    "DS4_BUTTON_CIRCLE", 
    "DS4_BUTTON_SQUARE",
    "DS4_BUTTON_TRIANGLE",
    "DS4_BUTTON_SHOULDER_LEFT",
    "DS4_BUTTON_SHOULDER_RIGHT",
    "DS4_BUTTON_TRIGGER_LEFT",
    "DS4_BUTTON_TRIGGER_RIGHT",
    "DS4_BUTTON_SHARE",
    "DS4_BUTTON_OPTIONS",
    "DS4_BUTTON_THUMB_LEFT",
    "DS4_BUTTON_THUMB_RIGHT"
]

# Button descriptions
XBOX360_BUTTON_NAMES = {
    "XUSB_GAMEPAD_A": "A Button (Green)",
    "XUSB_GAMEPAD_B": "B Button (Red)",
    "XUSB_GAMEPAD_X": "X Button (Blue)",
    "XUSB_GAMEPAD_Y": "Y Button (Yellow)",
    "XUSB_GAMEPAD_DPAD_UP": "D-Pad Up",
    "XUSB_GAMEPAD_DPAD_DOWN": "D-Pad Down",
    "XUSB_GAMEPAD_DPAD_LEFT": "D-Pad Left",
    "XUSB_GAMEPAD_DPAD_RIGHT": "D-Pad Right",
    "XUSB_GAMEPAD_LEFT_SHOULDER": "Left Bumper (LB)",
    "XUSB_GAMEPAD_RIGHT_SHOULDER": "Right Bumper (RB)",
    "XUSB_GAMEPAD_LEFT_THUMB": "Left Stick Click",
    "XUSB_GAMEPAD_RIGHT_THUMB": "Right Stick Click",
    "XUSB_GAMEPAD_START": "Start Button",
    "XUSB_GAMEPAD_BACK": "Back Button",
    "XUSB_GAMEPAD_GUIDE": "Xbox Button (Guide)"
}

DS4_BUTTON_NAMES = {
    "DS4_BUTTON_CROSS": "Cross Button (×)",
    "DS4_BUTTON_CIRCLE": "Circle Button (○)",
    "DS4_BUTTON_SQUARE": "Square Button (□)",
    "DS4_BUTTON_TRIANGLE": "Triangle Button (△)",
    "DS4_BUTTON_SHOULDER_LEFT": "L1 Button",
    "DS4_BUTTON_SHOULDER_RIGHT": "R1 Button",
    "DS4_BUTTON_TRIGGER_LEFT": "L2 Button (Digital)",
    "DS4_BUTTON_TRIGGER_RIGHT": "R2 Button (Digital)",
    "DS4_BUTTON_SHARE": "Share Button",
    "DS4_BUTTON_OPTIONS": "Options Button",
    "DS4_BUTTON_THUMB_LEFT": "L3 Button (Left Stick Click)",
    "DS4_BUTTON_THUMB_RIGHT": "R3 Button (Right Stick Click)"
}

# Axis names and descriptions
AXIS_NAMES = {
    "left_stick_x": "Left Stick X-axis (move left stick left)",
    "left_stick_y": "Left Stick Y-axis (move left stick up)",
    "right_stick_x": "Right Stick X-axis (move right stick right)",
    "right_stick_y": "Right Stick Y-axis (move right stick up)",
    "trigger_left": "Left Trigger (press and hold LT/L2)",
    "trigger_right": "Right Trigger (press and hold RT/R2)"
}

class ControllerMapper:
    def __init__(self, output_path, polling_interval=0.1):
        # Initialize attributes
        self.output_path = output_path
        self.polling_interval = polling_interval
        self.joystick = None
        self.gamepad_type = None
        self.button_mapping = {}
        self.hat_mapping = {}  # For D-pad if it uses a hat
        self.axis_mapping = {}
        self.uses_hat_for_dpad = False
        self.interrupt_flag = False
        
        # Initialize pygame
        pygame.init()
        pygame.joystick.init()
        
    def select_gamepad_type(self):
        """Allow user to select gamepad type"""
        controller_name = self.joystick.get_name().lower()
        
        # Try to auto-detect based on common controller names
        if 'xbox' in controller_name or 'x-box' in controller_name:
            suggested_type = 'xbox360'
        elif 'dual shock' in controller_name or 'dualshock' in controller_name or 'playstation' in controller_name or 'ps4' in controller_name:
            suggested_type = 'ds4'
        else:
            suggested_type = None
            
        # Ask user to confirm or select
        if suggested_type:
            print(f"\nDetected controller type: {suggested_type} (based on '{controller_name}')")
            print("Is this correct? (y/n)")
            response = input().lower()
            
            if response == 'y':
                self.gamepad_type = suggested_type
                return
        
        # Manual selection
        print("\nSelect gamepad type:")
        print("1. Xbox 360")
        print("2. DualShock 4 (PS4)")
        
        while True:
            choice = input("Enter choice (1 or 2): ")
            if choice == '1':
                self.gamepad_type = 'xbox360'
                break
            elif choice == '2':
                self.gamepad_type = 'ds4'
                break
            else:
                print("Invalid choice. Please enter 1 or 2.")
    
    def detect_controller(self):
        """Detect and initialize the first available controller"""
        if pygame.joystick.get_count() == 0:
            print("No gamepad detected! Please connect a gamepad and try again.")
            return False
            
        self.joystick = pygame.joystick.Joystick(0)
        self.joystick.init()
        
        print(f"\nController detected: {self.joystick.get_name()}")
        print(f"Number of buttons: {self.joystick.get_numbuttons()}")
        print(f"Number of axes: {self.joystick.get_numaxes()}")
        print(f"Number of hats: {self.joystick.get_numhats()}")
        
        # Select gamepad type
        self.select_gamepad_type()
        
        return True
    
    def wait_for_button_release(self):
        """Wait until all buttons are released"""
        time.sleep(0.3)  # Initial delay
        while True:
            pygame.event.pump()  # Process events without retrieving them
            all_released = True
            for i in range(self.joystick.get_numbuttons()):
                if self.joystick.get_button(i):
                    all_released = False
                    break
            if all_released:
                break
            time.sleep(self.polling_interval)
        time.sleep(0.2)  # Additional delay after release
    
    def wait_for_neutral(self, duration=1.0):
        """Wait for controller to return to neutral state"""
        print("\nPlease release all controls and return to neutral position...")
        time.sleep(duration)
        pygame.event.pump()
    
    def wait_for_button_press(self, timeout=10):
        """Wait for a button press and return the button index"""
        print("Waiting for button press...")
        start_time = time.time()
        button_states = [self.joystick.get_button(i) for i in range(self.joystick.get_numbuttons())]
        
        while time.time() - start_time < timeout:
            pygame.event.pump()  # Process events without retrieving them
            
            for i in range(self.joystick.get_numbuttons()):
                current_state = self.joystick.get_button(i)
                if current_state and not button_states[i]:
                    return i
                button_states[i] = current_state
            
            # Check for skip input
            if self.check_for_skip():
                return None
                
            time.sleep(self.polling_interval)
        
        return None
    
    def check_for_skip(self):
        """Non-blocking check for skip input (Enter key)"""
        for event in pygame.event.get([pygame.KEYDOWN]):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                return True
        return False
    
    def wait_for_hat_movement(self, timeout=10):
        """Wait for hat (D-pad) movement and return the value"""
        print("Waiting for D-pad input...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            pygame.event.pump()  # Process events without retrieving them
            
            for i in range(self.joystick.get_numhats()):
                hat_value = self.joystick.get_hat(i)
                if hat_value != (0, 0):
                    return hat_value
            
            # Check for skip input
            if self.check_for_skip():
                return None
                
            time.sleep(self.polling_interval)
        
        return None
    
    def map_buttons(self):
        """Guide user through mapping each button"""
        # Choose button list based on gamepad type
        if self.gamepad_type == 'xbox360':
            buttons = XBOX360_BUTTONS
            button_names = XBOX360_BUTTON_NAMES
        else:
            buttons = DS4_BUTTONS
            button_names = DS4_BUTTON_NAMES
            
        print("\n=== Button Mapping ===")
        print("Press each button when prompted. Press Enter to skip a button.")
        
        for button in buttons:
            # Skip mapping D-pad if we detect it uses a hat
            if button.startswith(("XUSB_GAMEPAD_DPAD_", "DS4_BUTTON_DPAD_")) and self.uses_hat_for_dpad:
                continue
                
            name = button_names[button]
            print(f"\nPress {name}")
            print("(or press Enter to skip)")
            
            # Check for D-pad buttons to detect if using hat
            is_dpad = button.startswith(("XUSB_GAMEPAD_DPAD_", "DS4_BUTTON_DPAD_"))
            
            if is_dpad and self.joystick.get_numhats() > 0:
                # Try hat for D-pad first
                hat_value = self.wait_for_hat_movement()
                if hat_value != (0, 0) and hat_value is not None:
                    # First hat press - detect that we're using a hat for D-pad
                    if not self.uses_hat_for_dpad:
                        print("D-pad uses hat control detected!")
                        self.uses_hat_for_dpad = True
                        
                    # Map this hat position to the D-pad button
                    if button.endswith("UP") and hat_value[1] == 1:
                        print(f"Mapped {name} to hat position (0, 1)")
                        self.hat_mapping["up"] = button
                    elif button.endswith("DOWN") and hat_value[1] == -1:
                        print(f"Mapped {name} to hat position (0, -1)")
                        self.hat_mapping["down"] = button
                    elif button.endswith("LEFT") and hat_value[0] == -1:
                        print(f"Mapped {name} to hat position (-1, 0)")
                        self.hat_mapping["left"] = button
                    elif button.endswith("RIGHT") and hat_value[0] == 1:
                        print(f"Mapped {name} to hat position (1, 0)")
                        self.hat_mapping["right"] = button
                
                    self.wait_for_button_release()
                    continue
            
            # Regular button mapping
            button_idx = self.wait_for_button_press()
            if button_idx is not None:
                print(f"Mapped {name} to button {button_idx}")
                self.button_mapping[button] = button_idx
            
            self.wait_for_button_release()
            
            # Check if we've been interrupted
            if self.interrupt_flag:
                return
        
        print("\nButton mapping completed!")
    
    def detect_axis_movement(self, axis_name, instruction, timeout=5.0, threshold=0.3):
        """
        Detect significant axis movement with improved feedback and direction detection
        
        Args:
            axis_name: The name of the axis being mapped
            instruction: Basic instruction to display to the user
            timeout: Time in seconds to wait for movement
            threshold: Minimum change to be considered significant
        """
        print(f"\n{instruction}")
        
        # Provide specific guidance based on axis type
        is_trigger = "trigger" in axis_name
        if "stick_y" in axis_name:
            print("IMPORTANT: Move the stick UPWARD (away from you)")
        elif "stick_x" in axis_name:
            print("IMPORTANT: Move the stick to the RIGHT")
        elif is_trigger:
            print("IMPORTANT: Press the trigger all the way down")
        
        print("You have 5 seconds... Starting in:")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        print("GO! Move and hold now...")
        
        # Capture initial axis values
        pygame.event.pump()
        initial_values = [self.joystick.get_axis(i) for i in range(self.joystick.get_numaxes())]
        
        start_time = time.time()
        max_changes = [0] * self.joystick.get_numaxes()
        direction_of_change = [0] * self.joystick.get_numaxes()  # Store direction of change
        best_axis = None
        best_value = 0
        
        while time.time() - start_time < timeout:
            pygame.event.pump()
            
            # Track changes for all axes
            for i in range(self.joystick.get_numaxes()):
                current = self.joystick.get_axis(i)
                change = current - initial_values[i]  # Keep sign for direction detection
                abs_change = abs(change)
                
                # Update max change and direction for this axis
                if abs_change > max_changes[i]:
                    max_changes[i] = abs_change
                    direction_of_change[i] = 1 if change > 0 else -1
                    
                    # Determine if this is a candidate based on axis type
                    is_candidate = abs_change > threshold
                    
                    # For triggers, prefer axes that move in positive direction (0 to 1)
                    if is_trigger and is_candidate:
                        if change > 0 and (best_axis is None or abs_change > max_changes[best_axis]):
                            best_axis = i
                            best_value = current
                    # For non-triggers, use the axis with largest change
                    elif is_candidate and (best_axis is None or abs_change > max_changes[best_axis]):
                        best_axis = i
                        best_value = current
            
            # Update progress indicator
            elapsed = time.time() - start_time
            progress = int((elapsed / timeout) * 10)
            sys.stdout.write("\r[" + "#" * progress + " " * (10 - progress) + "] ")
            if best_axis is not None:
                direction = "+" if direction_of_change[best_axis] > 0 else "-"
                sys.stdout.write(f"Detected axis {best_axis}: {direction}{max_changes[best_axis]:.2f}")
            sys.stdout.flush()
            
            time.sleep(self.polling_interval)
        
        print("\nTime's up!")
        
        if best_axis is not None:
            direction = "+" if direction_of_change[best_axis] > 0 else "-"
            print(f"Mapped to axis {best_axis} (value: {best_value:.2f}, change: {direction}{max_changes[best_axis]:.2f})")
            return best_axis, best_value, direction_of_change[best_axis]
        else:
            print("No significant movement detected")
            return None, None, None
    
    def map_axes(self):
        """Guide user through mapping each axis with improved usability"""
        print("\n=== Axis Mapping ===")
        print("Follow the prompts to map each axis correctly.")
        print("For each axis, you'll have 5 seconds to move and hold after the countdown.")
        
        # Map each axis
        for axis_name, axis_desc in AXIS_NAMES.items():
            
            # Wait for neutral position
            self.wait_for_neutral()
            
            # Allow retry if mapping fails
            while True:
                # Detect axis movement
                axis_idx, axis_value, direction = self.detect_axis_movement(
                    axis_name=axis_name,
                    instruction=f"Move {axis_desc}"
                )
                
                if axis_idx is not None:
                    self.axis_mapping[axis_name] = axis_idx
                    
                    # Special handling for Y-axis (inversion detection)
                    if axis_name.endswith('_y'):
                        # For Y-axis, moving UP should typically produce a negative value 
                        # in Xbox360 controllers and some DS4 controllers
                        is_up_negative = direction < 0  # Did moving up produce a negative value?
                        
                        print(f"\nWhen you moved the stick UP, it produced a {'NEGATIVE' if is_up_negative else 'POSITIVE'} value.")
                        
                        if self.gamepad_type == 'xbox360':
                            print("For Xbox controllers, UP should normally be NEGATIVE.")
                            inversion_needed = is_up_negative
                        else:  # DS4
                            print("For DualShock controllers, this can vary by game.")
                            inversion_needed = is_up_negative
                            
                        print(f"Based on testing, inversion is {'needed' if inversion_needed else 'NOT needed'}.")
                        print(f"Apply this recommendation? [Y/n]")
                        
                        response = input().lower()
                        # Default is to apply the recommendation
                        apply_recommendation = response != 'n'
                        
                        if axis_name == 'left_stick_y':
                            self.axis_mapping['invert_left_y'] = inversion_needed if apply_recommendation else not inversion_needed
                            print(f"Left Y-axis inversion set to: {self.axis_mapping['invert_left_y']}")
                        elif axis_name == 'right_stick_y':
                            self.axis_mapping['invert_right_y'] = inversion_needed if apply_recommendation else not inversion_needed
                            print(f"Right Y-axis inversion set to: {self.axis_mapping['invert_right_y']}")

                    # Successfully mapped
                    break
                else:
                    print("\nNo significant movement detected. Would you like to try again? [Y/n]")
                    if input().lower() == 'n':
                        print(f"Skipping {axis_desc}")
                        break

            # Check if we've been interrupted
            if self.interrupt_flag:
                return
        
        print("\nAxis mapping completed!")
    
    def verify_mapping(self):
        """Let user verify the mappings and make changes if needed"""
        print("\n=== Verify Mappings ===")
        
        # Show button mappings
        print("\nButton Mappings:")
        for button, idx in self.button_mapping.items():
            if self.gamepad_type == 'xbox360':
                name = XBOX360_BUTTON_NAMES[button]
            else:
                name = DS4_BUTTON_NAMES[button]
            print(f"{name} -> Button {idx}")
            
        # Show hat mappings if used
        if self.uses_hat_for_dpad:
            print("\nD-Pad Hat Mappings:")
            for direction, button in self.hat_mapping.items():
                print(f"D-Pad {direction} -> {button}")
            
        # Show axis mappings
        print("\nAxis Mappings:")
        for axis_name, idx in self.axis_mapping.items():
            if axis_name not in ['invert_left_y', 'invert_right_y']:
                print(f"{axis_name} -> Axis {idx}")
                
        # Inversion settings
        print("\nInversion Settings:")
        print(f"Invert Left Y-Axis: {self.axis_mapping.get('invert_left_y', False)}")
        print(f"Invert Right Y-Axis: {self.axis_mapping.get('invert_right_y', False)}")
            
        print("\nDo you want to make any changes? (y/n)")
        if input().lower() == 'y':
            self.manual_adjustments()
    
    def manual_adjustments(self):
        """Allow manual adjustments to mappings"""
        while True:
            print("\nWhat would you like to adjust?")
            print("1. Button mapping")
            print("2. Axis mapping")
            print("3. Finish adjustments")
            
            choice = input("Enter choice (1-3): ")
            
            if choice == '1':
                self.adjust_button_mapping()
            elif choice == '2':
                self.adjust_axis_mapping()
            elif choice == '3':
                break
            else:
                print("Invalid choice. Please enter 1-3.")
    
    def adjust_button_mapping(self):
        """Allow manual adjustment of button mappings"""
        if self.gamepad_type == 'xbox360':
            buttons = XBOX360_BUTTONS
            button_names = XBOX360_BUTTON_NAMES
        else:
            buttons = DS4_BUTTONS
            button_names = DS4_BUTTON_NAMES
            
        print("\nSelect button to adjust:")
        for i, button in enumerate(buttons):
            if button in self.button_mapping:
                idx = self.button_mapping[button]
                print(f"{i+1}. {button_names[button]} (currently mapped to button {idx})")
            else:
                print(f"{i+1}. {button_names[button]} (not mapped)")
                
        print(f"{len(buttons)+1}. Back")
        
        try:
            choice = int(input("Enter choice: "))
            if choice == len(buttons)+1:
                return
                
            if 1 <= choice <= len(buttons):
                button = buttons[choice-1]
                print(f"Enter new button index for {button_names[button]}:")
                idx = int(input())
                if 0 <= idx < self.joystick.get_numbuttons():
                    self.button_mapping[button] = idx
                    print(f"Updated mapping: {button_names[button]} -> Button {idx}")
                else:
                    print("Invalid button index")
        except ValueError:
            print("Invalid input")
    
    def adjust_axis_mapping(self):
        """Allow manual adjustment of axis mappings"""
        print("\nSelect axis to adjust:")
        axes = list(AXIS_NAMES.keys())
        for i, axis_name in enumerate(axes):
            if axis_name in self.axis_mapping:
                idx = self.axis_mapping[axis_name]
                print(f"{i+1}. {AXIS_NAMES[axis_name]} (currently mapped to axis {idx})")
            else:
                print(f"{i+1}. {AXIS_NAMES[axis_name]} (not mapped)")
                
        print(f"{len(axes)+1}. Back")
        
        try:
            choice = int(input("Enter choice: "))
            if choice == len(axes)+1:
                return
                
            if 1 <= choice <= len(axes):
                axis_name = axes[choice-1]
                print(f"Enter new axis index for {AXIS_NAMES[axis_name]}:")
                idx = int(input())
                if 0 <= idx < self.joystick.get_numaxes():
                    self.axis_mapping[axis_name] = idx
                    print(f"Updated mapping: {AXIS_NAMES[axis_name]} -> Axis {idx}")
                else:
                    print("Invalid axis index")
        except ValueError:
            print("Invalid input")
    
    def generate_config(self):
        """Generate configuration file for server"""
        # Check if file exists
        if os.path.exists(self.output_path):
            print(f"\nWarning: {self.output_path} already exists.")
            print("What would you like to do?")
            print("1. Overwrite")
            print("2. Choose a new filename")
            
            choice = input("Enter choice (1 or 2): ")
            if choice == '2':
                print("Enter new filename:")
                new_path = input()
                if new_path:
                    self.output_path = new_path
                else:
                    print("Using default filename with timestamp")
                    timestamp = int(time.time())
                    base, ext = os.path.splitext(self.output_path)
                    self.output_path = f"{base}_{timestamp}{ext}"
        
        # Create config object
        config = configparser.ConfigParser()
        
        # Server section
        config.add_section('server')
        config.set('server', 'host', '127.0.0.1')
        config.set('server', 'port', '9999')
        config.set('server', 'protocol', 'tcp')
        
        # Gamepad section
        config.add_section('vgamepad')
        config.set('vgamepad', 'type', self.gamepad_type)
        
        # Button mapping section
        section_name = f'button_mapping_{self.gamepad_type}'
        config.add_section(section_name)
        
        # Convert button mapping from {button_name: idx} to {idx: button_name}
        idx_to_button = {}
        for button, idx in self.button_mapping.items():
            idx_to_button[str(idx)] = button
            
        # Add each mapped button to config
        for idx, button in idx_to_button.items():
            config.set(section_name, idx, button)
            
        # Add D-pad hat mapping if used
        if self.uses_hat_for_dpad and self.hat_mapping:
            hat_section = f'{section_name}_hat'
            config.add_section(hat_section)
            for direction, button in self.hat_mapping.items():
                config.set(hat_section, f'hat_{direction}', button)
        
        # Axis mapping section
        config.add_section('axis_mapping')
        axis_mapping_filtered = {
            k: v
            for k, v in self.axis_mapping.items()
            if k not in ["invert_left_y", "invert_right_y"]
        }
        for axis_name, idx in axis_mapping_filtered.items():
            config.set('axis_mapping', axis_name, str(idx))
        
        # Axis options section
        config.add_section('axis_options')
        config.set('axis_options', 'dead_zone', '0.1')
        config.set('axis_options', 'trigger_threshold', '0.05')
        config.set('axis_options', 'invert_left_y', str(self.axis_mapping.get('invert_left_y', False)).lower())
        config.set('axis_options', 'invert_right_y', str(self.axis_mapping.get('invert_right_y', False)).lower())
        
        # Write to file
        with open(self.output_path, 'w') as config_file:
            config.write(config_file)
            
        print(f"\nConfiguration saved to {self.output_path}")
        print("You can use this file with your server.py using the --config option:")
        print(f"python server.py --config {self.output_path}")
    
    def run(self):
        """Run the mapping process"""
        try:
            print("=== Xbox360/DS4 Controller Key Mapper ===")
            print("This tool will guide you through mapping your controller buttons.")
            print("Press Ctrl+C at any time to exit.")
            
            if not self.detect_controller():
                return
                
            self.map_buttons()
            self.map_axes()
            self.verify_mapping()
            self.generate_config()
            
            print("\nMapping completed successfully!")
            
        except KeyboardInterrupt:
            print("\nMapping interrupted by user.")
            self.interrupt_flag = True
            if input("\nWould you like to save the partial mapping? (y/n): ").lower() == 'y':
                self.generate_config()
        finally:
            # Clean up pygame
            pygame.quit()


def main():
    parser = argparse.ArgumentParser(description="Xbox360/DS4 Controller Key Mapper")
    parser.add_argument('--output', type=str, default='controller_config.ini',
                        help='Output configuration file path')
    parser.add_argument('--polling-interval', type=float, default=0.1,
                        help='Polling interval in seconds (higher values use less CPU)')
    args = parser.parse_args()
    
    # Start the mapping process
    mapper = ControllerMapper(args.output, args.polling_interval)
    mapper.run()


if __name__ == "__main__":
    main()
