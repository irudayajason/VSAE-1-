# Step-by-Step Testing Guide for Hindsight and CascadeFlow

## Prerequisites

Before testing, ensure:
1. ✅ Server is running: `uvicorn backend.main:app --reload`
2. ✅ Browser is open at: `http://localhost:8000`
3. ✅ You have a Hindsight API key in `.env` (optional — local overlap detection works without it)

---

## Part 1: Setting Up Hindsight

### Step 1: Add API Key (Optional)

1. **Open `.env` file** in the project root
2. **Add your API key**:
   ```
   HINDSIGHT_API_KEY=your_actual_api_key_here
   ```
3. **Save the file**
4. **Restart the server**:
   - Stop server (Ctrl+C)
   - Start again: `uvicorn backend.main:app --reload`

> **Note:** Even without a Hindsight API key, overlap detection works via the local file-backed history (`ablation_history.json`). The Hindsight cloud API is used as an optional cloud backup only.

### Step 2: Verify Hindsight is Active

1. **Open browser** at `http://localhost:8000`
2. **Look at top-right corner** for two status indicators:
   - **Phi-2 status**: Green dot + `Phi-2 -- mps -- float16`
   - **Hindsight status**: Green dot + text
3. **Expected Result**:
   - ✅ `Hindsight -- Active (0)` with green dot = Cloud + Local working
   - ✅ `Hindsight -- Local` with green dot = Local-only (no API key, still works!)

### Step 3: Check Server Logs (if not working)

1. **Look at the terminal** where the server is running
2. **Look for**:
   ```
   INFO:backend.ablation:Hindsight memory client initialized successfully  ← Cloud active
   ```
   or:
   ```
   WARNING:backend.ablation:HINDSIGHT_API_KEY environment variable not set  ← Local only
   ```
3. **Either way**, overlap detection still works via local history.

---

## Part 2: Testing Hindsight Overlap Detection

### Test Case 1: First Ablation (No Warning Expected)

1. **Click the sidebar toggle** (☰) then click **Ablation Engine** at the bottom
2. **Enter concept**:
   ```
   J.K. Rowling is the author of Harry Potter
   ```
3. **Settings**:
   - Layers: 3 (recommended)
   - Strength: 1.0 (standard)
   - CascadeFlow: ☐ Unchecked (test without cascade first)
4. **Click "Run Ablation"**
5. **Expected Result**:
   - ✅ No warning modal
   - ✅ Ablation completes successfully
   - ✅ Shows perplexity increase (Before → After)
   - ✅ Shows before/after proof text
   - ✅ Hindsight counter increments to `(1)`

### Test Case 2: Similar Concept (Warning SHOULD Appear)

1. **Keep Ablation Engine open**
2. **Clear previous concept**
3. **Enter NEW concept**:
   ```
   J.K. Rowling wrote the Harry Potter books
   ```
4. **Click "Run Ablation"**
5. **Expected Result**:
   - ⚠️ **OVERLAP WARNING MODAL APPEARS**
   - Shows: similarity percentage (should be ~93%)
   - Shows historical impact data

### What the Warning Should Look Like:

```
⚠️ Ablation Overlap Warning

This concept overlaps 93% with a previous ablation
'J.K. Rowling is the author of Harry Potter'.
Stacking ablations on overlapping concepts may
degrade model quality by ~18%.

Past Concept: J.K. Rowling is the author of Harry Potter
Similarity: 93.5%
Historical Impact: 18% perplexity increase

[Cancel]  [Proceed Anyway]
```

### Step 6: Test Warning Actions

**Option A: Cancel**
1. Click "Cancel"
2. Modal closes
3. Ablation is NOT performed
4. Can try different concept

**Option B: Proceed Anyway**
1. Click "Proceed Anyway"
2. Modal closes
3. Ablation proceeds despite warning (with `force_ablate: true`)
4. Results shown normally

### Test Case 3: Unrelated Concept (No Warning Expected)

1. **Enter completely different concept**:
   ```
   Python is a programming language
   ```
2. **Click "Run Ablation"**
3. **Expected Result**:
   - ✅ No warning modal
   - ✅ Ablation proceeds normally
   - ✅ No similarity to previous concepts

