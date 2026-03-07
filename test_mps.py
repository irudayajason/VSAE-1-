import torch

print("PyTorch version:", torch.__version__)
print("MPS available:", torch.backends.mps.is_available())
print("MPS built:", torch.backends.mps.is_built())

if torch.backends.mps.is_available():
    device = torch.device("mps")
    x = torch.ones(3, 3).to(device)
    print("Tensor on MPS:", x.device)
    print("GPU is working correctly!")
else:
    print("MPS not available - running on CPU only")
