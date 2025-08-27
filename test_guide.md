# Testing Guide for Anki Review Nudger Addon

## Overview
This addon forces periodic review sessions every 30 minutes (configurable) with features like snoozing, quiet hours, and daily disable options.

## Manual Testing Steps

### 1. Basic Installation Test
1. Restart Anki after installing the addon
2. Check that no errors appear in the console
3. Verify the addon appears in Tools menu with three new options:
   - "Forced Review: Toggle Enabled"
   - "Forced Review: Snooze 5m" 
   - "Forced Review: Reset Today"

### 2. Configuration Test
1. Go to Tools → Add-ons → Select your addon → Config
2. Verify default configuration loads:
   ```json
   {
     "interval_minutes": 30,
     "snooze_minutes": 5,
     "quiet_hours": {"start": 22, "end": 7},
     "enabled": true
   }
   ```
3. Modify values and restart Anki to ensure they persist

### 3. Timer Functionality Test
**Note: For faster testing, temporarily change `interval_minutes` to 1 in config**

1. **Initial Timer Test:**
   - Start Anki and wait for the configured interval
   - Verify popup appears with 4 buttons: "Start Review", "Snooze 5m", "Disable for Today", "Cancel"

2. **Start Review Button:**
   - Click "Start Review"
   - Verify it navigates to deck overview and attempts to start study session
   - Timer should reset for next interval

3. **Snooze Button:**
   - Click "Snooze 5m"
   - Verify tooltip shows "Snoozed for 5 minutes"
   - Wait 5 minutes, popup should appear again

4. **Disable for Today:**
   - Click "Disable for Today"
   - Verify tooltip shows "Disabled for today"
   - No more popups should appear until next day

5. **Cancel Button:**
   - Click "Cancel"
   - Popup should reappear in 2 minutes

### 4. Activity Detection Test
1. Start a review session manually
2. Answer some cards
3. Verify that answering cards resets the timer (no popup during active review)
4. Stop reviewing and wait for interval - popup should appear

### 5. State Change Test
1. Switch between different Anki states (deck browser, overview, review)
2. Verify no popup appears while in review state
3. Verify timer resets when entering review state

### 6. Quiet Hours Test
1. Set quiet hours in config (e.g., current time ± 1 hour)
2. Verify no popups appear during quiet hours
3. Change system time to outside quiet hours
4. Verify popups resume

### 7. Menu Actions Test
1. **Toggle Enabled:**
   - Use Tools → "Forced Review: Toggle Enabled"
   - Verify tooltip shows "ON" or "OFF"
   - When OFF, no popups should appear

2. **Quick Snooze:**
   - Use Tools → "Forced Review: Snooze 5m"
   - Verify tooltip and 5-minute delay

3. **Reset Today:**
   - After disabling for today, use "Reset Today"
   - Verify functionality resumes

## Automated Testing Ideas

### Quick Test Script
Create a test configuration with very short intervals for rapid testing:

```json
{
  "interval_minutes": 0.25,
  "snooze_minutes": 0.1,
  "quiet_hours": {"start": 25, "end": 26},
  "enabled": true
}
```

### Debug Mode
Add debug logging by temporarily modifying the code:

```python
# Add at top of file
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add debug statements in key methods
def _on_tick(self):
    logger.debug(f"Timer tick - enabled: {self.cfg.get('enabled')}, state: {mw.state}")
    # ... rest of method
```

## Common Issues to Test

1. **Profile switching:** Test with multiple Anki profiles
2. **Anki restart:** Verify addon survives Anki restarts
3. **Config corruption:** Test with invalid JSON in config
4. **Edge cases:** Test around midnight for quiet hours
5. **Performance:** Verify 15-second timer doesn't impact Anki performance

## Expected Behavior Summary

- ✅ Popup appears every 30 minutes (or configured interval)
- ✅ No popup during active review sessions
- ✅ No popup during quiet hours
- ✅ Snooze delays popup by configured minutes
- ✅ Daily disable prevents all popups until next day
- ✅ Menu actions work correctly
- ✅ Configuration persists across restarts
- ✅ Timer resets on review activity

## Troubleshooting

If addon doesn't work:
1. Check Anki console for error messages (Help → Debug Console)
2. Verify addon is enabled in Tools → Add-ons
3. Check configuration is valid JSON
4. Restart Anki completely
5. Test with default configuration first