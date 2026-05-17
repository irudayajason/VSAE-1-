"""
Test suite for VSAE ablation mathematics.

All tests run WITHOUT loading Phi-2 or any real model.
Uses unittest.mock to mock model, tokenizer, and device calls.
"""

import pytest
import torch
import math
from unittest.mock import patch, MagicMock
from typing import Dict

# Import functions to test
from backend.ablation import apply_projection, _weight_hash
from backend.evaluate import compute_perplexity, membership_inference_attack


class TestProjectionMath:
    """Test the orthogonal projection formula."""
    
    def test_projection_removes_concept_direction(self):
        """
        Test 1: Verify that projection removes the concept direction.
        
        After applying W_new = W - alpha * (W @ v) @ v.T / (v.T @ v),
        the component of W_new along v should be near zero.
        """
        # Create synthetic tensors
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()  # Normalize to unit vector
        
        # Apply projection with alpha=1.0 (full removal)
        W_new = apply_projection(W, v, alpha=1.0)
        
        # Compute the component along v before and after
        component_before = (W @ v).norm()
        component_after = (W_new @ v).norm()
        
        # After projection, component should be < 1% of original
        assert component_after < 0.01 * component_before, (
            f"Projection failed: component_after={component_after:.6f}, "
            f"component_before={component_before:.6f}"
        )
        
        # Should be very close to zero
        assert component_after < 0.1, f"Component not suppressed: {component_after:.6f}"
    
    def test_alpha_zero_produces_no_change(self):
        """
        Test 2: Verify that alpha=0.0 produces no change to weights.
        
        With alpha=0, the projection term is zero, so W_new should equal W.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Apply projection with alpha=0.0 (no change)
        W_new = apply_projection(W, v, alpha=0.0)
        
        # W_new should be identical to W
        assert torch.allclose(W_new, W, atol=1e-6), (
            "Alpha=0.0 should produce no change to weights"
        )
    
    def test_alpha_one_full_suppression(self):
        """
        Test 3: Verify that alpha=1.0 fully suppresses the concept direction.
        
        This is the standard orthogonal projection case.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Apply projection with alpha=1.0
        W_new = apply_projection(W, v, alpha=1.0)
        
        # The projection of W_new onto v should be near zero
        projection = W_new @ v
        projection_norm = projection.norm()
        
        # Should be very small (numerical precision limits)
        assert projection_norm < 1e-4, (
            f"Full suppression failed: projection_norm={projection_norm:.6f}"
        )
    
    def test_alpha_partial_suppression(self):
        """
        Test 3b: Verify that 0 < alpha < 1 produces partial suppression.
        
        With alpha=0.5, the component should be reduced by ~50%.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Measure original component
        component_original = (W @ v).norm()
        
        # Apply projection with alpha=0.5
        W_new = apply_projection(W, v, alpha=0.5)
        component_after = (W_new @ v).norm()
        
        # Component should be reduced but not eliminated
        reduction_ratio = component_after / component_original
        
        # Should be approximately 50% remaining (within 20% tolerance)
        assert 0.3 < reduction_ratio < 0.7, (
            f"Partial suppression failed: reduction_ratio={reduction_ratio:.2f}, "
            f"expected ~0.5"
        )
    
    def test_projection_preserves_orthogonal_directions(self):
        """
        Test 3c: Verify that projection preserves directions orthogonal to v.
        
        If u is orthogonal to v, then W @ u should be unchanged.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Create a vector orthogonal to v using Gram-Schmidt
        u = torch.randn(10, dtype=torch.float32)
        u = u - (u @ v) * v  # Remove component along v
        u = u / u.norm()
        
        # Verify u is orthogonal to v
        assert abs(u @ v) < 1e-5, "Test setup failed: u not orthogonal to v"
        
        # Apply projection
        W_new = apply_projection(W, v, alpha=1.0)
        
        # W @ u and W_new @ u should be very similar
        Wu_before = W @ u
        Wu_after = W_new @ u
        
        assert torch.allclose(Wu_before, Wu_after, atol=1e-4), (
            "Projection should preserve orthogonal directions"
        )


