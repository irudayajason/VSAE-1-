# VSAE UI Features Guide

## Visual Indicators for Hindsight and CascadeFlow

This guide explains how users can see and interact with Hindsight and CascadeFlow features in the VSAE UI.

---

## 1. Hindsight Status Indicator

### Location
Top-right corner of the screen, next to the model status badge.

### What It Shows

#### ✅ **Hindsight Active** (Green checkmark)
- **Meaning**: Hindsight SDK is properly configured and running
- **Features Enabled**:
  - Semantic overlap detection
  - Ablation history tracking
  - Perplexity degradation warnings
- **Tooltip**: "Hindsight SDK is active - overlap detection enabled"

#### ⊖ **Hindsight Disabled** (Gray circle with line)
- **Meaning**: Hindsight SDK is not configured
- **Features Disabled**:
  - No overlap detection
  - No ablation history
  - No warnings for similar concepts
- **Tooltip**: "Hindsight SDK not configured - set HINDSIGHT_API_KEY to enable"

### How to Enable Hindsight
1. Get API key from https://hindsight.dev
2. Edit `.env` file: `HINDSIGHT_API_KEY=your_key_here`
3. Restart the server
4. Indicator will turn green with checkmark

---

## 2. CascadeFlow Toggle

### Location
In the Ablation Engine drawer, below the "Strength" dropdown.

### What It Does
Enables automatic recovery if ablation degrades model performance too much.

### Visual Elements

#### Toggle Switch
- **Checked (Default)**: CascadeFlow is enabled
- **Unchecked**: Standard ablation without automatic recovery

#### Label
```
🛡️ Enable CascadeFlow (Auto-Recovery)
```

#### Description
```
Automatically retries with shifted layers if perplexity degrades >15%
```

### How It Works
1. **Initial Ablation**: Applies ablation to selected layers
2. **Perplexity Check**: Measures model degradation
3. **Threshold Check**: If degradation > 15%:
   - Automatically rolls back
   - Shifts layers by -2 (tries earlier layers)
   - If that fails, shifts by +2 (tries later layers)
4. **Result**: Keeps the best configuration or reports failure

---

## 3. Overlap Warning Modal (Hindsight Feature)

### When It Appears
When you try to ablate a concept that's semantically similar to a previously ablated concept.

### Visual Design
- **Enhanced border**: Gold glowing border with shimmer animation
- **Warning icon**: ⚠️ in header
- **Color coding**: Red-tinted background for warning message

### Information Displayed

#### Warning Message
```
Warning: The new concept overlaps 85% with historical deletion 'Harry Potter'. 
Stacking these ablations historically degraded perplexity by 18%. Proceed?
```

#### Details Panel
- **Past Concept**: Shows what was previously ablated
- **Similarity**: Percentage of semantic overlap (0-100%)
- **Historical Impact**: Expected perplexity degradation based on past data

### User Actions
1. **Cancel**: Closes modal, cancels ablation
2. **Proceed Anyway**: Continues with ablation despite warning

---

## 4. CascadeFlow Status Cards

### When They Appear
After an ablation completes, if CascadeFlow was triggered.

### Visual Design
- **Gold accent**: Highlighted with gold color
- **🔄 Icon**: Indicates automatic recovery was used
- **Success badge**: Green border when successful

### Information Displayed

#### CascadeFlow Activated Card
```
🔄 CascadeFlow Activated

Initial ablation exceeded 15% degradation threshold.
Automatically shifted layers by -2 and retried.
Result: 12.3% degradation (within threshold)

Original layers: 10, 15, 20, 25
Final layers: 8, 13, 18, 23
```

#### Cascade Failure Card (if all attempts fail)
```
❌ CascadeFlow Failed

Initial ablation and all cascade retries exceeded 15% degradation threshold

Cascade Attempts:
Shift -2: Layers 8, 13, 18 → 18.5% degradation ✗
Shift +2: Layers 12, 17, 22 → 16.2% degradation ✗
```

---

## 5. Smooth Ablation Experience (No Glitching)

### Improvements Made

#### Before
- UI would freeze or glitch during ablation
- Status cards would jump around
- Buttons would flicker

#### After
- **Smooth transitions**: All status cards fade in smoothly
- **No layout shifts**: Fixed minimum heights prevent jumping
- **Loading states**: Clear visual feedback during processing
- **Optimized animations**: Hardware-accelerated CSS transitions

### Technical Details
- `will-change` properties for GPU acceleration
- Opacity transitions instead of display changes
- Fixed container heights during operations
- Debounced state updates

---

## 6. Testing the Features

### Test Hindsight Overlap Detection

1. **First Ablation**:
   ```
   Concept: "Harry Potter lives at 4 Privet Drive"
   ```
   - Should complete normally
   - No warning modal

2. **Second Ablation** (similar concept):
   ```
   Concept: "Hermione Granger is a wizard"
   ```
   - **Expected**: Overlap warning modal appears
   - Shows similarity percentage (likely 70-85%)
   - Displays historical impact data

