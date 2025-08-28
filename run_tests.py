#!/usr/bin/env python3
"""
Automated Test Runner for Anki Review Nudger

This script performs automated checks to verify the addon is working correctly.
Run this while Anki is closed to check configuration and file integrity.

Usage: python run_tests.py
"""

import json
import os
import sys
from pathlib import Path
import importlib.util

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.addon_dir = Path(__file__).parent
        
    def test(self, name, condition, message=""):
        """Run a single test"""
        if condition:
            print(f"✅ {name}")
            self.passed += 1
        else:
            print(f"❌ {name}: {message}")
            self.failed += 1
    
    def info(self, message):
        """Print info message"""
        print(f"ℹ️  {message}")
    
    def warning(self, message):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    def run_all_tests(self):
        """Run all tests"""
        print("🧪 Anki Review Nudger - Automated Tests\n")
        
        self.test_file_structure()
        self.test_main_code()
        self.test_configuration()
        self.test_imports()
        self.test_helper_files()
        
        print(f"\n📊 Test Results: {self.passed} passed, {self.failed} failed")
        
        if self.failed == 0:
            print("🎉 All tests passed! Your addon should work correctly.")
            print("\n🚀 Next steps:")
            print("   1. Start Anki")
            print("   2. Run: python test_config.py fast")
            print("   3. Restart Anki")
            print("   4. Wait 15 seconds for popup")
        else:
            print("❌ Some tests failed. Check the issues above.")
        
        return self.failed == 0
    
    def test_file_structure(self):
        """Test that all required files exist"""
        self.info("Testing file structure...")
        
        required_files = [
            "__init__.py",
            "test_guide.md",
            "test_config.py", 
            "README.md",
            "run_tests.py"
        ]
        
        for file in required_files:
            file_path = self.addon_dir / file
            self.test(
                f"File exists: {file}",
                file_path.exists(),
                f"Missing file: {file_path}"
            )
    
    def test_main_code(self):
        """Test the main addon code"""
        self.info("Testing main addon code...")
        
        init_file = self.addon_dir / "__init__.py"
        if not init_file.exists():
            self.test("Main code file", False, "__init__.py not found")
            return
        
        try:
            content = init_file.read_text(encoding='utf-8')
            
            # Check for key components
            required_components = [
                ("ReviewNudger class", "class ReviewNudger"),
                ("Timer setup", "QTimer"),
                ("Configuration handling", "get_cfg"),
                ("Menu installation", "_install_menu"),
                ("Hooks registration", "gui_hooks"),
                ("Profile initialization", "profile_did_open")
            ]
            
            for name, pattern in required_components:
                self.test(
                    f"Code contains: {name}",
                    pattern in content,
                    f"Missing: {pattern}"
                )
            
            # Check for potential issues
            if "import logging" in content:
                self.warning("Debug mode detected - remember to use normal version for production")
            
        except Exception as e:
            self.test("Read main code", False, f"Error reading __init__.py: {e}")
    
    def test_configuration(self):
        """Test configuration file if it exists"""
        self.info("Testing configuration...")
        
        config_file = self.addon_dir / "config.json"
        
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.test("Config file is valid JSON", True)
                
                # Check required keys
                required_keys = ["interval_minutes", "snooze_minutes", "quiet_hours", "enabled"]
                for key in required_keys:
                    self.test(
                        f"Config has key: {key}",
                        key in config,
                        f"Missing config key: {key}"
                    )
                
                # Check value types and ranges
                if "interval_minutes" in config:
                    interval = config["interval_minutes"]
                    self.test(
                        "Interval is positive number",
                        isinstance(interval, (int, float)) and interval > 0,
                        f"Invalid interval: {interval}"
                    )
                    
                    if interval < 1:
                        self.info(f"Fast test mode detected: {interval} minutes")
                
                if "quiet_hours" in config:
                    quiet = config["quiet_hours"]
                    self.test(
                        "Quiet hours is dict",
                        isinstance(quiet, dict),
                        f"Invalid quiet_hours: {quiet}"
                    )
                    
                    if isinstance(quiet, dict):
                        self.test(
                            "Quiet hours has start/end",
                            "start" in quiet and "end" in quiet,
                            "Missing start/end in quiet_hours"
                        )
                
            except json.JSONDecodeError as e:
                self.test("Config file is valid JSON", False, f"JSON error: {e}")
            except Exception as e:
                self.test("Read config file", False, f"Error: {e}")
        else:
            self.info("No config.json found (will use defaults)")
    
    def test_imports(self):
        """Test that required modules can be imported"""
        self.info("Testing imports...")
        
        # Test if we can load the main module
        init_file = self.addon_dir / "__init__.py"
        if init_file.exists():
            try:
                spec = importlib.util.spec_from_file_location("addon", init_file)
                if spec and spec.loader:
                    # Don't actually import (might cause issues), just check syntax
                    with open(init_file, 'r', encoding='utf-8') as f:
                        code = f.read()
                    
                    compile(code, str(init_file), 'exec')
                    self.test("Main code compiles", True)
                else:
                    self.test("Main code can be loaded", False, "Could not create module spec")
            except SyntaxError as e:
                self.test("Main code syntax", False, f"Syntax error: {e}")
            except Exception as e:
                self.test("Main code compilation", False, f"Compilation error: {e}")
    
    def test_helper_files(self):
        """Test helper files"""
        self.info("Testing helper files...")
        
        # Test test_config.py
        test_config = self.addon_dir / "test_config.py"
        if test_config.exists():
            try:
                content = test_config.read_text(encoding='utf-8')
                self.test(
                    "Test config script has CONFIGS",
                    "CONFIGS = {" in content,
                    "Missing CONFIGS dictionary"
                )
                
                self.test(
                    "Test config has fast mode",
                    '"fast"' in content,
                    "Missing fast test mode"
                )
            except Exception as e:
                self.test("Read test config", False, f"Error: {e}")

def main():
    """Main entry point"""
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()