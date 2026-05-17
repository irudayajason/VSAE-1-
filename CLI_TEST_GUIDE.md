# VSAE CLI Test Guide

## IBM Bob Hackathon - CLI Testing Documentation

This guide provides comprehensive testing instructions for the VSAE CLI tool (`vsae-cli.py`).

---

## Prerequisites

### 1. Environment Setup
```bash
# Ensure virtual environment is activated
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Verify dependencies
pip install -r requirements.txt
```

### 2. Required Dependencies
- Python 3.8+
- PyTorch
- Transformers
- Rich (for colored output)
- All backend modules

---

## Quick Start Tests

### Test 1: Basic Ablation
```bash
python vsae-cli.py --forget_text "Harry Potter" --top_k 5 --alpha 0.8
```

**Expected Output:**
- ✅ Model loads successfully
- ✅ Forget vectors extracted
- ✅ Target layers identified
- ✅ Ablation completes
- ✅ JSON report generated in `reports/` directory

### Test 2: Minimal Parameters
```bash
python vsae-cli.py --forget_text "Python programming"
```

**Expected Behavior:**
- Uses default `top_k=5`
- Uses default `alpha=0.8`
- Runs full evaluation suite

### Test 3: Force Mode (Skip Overlap Check)
```bash
python vsae-cli.py --forget_text "Apple Inc" --force
```

**Expected Behavior:**
- Skips overlap detection
- Proceeds directly to ablation

### Test 4: Fast Mode (No Evaluation)
```bash
python vsae-cli.py --forget_text "Test concept" --no-evaluation
```

**Expected Behavior:**
- Skips full evaluation suite
- Uses simple perplexity threshold (>100 = FORGOTTEN)
- Faster execution

---

## Advanced Tests

### Test 5: Custom Alpha Values
```bash
# Weak ablation
python vsae-cli.py --forget_text "Concept A" --alpha 0.3

# Strong ablation
python vsae-cli.py --forget_text "Concept B" --alpha 1.0

# Over-projection
python vsae-cli.py --forget_text "Concept C" --alpha 1.5
```

**Expected Behavior:**
- Lower alpha = weaker forgetting
- Higher alpha = stronger forgetting
- Alpha > 1.0 = over-projection (may flip direction)

### Test 6: Layer Targeting
```bash
# Target fewer layers
python vsae-cli.py --forget_text "Concept D" --top_k 3

# Target more layers
python vsae-cli.py --forget_text "Concept E" --top_k 8
```

**Expected Behavior:**
- Fewer layers = more surgical, less impact
- More layers = broader impact, higher perplexity change

### Test 7: Custom Output Directory
```bash
python vsae-cli.py --forget_text "Test" --output-dir custom_reports
```

**Expected Behavior:**
- Creates `custom_reports/` directory
- Saves JSON report there

---

## Validation Tests

### Test 8: Compliance Report Validation
```bash
# Run CLI
python vsae-cli.py --forget_text "Validation test" --top_k 5 --alpha 0.8

# Validate generated report
python scripts/validate_compliance_report.py reports/<generated_report>.json
```

**Expected Output:**
```
✅ PASS - All validations passed

Validated Fields:
  ✓ ablation_id: <uuid>
  ✓ timestamp: <iso8601>
  ✓ concept: Validation test
  ✓ target_layers: list (length: 5)
  ✓ alpha: 0.8000
  ✓ pre_perplexity: <value>
  ✓ post_perplexity: <value>
  ✓ perplexity_delta: <value>
  ✓ forgetting_signal: FORGOTTEN or STILL_KNOWN
  ✓ config_hash: <sha256>
```

### Test 9: JSON Schema Verification
```bash
# Generate report
python vsae-cli.py --forget_text "Schema test" --top_k 3

# Check JSON structure
python -m json.tool reports/<generated_report>.json
```

**Required Fields:**
- `ablation_id` (string)
- `timestamp` (ISO 8601)
- `concept` (string)
- `target_layers` (array)
- `alpha` (float)
- `pre_perplexity` (float)
- `post_perplexity` (float)
- `perplexity_delta` (float)
- `forgetting_signal` (string: "FORGOTTEN" or "STILL_KNOWN")
- `config_hash` (string, 64 chars)

---

## Error Handling Tests

### Test 10: Empty Concept
```bash
python vsae-cli.py --forget_text ""
```

**Expected Output:**
```
[VSAE] Error: forget_text cannot be empty
Exit code: 1
```

### Test 11: Invalid Alpha
```bash
python vsae-cli.py --forget_text "Test" --alpha 2.5
```

**Expected Output:**
```
[VSAE] Error: alpha must be between 0.0 and 2.0
Exit code: 1
```

### Test 12: Invalid Top-K
```bash
python vsae-cli.py --forget_text "Test" --top_k 15
```

**Expected Output:**
```
[VSAE] Error: top_k must be between 1 and 10
Exit code: 1
```

### Test 13: Keyboard Interrupt
```bash
python vsae-cli.py --forget_text "Test" --top_k 5
# Press Ctrl+C during execution
```

