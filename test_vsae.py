#!/usr/bin/env python3
"""
VSAE Integration Test Suite
Tests all major components without requiring the full Phi-2 model download
"""

import sys
import os

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Test 1: Module Imports")
    try:
        import torch
        import transformers
        import fastapi
        import uvicorn
        from hindsight_client import Hindsight
        print("  ✅ All core dependencies imported successfully")
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_backend_modules():
    """Test that backend modules load correctly"""
    print("\n🧪 Test 2: Backend Modules")
    try:
        from backend.main import app
        from backend.ablation import (
            initialize_hindsight, 
            check_ablation_overlap,
            ablate_with_cascade,
            shift_target_layers
        )
        from backend.embedding import load_model, get_forget_vector
        from backend.locator import find_target_layers
        from backend.evaluate import compute_perplexity
        print("  ✅ All backend modules loaded successfully")
        return True
    except Exception as e:
        print(f"  ❌ Backend module loading failed: {e}")
        return False

def test_hindsight_integration():
    """Test Hindsight SDK integration"""
    print("\n🧪 Test 3: Hindsight Integration")
    try:
        from backend.ablation import initialize_hindsight
        result = initialize_hindsight()
        if result:
            print("  ✅ Hindsight initialized successfully")
        else:
            print("  ⚠️  Hindsight not initialized (API key not set - this is OK)")
        return True
    except Exception as e:
        print(f"  ❌ Hindsight test failed: {e}")
        return False

def test_cascadeflow():
    """Test CascadeFlow functionality"""
    print("\n🧪 Test 4: CascadeFlow Functionality")
    try:
        from backend.ablation import shift_target_layers, ablate_with_cascade
        import inspect
        
        # Test layer shifting
        target_layers = [
            {'layer_index': 10, 'target_matrices': ['W_Q', 'W_K', 'W_V']},
            {'layer_index': 15, 'target_matrices': ['W_Q', 'W_K', 'W_V']},
        ]
        
        shifted = shift_target_layers(target_layers, -2, 32)
        assert len(shifted) == 2
        assert shifted[0]['layer_index'] == 8
        assert shifted[1]['layer_index'] == 13
        
        # Verify function signature
        sig = inspect.signature(ablate_with_cascade)
        params = list(sig.parameters.keys())
        required = ['layer_forget_vectors', 'target_layers', 'cascade_threshold']
        assert all(p in params for p in required)
        
        print("  ✅ CascadeFlow functionality verified")
        return True
    except Exception as e:
        print(f"  ❌ CascadeFlow test failed: {e}")
        return False

def test_api_endpoints():
    """Test that API endpoints are properly defined"""
    print("\n🧪 Test 5: API Endpoints")
    try:
        from backend.main import app
        
        routes = [route.path for route in app.routes]
        required_endpoints = ['/health', '/ablate', '/probe', '/rollback', '/ablations']
        
        for endpoint in required_endpoints:
            if endpoint in routes:
                print(f"  ✅ {endpoint} endpoint defined")
            else:
                print(f"  ❌ {endpoint} endpoint missing")
                return False
        
        return True
    except Exception as e:
        print(f"  ❌ API endpoint test failed: {e}")
        return False

def test_frontend_files():
    """Test that frontend files exist"""
    print("\n🧪 Test 6: Frontend Files")
    try:
        frontend_files = [
            'frontend/index.html',
            'frontend/app.js',
            'frontend/style.css',
            'frontend/sphere3d.js',
            'frontend/dustfx.js'
        ]
        
        all_exist = True
        for file in frontend_files:
            if os.path.exists(file):
                print(f"  ✅ {file} exists")
            else:
                print(f"  ❌ {file} missing")
                all_exist = False
        
        return all_exist
    except Exception as e:
        print(f"  ❌ Frontend files test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("VSAE Integration Test Suite")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_backend_modules,
        test_hindsight_integration,
        test_cascadeflow,
        test_api_endpoints,
        test_frontend_files
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! VSAE is ready to run.")
        print("\nNext steps:")
        print("1. Start the server: uvicorn backend.main:app --reload")
        print("2. Open http://localhost:8000 in your browser")
        print("3. (Optional) Set HINDSIGHT_API_KEY in .env for ablation history")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
