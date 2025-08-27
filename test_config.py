#!/usr/bin/env python3
"""
Test Configuration Helper for Anki Review Nudger

This script helps set up different test configurations for the addon.
Run this script to quickly switch between normal and test configurations.

Usage:
1. Close Anki completely
2. Run this script with desired test mode
3. Start Anki to test

Test modes:
- fast: Very short intervals for rapid testing (15 seconds)
- normal: Default production settings
- quiet: Test quiet hours functionality
- disabled: Test disabled state
"""

import json
import os
import sys
from pathlib import Path

# Configuration templates
CONFIGS = {
    "fast": {
        "interval_minutes": 0.25,  # 15 seconds
        "snooze_minutes": 0.1,     # 6 seconds
        "quiet_hours": {"start": 25, "end": 26},  # Never quiet (invalid hours)
        "enabled": True
    },
    "normal": {
        "interval_minutes": 30,
        "snooze_minutes": 5,
        "quiet_hours": {"start": 22, "end": 7},
        "enabled": True
    },
    "quiet": {
        "interval_minutes": 0.5,   # 30 seconds for testing
        "snooze_minutes": 0.1,
        "quiet_hours": {"start": 0, "end": 23},  # Always quiet
        "enabled": True
    },
    "disabled": {
        "interval_minutes": 0.25,
        "snooze_minutes": 0.1,
        "quiet_hours": {"start": 22, "end": 7},
        "enabled": False
    }
}

def find_addon_config_path():
    """Find the addon configuration file path"""
    # Common Anki addon paths
    possible_paths = [
        Path.home() / "AppData" / "Roaming" / "Anki2" / "addons21",
        Path.home() / ".local" / "share" / "Anki2" / "addons21",
        Path.home() / "Library" / "Application Support" / "Anki2" / "addons21"
    ]
    
    for base_path in possible_paths:
        if base_path.exists():
            # Look for our addon folder
            for addon_dir in base_path.iterdir():
                if addon_dir.is_dir():
                    init_file = addon_dir / "__init__.py"
                    if init_file.exists():
                        # Check if this is our addon by looking for our code
                        try:
                            content = init_file.read_text(encoding='utf-8')
                            if "ReviewNudger" in content and "forced_review" in content:
                                config_file = addon_dir / "config.json"
                                return config_file
                        except Exception:
                            continue
    return None

def set_config(mode):
    """Set the addon configuration to the specified test mode"""
    if mode not in CONFIGS:
        print(f"Unknown mode: {mode}")
        print(f"Available modes: {', '.join(CONFIGS.keys())}")
        return False
    
    config_path = find_addon_config_path()
    if not config_path:
        print("Could not find addon configuration file.")
        print("Make sure the addon is installed and Anki has been run at least once.")
        return False
    
    try:
        # Write the new configuration
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(CONFIGS[mode], f, indent=2)
        
        print(f"✅ Configuration set to '{mode}' mode")
        print(f"📁 Config file: {config_path}")
        print(f"⚙️  Settings: {json.dumps(CONFIGS[mode], indent=2)}")
        print("\n🔄 Please restart Anki for changes to take effect.")
        
        if mode == "fast":
            print("\n⚡ Fast mode active:")
            print("   - Popup every 15 seconds")
            print("   - Snooze for 6 seconds")
            print("   - No quiet hours")
        elif mode == "quiet":
            print("\n🔇 Quiet mode active:")
            print("   - Always in quiet hours (no popups should appear)")
        elif mode == "disabled":
            print("\n❌ Disabled mode active:")
            print("   - Addon is disabled (no popups should appear)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error writing configuration: {e}")
        return False

def show_current_config():
    """Show the current configuration"""
    config_path = find_addon_config_path()
    if not config_path or not config_path.exists():
        print("No configuration file found.")
        return
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"📁 Config file: {config_path}")
        print(f"⚙️  Current settings:")
        print(json.dumps(config, indent=2))
        
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")

def main():
    if len(sys.argv) != 2:
        print("Anki Review Nudger - Test Configuration Helper")
        print("\nUsage: python test_config.py <mode>")
        print(f"\nAvailable modes:")
        for mode, config in CONFIGS.items():
            print(f"  {mode:8} - {config.get('interval_minutes')*60:.0f}s intervals, enabled: {config['enabled']}")
        print("\nOther commands:")
        print("  show     - Show current configuration")
        return
    
    mode = sys.argv[1].lower()
    
    if mode == "show":
        show_current_config()
    else:
        set_config(mode)

if __name__ == "__main__":
    main()