---

## Part 3: Testing CascadeFlow

### How CascadeFlow Works

CascadeFlow is a **safety net** that protects the model from becoming incoherent after ablation. It works by:

1. Measuring the model's **general coherence** on a neutral sentence ("The sky is blue and the grass is green") BEFORE and AFTER ablation
2. If coherence degrades by more than **50%**, it rolls back and retries with layers shifted ±2 positions
3. It does NOT measure perplexity on the ablated concept — increased perplexity on the target is expected and desired

### Test Case 1: Normal Ablation (No Cascade Needed)

1. **Open Ablation Engine**
2. **Check CascadeFlow toggle** ✓
3. **Enter concept**:
   ```
   The Eiffel Tower is in Paris
   ```
4. **Settings**:
   - Layers: 3
   - Strength: 1.0
5. **Click "Run Ablation"**
6. **Expected Result**:
   - ✅ Ablation completes
   - ✅ NO "CascadeFlow Activated" card (coherence stayed within 50%)
   - ✅ Perplexity increases on the concept (this is good!)

### Test Case 2: Aggressive Ablation (Cascade MAY Trigger)

1. **Enter concept**:
   ```
   Machine learning algorithms process data
   ```
2. **Settings**:
   - Layers: **8** (aggressive!)
   - Strength: **1.0**
   - CascadeFlow: ✓ **CHECKED**
3. **Click "Run Ablation"**
4. **Possible Results**:

   **If coherence is fine (< 50% degradation):**
   - ✅ Normal completion, no cascade card

   **If coherence degrades (> 50%):**
   - 🔄 **"CascadeFlow Activated" card appears**
   - Shows: "Automatically shifted layers by ±2 and retried"
   - Shows: Original layers vs Final layers
   - Shows: Final degradation percentage

### What CascadeFlow Card Should Look Like:

```
🔄 CascadeFlow

CascadeFlow Activated

Initial ablation exceeded 50% degradation threshold.
Automatically shifted layers by -2 and retried.
Result: 35.2% degradation (within threshold)

Original layers: 27, 25, 22, 19, 16, 14, 10, 5
Final layers: 25, 23, 20, 17, 14, 12, 8, 3
```

### Test Case 3: Cascade Exhaustion (All Attempts Exceed Threshold)

1. **Enter concept**:
   ```
   Complex technical terminology and jargon
   ```
2. **Settings**:
   - Layers: **8**
   - Strength: **1.0**
   - CascadeFlow: ✓ **CHECKED**
3. **Click "Run Ablation"**
4. **Possible Result** (if all shifted layers also degrade):
   - ⚠️ **"CascadeFlow Note" card** (yellow warning)
   - Message: "CascadeFlow tried shifted layers but used original."
   - Ablation IS still applied with original layers (CascadeFlow never blocks — it always proceeds)

### Test Case 4: CascadeFlow Disabled

1. **UNCHECK CascadeFlow toggle** ☐
2. **Enter concept and run ablation**
3. **Expected Result**:
   - ✅ Ablation proceeds regardless of any degradation
   - ✅ NO cascade attempts
   - ✅ NO "CascadeFlow Activated" card
   - ⚠️ May result in high perplexity if aggressive

---

## Part 4: Troubleshooting

### Problem: Hindsight Shows "Loading..." Forever

**Diagnosis**:
1. Open browser DevTools (F12)
2. Go to Console tab, check for errors
3. Check Network tab for `/health` request

**Solutions**:
1. **Check if server is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return JSON with `"status": "ok"`.

2. **Restart server**:
   ```bash
   # Stop server (Ctrl+C)
   uvicorn backend.main:app --reload
   ```

3. **Check server logs** for:
   ```
   WARNING:backend.ablation:HINDSIGHT_API_KEY environment variable not set
   OR
   INFO:backend.ablation:Hindsight memory client initialized successfully
   ```

### Problem: No Overlap Warning for Similar Concepts