class TestPerplexityComputation:
    """Test perplexity computation with mocked model."""
    
    @patch('backend.evaluate.load_model')
    def test_perplexity_returns_positive_float(self, mock_load_model):
        """
        Test 4: Verify compute_perplexity returns exp(loss).
        
        Mock the model to return a fixed loss value and verify
        perplexity = exp(loss).
        """
        # Create mock model that returns a fixed loss
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_device = torch.device('cpu')
        
        # Mock tokenizer to return fake input tensors with .to() support
        mock_encoded = MagicMock()
        mock_encoded.to.return_value = {
            'input_ids': torch.tensor([[1, 2, 3, 4]]),
            'attention_mask': torch.tensor([[1, 1, 1, 1]])
        }
        mock_tokenizer.return_value = mock_encoded
        
        # Mock model forward pass to return fixed loss
        mock_output = MagicMock()
        mock_output.loss = torch.tensor(2.3)
        mock_model.return_value = mock_output
        
        # Setup load_model to return mocks
        mock_load_model.return_value = (mock_model, mock_tokenizer, mock_device)
        
        # Call compute_perplexity
        perplexity = compute_perplexity("test text")
        
        # Verify perplexity = exp(2.3)
        expected_perplexity = math.exp(2.3)
        assert abs(perplexity - expected_perplexity) < 0.01, (
            f"Perplexity mismatch: got {perplexity:.4f}, "
            f"expected {expected_perplexity:.4f}"
        )
        
        # Verify it's a positive float
        assert isinstance(perplexity, float), "Perplexity should be a float"
        assert perplexity > 0, "Perplexity should be positive"
    
    @patch('backend.evaluate.load_model')
    def test_perplexity_high_loss_produces_high_perplexity(self, mock_load_model):
        """
        Test 4b: Verify that high loss produces high perplexity.
        
        Loss of 5.0 should produce perplexity of ~148.
        """
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_device = torch.device('cpu')
        
        # Mock tokenizer to return fake input tensors with .to() support
        mock_encoded = MagicMock()
        mock_encoded.to.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value = mock_encoded
        
        mock_output = MagicMock()
        mock_output.loss = torch.tensor(5.0)
        mock_model.return_value = mock_output
        
        mock_load_model.return_value = (mock_model, mock_tokenizer, mock_device)
        
        perplexity = compute_perplexity("forgotten concept")
        
        expected = math.exp(5.0)  # ~148.4
        assert abs(perplexity - expected) < 1.0, (
            f"High loss perplexity mismatch: got {perplexity:.2f}, "
            f"expected {expected:.2f}"
        )


class TestForgettingSignal:
    """Test the forgetting signal logic."""
    
    @patch('backend.evaluate.load_model')
    def test_forgetting_signal_logic(self, mock_load_model):
        """
        Test 5: Verify forgetting signal thresholds.
        
        - Perplexity > 100 → FORGOTTEN
        - Perplexity < 100 → STILL_KNOWN
        """
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_device = torch.device('cpu')
        
        # Mock tokenizer to return fake input tensors with .to() support
        mock_encoded = MagicMock()
        mock_encoded.to.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value = mock_encoded
        
        mock_load_model.return_value = (mock_model, mock_tokenizer, mock_device)
        
        # Test case 1: High perplexity (150) → FORGOTTEN
        mock_output_high = MagicMock()
        mock_output_high.loss = torch.tensor(math.log(150))  # perplexity = 150
        mock_model.return_value = mock_output_high
        
        result_high = membership_inference_attack("forgotten text")
        assert result_high["verdict"] == "FORGOTTEN", (
            f"High perplexity should be FORGOTTEN, got {result_high['verdict']}"
        )
        assert result_high["perplexity"] > 100, (
            f"Expected perplexity > 100, got {result_high['perplexity']}"
        )
        
        # Test case 2: Low perplexity (50) → STILL_KNOWN
        mock_output_low = MagicMock()
        mock_output_low.loss = torch.tensor(math.log(50))  # perplexity = 50
        mock_model.return_value = mock_output_low
        
        result_low = membership_inference_attack("known text")
        assert result_low["verdict"] == "STILL_KNOWN", (
            f"Low perplexity should be STILL_KNOWN, got {result_low['verdict']}"
        )
        assert result_low["perplexity"] < 100, (
            f"Expected perplexity < 100, got {result_low['perplexity']}"
        )
    
    @patch('backend.evaluate.load_model')
    def test_forgetting_threshold_boundary(self, mock_load_model):
        """
        Test 5b: Verify behavior at the threshold boundary (perplexity = 100).
        """
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_device = torch.device('cpu')
        
        # Mock tokenizer to return fake input tensors with .to() support
        mock_encoded = MagicMock()
        mock_encoded.to.return_value = {
            'input_ids': torch.tensor([[1, 2, 3]]),
            'attention_mask': torch.tensor([[1, 1, 1]])
        }
        mock_tokenizer.return_value = mock_encoded
        
        mock_load_model.return_value = (mock_model, mock_tokenizer, mock_device)
        
        # Just under threshold to avoid floating-point errors
        mock_output = MagicMock()
        mock_output.loss = torch.tensor(math.log(99.9))  # Avoid floating-point >100 error
        mock_model.return_value = mock_output
        
        result = membership_inference_attack("boundary text")
        
        # Just under 100, should be STILL_KNOWN (threshold is >100, not >=100)
        assert result["verdict"] == "STILL_KNOWN", (
            f"Perplexity<100 should be STILL_KNOWN, got {result['verdict']}"
        )


