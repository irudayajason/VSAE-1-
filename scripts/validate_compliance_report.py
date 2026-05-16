#!/usr/bin/env python3
"""
Compliance Report Validator for VSAE Ablation Reports

Validates JSON compliance reports without requiring PyTorch or model loading.
Designed to run in GitHub Actions with 7GB RAM constraint.

Usage:
    python scripts/validate_compliance_report.py <report.json>

Exit Codes:
    0 = PASS (all validations passed)
    1 = FAIL (validation errors found)
"""

import sys
import json
from datetime import datetime
from typing import Dict, List, Any


class ValidationError:
    """Represents a single validation failure."""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
    
    def __str__(self):
        return f"  ❌ {self.field}: {self.message}"


class ComplianceValidator:
    """Validates VSAE ablation compliance reports."""
    
    REQUIRED_FIELDS = {
        "ablation_id": str,
        "timestamp": str,
        "concept": str,
        "target_layers": list,
        "alpha": (float, int),
        "pre_perplexity": (float, int),
        "post_perplexity": (float, int),
        "perplexity_delta": (float, int),
        "forgetting_signal": str,
        "config_hash": str,
    }
    
    PERPLEXITY_THRESHOLD = 100.0  # Matches backend/evaluate.py threshold
    
    def __init__(self, report_path: str):
        self.report_path = report_path
        self.errors: List[ValidationError] = []
        self.data: Dict[str, Any] = {}
    
    def validate(self) -> bool:
        """Run all validations. Returns True if all pass."""
        try:
            self._load_json()
            self._validate_required_fields()
            self._validate_field_types()
            self._validate_field_values()
            self._validate_perplexity_logic()
            self._validate_forgetting_signal()
            
            return len(self.errors) == 0
        
        except Exception as e:
            self.errors.append(ValidationError("CRITICAL", f"Validation failed: {str(e)}"))
            return False
    
    def _load_json(self):
        """Load and parse JSON file."""
        try:
            with open(self.report_path, 'r') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            raise Exception(f"Report file not found: {self.report_path}")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON: {str(e)}")
    
    def _validate_required_fields(self):
        """Check all required fields are present."""
        for field in self.REQUIRED_FIELDS.keys():
            if field not in self.data:
                self.errors.append(ValidationError(field, "Missing required field"))
    
    def _validate_field_types(self):
        """Validate field types match expected types."""
        for field, expected_type in self.REQUIRED_FIELDS.items():
            if field not in self.data:
                continue  # Already reported as missing
            
            value = self.data[field]
            if not isinstance(value, expected_type):
                self.errors.append(
                    ValidationError(field, f"Expected {expected_type}, got {type(value).__name__}")
                )
    
    def _validate_field_values(self):
        """Validate field value constraints."""
        # ablation_id: non-empty string
        if "ablation_id" in self.data:
            if not self.data["ablation_id"].strip():
                self.errors.append(ValidationError("ablation_id", "Cannot be empty"))
        
        # timestamp: valid ISO 8601 format
        if "timestamp" in self.data:
            try:
                datetime.fromisoformat(self.data["timestamp"].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                self.errors.append(ValidationError("timestamp", "Invalid ISO 8601 format"))
        
        # concept: non-empty string
        if "concept" in self.data:
            if not self.data["concept"].strip():
                self.errors.append(ValidationError("concept", "Cannot be empty"))
        
        # target_layers: minimum 1 element
        if "target_layers" in self.data:
            if len(self.data["target_layers"]) < 1:
                self.errors.append(ValidationError("target_layers", "Must contain at least 1 layer"))
        
        # alpha: between 0.0 and 1.0
        if "alpha" in self.data:
            alpha = float(self.data["alpha"])
            if not (0.0 <= alpha <= 1.0):
                self.errors.append(ValidationError("alpha", f"Must be between 0.0 and 1.0, got {alpha}"))
        
        # pre_perplexity: greater than 0
        if "pre_perplexity" in self.data:
            pre = float(self.data["pre_perplexity"])
            if pre <= 0:
                self.errors.append(ValidationError("pre_perplexity", f"Must be > 0, got {pre}"))
        
        # post_perplexity: greater than 0
        if "post_perplexity" in self.data:
            post = float(self.data["post_perplexity"])
            if post <= 0:
                self.errors.append(ValidationError("post_perplexity", f"Must be > 0, got {post}"))
        
        # forgetting_signal: must be FORGOTTEN or STILL_KNOWN
        if "forgetting_signal" in self.data:
            signal = self.data["forgetting_signal"]
            if signal not in ["FORGOTTEN", "STILL_KNOWN"]:
                self.errors.append(
                    ValidationError("forgetting_signal", f"Must be 'FORGOTTEN' or 'STILL_KNOWN', got '{signal}'")
                )
        
        # config_hash: non-empty string
        if "config_hash" in self.data:
            if not self.data["config_hash"].strip():
                self.errors.append(ValidationError("config_hash", "Cannot be empty"))
    
    def _validate_perplexity_logic(self):
        """Validate perplexity relationships and calculations."""
        required = ["pre_perplexity", "post_perplexity", "perplexity_delta"]
        if not all(field in self.data for field in required):
            return  # Missing fields already reported
        
        pre = float(self.data["pre_perplexity"])
        post = float(self.data["post_perplexity"])
        delta = float(self.data["perplexity_delta"])
        
        # Rule 1: post_perplexity must be HIGHER than pre_perplexity
        # (higher perplexity = model is more confused = concept was forgotten)
        if post <= pre:
            self.errors.append(
                ValidationError(
                    "post_perplexity",
                    f"Must be HIGHER than pre_perplexity (post={post:.2f} <= pre={pre:.2f}). "
                    "Higher perplexity indicates successful forgetting."
                )
            )
        
        # Rule 2: perplexity_delta must be positive
        if delta <= 0:
            self.errors.append(
                ValidationError("perplexity_delta", f"Must be positive, got {delta:.2f}")
            )
        
        # Rule 3: perplexity_delta must equal (post - pre) within tolerance
        expected_delta = post - pre
        tolerance = 0.01
        if abs(delta - expected_delta) > tolerance:
            self.errors.append(
                ValidationError(
                    "perplexity_delta",
                    f"Must equal (post - pre) = {expected_delta:.2f}, got {delta:.2f} "
                    f"(difference: {abs(delta - expected_delta):.4f} > tolerance {tolerance})"
                )
            )
    
    def _validate_forgetting_signal(self):
        """Validate forgetting_signal matches perplexity threshold logic."""
        required = ["post_perplexity", "forgetting_signal"]
        if not all(field in self.data for field in required):
            return  # Missing fields already reported
        
        post = float(self.data["post_perplexity"])
        signal = self.data["forgetting_signal"]
        
        # Threshold logic from backend/evaluate.py:79
        expected_signal = "FORGOTTEN" if post > self.PERPLEXITY_THRESHOLD else "STILL_KNOWN"
        
        if signal != expected_signal:
            self.errors.append(
                ValidationError(
                    "forgetting_signal",
                    f"Inconsistent with perplexity. post_perplexity={post:.2f}, "
                    f"threshold={self.PERPLEXITY_THRESHOLD}, expected '{expected_signal}', got '{signal}'"
                )
            )
    
    def print_report(self):
        """Print validation results."""
        print(f"\n{'='*70}")
        print(f"VSAE Compliance Report Validation")
        print(f"{'='*70}")
        print(f"Report: {self.report_path}")
        print(f"{'='*70}\n")
        
        if len(self.errors) == 0:
            print("✅ PASS - All validations passed")
            print(f"\nValidated Fields:")
            for field in self.REQUIRED_FIELDS.keys():
                value = self.data.get(field)
                if isinstance(value, (list, dict)):
                    print(f"  ✓ {field}: {type(value).__name__} (length: {len(value)})")
                elif isinstance(value, float):
                    print(f"  ✓ {field}: {value:.4f}")
                else:
                    print(f"  ✓ {field}: {value}")
            print()
        else:
            print(f"❌ FAIL - {len(self.errors)} validation error(s) found:\n")
            for error in self.errors:
                print(error)
            print()


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_compliance_report.py <report.json>")
        sys.exit(1)
    
    report_path = sys.argv[1]
    validator = ComplianceValidator(report_path)
    
    passed = validator.validate()
    validator.print_report()
    
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()

# Made with Bob