**Possible Causes**:
1. **First ablation** — No history yet to compare against
2. **Concepts not similar enough** — Need >53% cosine similarity
3. **Server restarted** — History persists in `ablation_history.json`, so this shouldn't be an issue

**Solutions**:
1. **Do a first ablation**, then try a related concept
2. **Use closely related concepts**:
   - First: "J.K. Rowling is the author of Harry Potter"
   - Second: "J.K. Rowling wrote the Harry Potter books"
   - These score ~93% similarity and WILL trigger warning
3. **Check server logs** for:
   ```
   INFO:backend.ablation:Overlap: 'J.K. Rowling wrote' vs 'J.K. Rowling is' = 0.9348
   ```

### Problem: CascadeFlow Not Triggering

**Diagnosis**:
1. Check toggle is CHECKED ✓
2. CascadeFlow only triggers when **general model coherence** degrades >53%
3. Most 3-layer ablations won't degrade coherence enough to trigger it

**Solutions**:
1. **Use more aggressive settings**:
   - Layers: 8
   - Strength: 1.0
2. **CascadeFlow is a safety net** — it's expected to NOT trigger on most normal ablations. This means the ablation was safe.

---

## Part 5: Expected Behavior Summary

### Hindsight Status Indicator States

| State | Dot | Text | Meaning |
|-------|-----|------|---------| 
| Cloud Active | 🟢 Green | `Hindsight -- Active (N)` | API key set, cloud + local working, N = ablation count |
| Local Only | 🟢 Green | `Hindsight -- Local` | No API key, local history still works |
| Loading | ⚪ Gray | `Hindsight -- Loading...` | Health check in progress (should resolve quickly) |

### Overlap Warning Triggers

| Scenario | Warning? | Why |
|----------|----------|-----|
| First ablation | ❌ No | No history to compare |
| Similar concept (>65%) | ✅ Yes | High semantic overlap |
| Different concept (<65%) | ❌ No | Low semantic overlap |
| Force ablate (Proceed Anyway) | ❌ No | Bypassed intentionally |

### CascadeFlow Triggers

| Coherence Degradation | Cascade? | Result |
|----------------------|----------|--------|
| <50% | ❌ No | Normal completion |
| >50% (retry succeeds) | ✅ Yes | Shows shifted layers used |
| >50% (all retries fail) | ✅ Yes | Shows warning, proceeds with original layers |
| Toggle unchecked | ❌ No | Proceeds regardless |

---

## Part 6: Quick Verification Checklist

Before reporting issues, verify:

- [ ] Server is running without errors
- [ ] Browser is at `http://localhost:8000`
- [ ] Top-right shows Phi-2 status with green dot
- [ ] Top-right shows Hindsight status (Active or Local)
- [ ] Browser console shows no JavaScript errors (F12)
- [ ] CascadeFlow toggle is checked for cascade tests
- [ ] Using related concepts for overlap tests
- [ ] At least one ablation done before testing overlap

---

## Part 7: Success Criteria

### Hindsight Working ✅
- Green dot with "Active" or "Local" in top-right
- Overlap warning appears for similar concepts (>65% similarity)
- Warning shows similarity percentage
- Can cancel or proceed with warning
- History persists across server restarts (via `ablation_history.json`)

### CascadeFlow Working ✅
- Toggle is visible and functional
- Cascade card appears when general coherence degrades >50%
- Shows original vs final layers
- Always proceeds (never blocks ablation)

### UI Working ✅
- No glitching during ablation
- Smooth transitions
- Status cards appear cleanly
- Modal animations work properly

---

## Need Help?

If issues persist:
1. Check server terminal for error messages
2. Check browser console (F12) for JavaScript errors
3. Try `curl http://localhost:8000/health` to verify backend
4. Try with a fresh browser session (clear cache)
5. Delete `ablation_history.json` for a clean start
6. Restart both server and browser

## Test Results Template

Use this to document your tests:

```
Test Date: ___________
Server Running: Yes / No

Hindsight Status: Active (N) / Local / Loading
First Ablation: Success / Failed
Overlap Warning: Appeared / Did Not Appear
CascadeFlow: Triggered / Not Triggered / Exhausted

Notes:
_________________________________
_________________________________
```