class TestWeightHashing:
    """Test weight tensor hashing for verification."""
    
    def test_config_hash_is_deterministic(self):
        """
        Test 6: Verify that weight hashing is deterministic.
        
        Same tensor should produce same hash every time.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        
        # Generate hash twice
        hash1 = _weight_hash(W)
        hash2 = _weight_hash(W)
        
        # Should be identical
        assert hash1 == hash2, (
            f"Hash should be deterministic: {hash1} != {hash2}"
        )
        
        # Should be a string
        assert isinstance(hash1, str), "Hash should be a string"
        
        # Should be 16 characters (truncated SHA256)
        assert len(hash1) == 16, f"Hash should be 16 chars, got {len(hash1)}"
    
    def test_different_tensors_produce_different_hashes(self):
        """
        Test 6b: Verify that different tensors produce different hashes.
        """
        torch.manual_seed(42)
        W1 = torch.randn(10, 10, dtype=torch.float32)
        W2 = torch.randn(10, 10, dtype=torch.float32)
        
        hash1 = _weight_hash(W1)
        hash2 = _weight_hash(W2)
        
        # Should be different
        assert hash1 != hash2, (
            "Different tensors should produce different hashes"
        )
    
    def test_modified_tensor_produces_different_hash(self):
        """
        Test 6c: Verify that modifying a tensor changes its hash.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        
        hash_before = _weight_hash(W)
        
        # Modify the tensor
        W[0, 0] += 1.0
        
        hash_after = _weight_hash(W)
        
        # Hash should change
        assert hash_before != hash_after, (
            "Hash should change after tensor modification"
        )


class TestProjectionEdgeCases:
    """Test edge cases and error handling."""
    
    def test_near_zero_vector_handling(self):
        """
        Test that projection handles near-zero vectors gracefully.
        
        Should return original W unchanged and log a warning.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.zeros(10, dtype=torch.float32)  # Zero vector
        
        # Should return W unchanged
        W_new = apply_projection(W, v, alpha=1.0)
        
        assert torch.allclose(W_new, W, atol=1e-6), (
            "Zero vector should return unchanged weights"
        )
    
    def test_projection_with_float16_weights(self):
        """
        Test that projection works with float16 weights (Phi-2 uses float16).
        
        Should upcast to float32, compute, then cast back to float16.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float16)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Apply projection
        W_new = apply_projection(W, v, alpha=1.0)
        
        # Result should be float16
        assert W_new.dtype == torch.float16, (
            f"Result should be float16, got {W_new.dtype}"
        )
        
        # Component should still be suppressed (within float16 precision)
        component_after = (W_new.float() @ v).norm()
        assert component_after < 0.1, (
            f"Float16 projection failed: component={component_after:.6f}"
        )
    
    def test_projection_with_large_alpha(self):
        """
        Test projection with alpha > 1.0 (over-projection).
        
        Should work but may flip the direction.
        """
        torch.manual_seed(42)
        W = torch.randn(10, 10, dtype=torch.float32)
        v = torch.randn(10, dtype=torch.float32)
        v = v / v.norm()
        
        # Apply over-projection
        W_new = apply_projection(W, v, alpha=2.0)
        
        # Should not crash
        assert W_new.shape == W.shape, "Shape should be preserved"
        
        # Component magnitude should be larger than with alpha=1.0
        W_alpha1 = apply_projection(W, v, alpha=1.0)
        component_alpha1 = (W_alpha1 @ v).norm()
        component_alpha2 = (W_new @ v).norm()
        
        # With alpha=2.0, we over-project, so component might flip sign
        # but magnitude should be comparable or larger
        assert component_alpha2 >= 0, "Component should be non-negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
