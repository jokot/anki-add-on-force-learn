# Anki Review Nudger - Testing Documentation

This addon forces you to review your Anki deck every 30 minutes (configurable) with smart features like snoozing, quiet hours, and daily disable options.

## 🚀 Quick Start Testing

### Method 1: Fast Testing (Recommended)
1. **Close Anki completely**
2. **Run the test configuration script:**
   ```bash
   python test_config.py fast
   ```
3. **Start Anki**
4. **Wait 15 seconds** - you should see a popup!

### Method 2: Manual Configuration
1. Go to **Tools → Add-ons → [Your Addon] → Config**
2. Change `"interval_minutes"` to `0.25` (15 seconds)
3. Restart Anki
4. Wait 15 seconds for the popup

## 📁 Testing Files Created

- **`test_guide.md`** - Comprehensive manual testing guide
- **`test_config.py`** - Quick configuration switcher for different test modes
- **`debug_version.py`** - Debug version with detailed logging
- **`README.md`** - This file

## 🛠️ Test Configuration Tool

The `test_config.py` script provides several test modes:

```bash
# Fast testing (15-second intervals)
python test_config.py fast

# Normal production settings
python test_config.py normal

# Test quiet hours (always quiet)
python test_config.py quiet

# Test disabled state
python test_config.py disabled

# Show current configuration
python test_config.py show
```

## 🐛 Debug Mode

For detailed troubleshooting:

1. **Backup your current `__init__.py`:**
   ```bash
   copy __init__.py __init__.py.backup
   ```

2. **Replace with debug version:**
   ```bash
   copy debug_version.py __init__.py
   ```

3. **Restart Anki**

4. **Check debug output:**
   - Console output in Anki
   - Log file: `anki_nudger_debug.log`
   - New menu item: "Forced Review: Show Debug Info"

5. **Restore original when done:**
   ```bash
   copy __init__.py.backup __init__.py
   ```

## ✅ What to Test

### Core Functionality
- [ ] Popup appears at configured intervals
- [ ] "Start Review" button works
- [ ] "Snooze" delays popup correctly
- [ ] "Disable for Today" stops popups
- [ ] "Cancel" shows popup again in 2 minutes

### Smart Features
- [ ] No popup during active review sessions
- [ ] No popup during quiet hours
- [ ] Timer resets when answering cards
- [ ] Menu actions work (Tools menu)

### Edge Cases
- [ ] Configuration changes persist
- [ ] Works after Anki restart
- [ ] Handles profile switching
- [ ] Works around midnight (quiet hours)

## 🔧 Menu Actions

The addon adds these items to the **Tools** menu:

- **"Forced Review: Toggle Enabled"** - Turn addon on/off
- **"Forced Review: Snooze 5m"** - Quick snooze
- **"Forced Review: Reset Today"** - Re-enable after daily disable
- **"Forced Review: Show Debug Info"** (debug mode only)

## ⚙️ Configuration Options

```json
{
  "interval_minutes": 30,     // How often to show popup
  "snooze_minutes": 5,        // Snooze duration
  "quiet_hours": {            // No popups during these hours
    "start": 22,              // 10 PM
    "end": 7                  // 7 AM
  },
  "enabled": true             // Master enable/disable
}
```

## 🚨 Troubleshooting

### Popup Not Appearing?
1. Check if addon is enabled: Tools → Add-ons
2. Verify configuration is valid JSON
3. Check if you're in quiet hours
4. Try "Reset Today" from Tools menu
5. Use debug mode for detailed logging

### Console Errors?
1. Check Anki console: Help → Debug Console
2. Look for Python errors
3. Verify all imports are working
4. Try with default configuration

### Performance Issues?
1. The addon checks every 15 seconds (lightweight)
2. No impact during normal Anki usage
3. Debug mode adds logging overhead

## 📊 Expected Behavior

| Scenario | Expected Result |
|----------|----------------|
| Normal use | Popup every 30 minutes |
| During review | No popup |
| Quiet hours | No popup |
| Disabled | No popup |
| After snooze | Popup after snooze time |
| After "Disable Today" | No popup until tomorrow |
| After answering cards | Timer resets |

## 🎯 Testing Checklist

### Quick Test (5 minutes)
- [ ] Set fast mode: `python test_config.py fast`
- [ ] Restart Anki
- [ ] Wait 15 seconds for popup
- [ ] Test each button (Start, Snooze, Disable, Cancel)
- [ ] Check menu actions work

### Full Test (30 minutes)
- [ ] Follow complete `test_guide.md`
- [ ] Test all configurations
- [ ] Test edge cases
- [ ] Verify persistence across restarts

### Debug Test (when issues occur)
- [ ] Enable debug mode
- [ ] Check console output
- [ ] Review log file
- [ ] Use "Show Debug Info" menu

## 💡 Tips

- **Always close Anki completely** when changing configurations
- **Use fast mode** for quick testing cycles
- **Check the console** for any error messages
- **Test with default settings first** if having issues
- **Use debug mode** when troubleshooting

## 🔄 Restoring Normal Operation

After testing:

1. **Restore normal config:**
   ```bash
   python test_config.py normal
   ```

2. **If using debug mode, restore original:**
   ```bash
   copy __init__.py.backup __init__.py
   ```

3. **Restart Anki**

Your addon should now work normally with 30-minute intervals!