**Expected Output:**
```
[VSAE] Ablation cancelled by user
Exit code: 130
```

---

## Performance Tests

### Test 14: Execution Time Measurement
```bash
# Linux/Mac
time python vsae-cli.py --forget_text "Performance test" --no-evaluation

# Windows PowerShell
Measure-Command { python vsae-cli.py --forget_text "Performance test" --no-evaluation }
```

**Expected Timing:**
- With evaluation: ~2-5 minutes (depends on hardware)
- Without evaluation: ~1-2 minutes

### Test 15: Memory Usage
```bash
# Linux
/usr/bin/time -v python vsae-cli.py --forget_text "Memory test"

# Monitor peak memory usage
```

**Expected Memory:**
- Peak: ~4-6 GB (Phi-2 model loading)
- Steady state: ~3-4 GB

---

## Integration Tests

### Test 16: Backend Function Calls
Verify CLI correctly calls backend functions:

```bash
# Enable debug logging
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from vsae_cli import main
import sys
sys.argv = ['vsae-cli.py', '--forget_text', 'Integration test', '--top_k', '3']
main()
"
```

**Expected Log Sequence:**
1. `load_model()` called
2. `get_forget_vector()` called
3. `get_layerwise_forget_vectors()` called
4. `find_target_layers()` called
5. `compute_perplexity()` called (pre)
6. `ablate()` called
7. `compute_perplexity()` called (post)
8. `run_full_evaluation()` called
9. `log_ablation_to_hindsight()` called

### Test 17: Report Generation Pipeline
```bash
# Run full pipeline
python vsae-cli.py --forget_text "Pipeline test" --top_k 5 --alpha 0.8

# Verify report exists
ls -lh reports/

# Validate report
python scripts/validate_compliance_report.py reports/<latest_report>.json

# Check report content
cat reports/<latest_report>.json | jq '.forgetting_signal'
```

---

## Regression Tests

### Test 18: Backward Compatibility
Verify old field names still present:

```bash
python vsae-cli.py --forget_text "Compatibility test"

# Check both old and new field names exist
cat reports/<latest_report>.json | jq '{
  old_forget_text: .forget_text,
  new_concept: .concept,
  old_targeted_layers: .targeted_layers,
  new_target_layers: .target_layers,
  old_perplexity_change: .perplexity_change,
  new_perplexity_delta: .perplexity_delta
}'
```

**Expected Output:**
All fields should be present with matching values.

---

## CI/CD Tests

### Test 19: GitHub Actions Simulation
```bash
# Simulate CI environment
export CI=true
export GITHUB_ACTIONS=true

# Run CLI in CI mode
python vsae-cli.py --forget_text "CI test" --no-evaluation --force

# Validate report
python scripts/validate_compliance_report.py reports/<latest_report>.json
```

**Expected Behavior:**
- No interactive prompts
- Deterministic output
- Exit code 0 on success

---

## Troubleshooting

### Issue: Model Loading Fails
```bash
# Check CUDA availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# Force CPU mode
export CUDA_VISIBLE_DEVICES=""
python vsae-cli.py --forget_text "Test"
```

### Issue: Rich Not Installed
```bash
# CLI works without Rich (fallback mode)
pip uninstall rich -y
python vsae-cli.py --forget_text "Test"
# Should display plain text output
```

### Issue: Permission Denied on Reports Directory
```bash
# Create directory manually
mkdir -p reports
chmod 755 reports
python vsae-cli.py --forget_text "Test"
```

---

## Test Checklist

Use this checklist for comprehensive testing:

- [ ] Basic ablation completes successfully
- [ ] JSON report generated with all required fields
- [ ] Compliance validator passes
- [ ] Pre/post perplexity values are positive
- [ ] Perplexity delta equals (post - pre)
- [ ] Forgetting signal matches perplexity threshold
- [ ] Config hash is non-empty 64-char string
- [ ] Before/after probes show behavioral change
- [ ] Sanity check passes (alpha_ratio >= 0.5)
- [ ] Error handling works for invalid inputs
- [ ] Force mode skips overlap check
- [ ] No-evaluation mode runs faster
- [ ] Custom output directory works
- [ ] Keyboard interrupt handled gracefully
- [ ] Backward compatibility maintained

---

## Success Criteria

A successful CLI test run should produce:

1. **Console Output:**
   - Clear step-by-step progress
   - Colored output (if Rich available)
   - Final summary table
   - Success message

2. **JSON Report:**
   - Valid JSON structure
   - All required fields present
   - Passes compliance validation
   - Perplexity logic consistent

3. **Exit Code:**
   - `0` for success
   - `1` for errors
   - `130` for user cancellation

---

## Contact

For issues or questions about CLI testing:
- Check `bob_session_cli.md` for development notes
- Review `TESTING_GUIDE.md` for pytest instructions
- See `README.md` for general documentation

---

**Last Updated:** 2026-05-17  
**IBM Bob Hackathon Submission**  
**Made with Bob** 🤖