3. **Third Ablation** (unrelated concept):
   ```
   Concept: "Python programming language"
   ```
   - Should complete normally
   - No warning (different semantic space)

### Test CascadeFlow

1. **Enable CascadeFlow**: Check the toggle in Ablation Engine

2. **Aggressive Ablation**:
   ```
   Concept: "Complex technical concept"
   Layers: 8 (aggressive)
   Strength: 1.0
   ```

3. **Expected Behavior**:
   - If initial ablation degrades >15%:
     - Status card shows "🔄 CascadeFlow Activated"
     - Displays original vs final layers
     - Shows degradation percentage
   - If all attempts fail:
     - Shows "CascadeFlow Failed" card
     - Lists all attempts with results

### Test UI Smoothness

1. **Open Ablation Drawer**: Should slide in smoothly
2. **Run Ablation**: Watch status cards appear
   - Should fade in one by one
   - No jumping or layout shifts
   - Smooth transitions between states
3. **Close Drawer**: Should slide out smoothly

---

## 7. Visual Feedback Summary

| Feature | Visual Indicator | Location | Color |
|---------|-----------------|----------|-------|
| Hindsight Active | ✅ Green checkmark | Top-right | Green |
| Hindsight Disabled | ⊖ Gray circle | Top-right | Gray |
| CascadeFlow Enabled | ✓ Checked toggle | Ablation drawer | Gold |
| Overlap Warning | ⚠️ Modal | Center screen | Gold border, red accent |
| Cascade Success | 🔄 Status card | Ablation results | Gold/Green |
| Cascade Failure | ❌ Status card | Ablation results | Red |

---

## 8. Keyboard Shortcuts

- **Escape**: Close overlap warning modal
- **Enter**: Proceed with ablation (when modal is open)
- **Tab**: Navigate between modal buttons

---

## 9. Accessibility Features

- **Tooltips**: Hover over indicators for detailed information
- **Color coding**: Consistent use of colors (green=good, red=warning, gold=feature)
- **Clear labels**: All features have descriptive text
- **Smooth animations**: Reduced motion for better accessibility
- **High contrast**: Dark theme with sufficient contrast ratios

---

## 10. Troubleshooting

### Hindsight Indicator Stays Gray
**Problem**: Indicator shows "Hindsight Disabled" even after setting API key

**Solutions**:
1. Check `.env` file has correct format: `HINDSIGHT_API_KEY=your_key`
2. Restart the server: `uvicorn backend.main:app --reload`
3. Check browser console for errors
4. Verify API key is valid at https://hindsight.dev

### CascadeFlow Not Triggering
**Problem**: Ablation completes without cascade even with high degradation

**Solutions**:
1. Ensure toggle is checked (blue checkmark)
2. Check if degradation actually exceeded 15%
3. Look for "CascadeFlow Failed" card (all attempts may have failed)
4. Try with more aggressive settings (8 layers, strength 1.0)

### Overlap Warning Not Appearing
**Problem**: Similar concepts don't trigger warning

**Solutions**:
1. Verify Hindsight is active (green checkmark)
2. Concepts must be semantically similar (>70% similarity)
3. First ablation won't show warning (no history yet)
4. Check backend logs for Hindsight errors

### UI Still Glitching
**Problem**: Status cards jump or flicker

**Solutions**:
1. Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
2. Clear browser cache
3. Check if CSS file loaded correctly (view source)
4. Try different browser (Chrome/Firefox/Safari)

---

## 11. Best Practices

### For Hindsight
- ✅ Enable Hindsight for production use
- ✅ Pay attention to overlap warnings
- ✅ Review historical impact data before proceeding
- ❌ Don't ignore high similarity warnings (>85%)

### For CascadeFlow
- ✅ Keep enabled by default (checked)
- ✅ Use for experimental ablations
- ✅ Review cascade attempts if triggered
- ❌ Don't disable for aggressive ablations

### For UI Experience
- ✅ Wait for status cards to fully load
- ✅ Read all information before proceeding
- ✅ Use tooltips for additional context
- ❌ Don't spam the ablate button

---

## 12. Advanced Features

### Custom Cascade Threshold
Currently set to 15% by default. To customize:

1. Edit `frontend/app.js`
2. Find: `const cascadeThreshold = cascadeEnabled ? 15.0 : null;`
3. Change `15.0` to your desired percentage
4. Refresh browser

### Hindsight Similarity Threshold
Currently set to 70% by default. To customize:

1. Edit `backend/ablation.py`
2. Find: `similarity_threshold=0.70`
3. Change to your desired threshold (0.0-1.0)
4. Restart server

---

## Summary

The VSAE UI now provides clear visual feedback for:
- ✅ Hindsight status and overlap detection
- ✅ CascadeFlow automatic recovery
- ✅ Smooth, glitch-free ablation experience
- ✅ Enhanced warning modals with detailed information
- ✅ Real-time status updates during operations

All features are designed to be intuitive and provide maximum transparency about what's happening during ablation operations.