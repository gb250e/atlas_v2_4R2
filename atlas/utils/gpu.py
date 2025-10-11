from __future__ import annotations

from typing import Dict


def detect_accelerator() -> Dict[str, str]:
    """Return backend/device information if GPU backends are available."""
    backend = "numpy"
    device = "cpu"
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            backend = "torch"
            device = f"cuda:{torch.cuda.current_device()}"
            return {"backend": backend, "device": device}
    except Exception:
        pass
    try:
        import cupy  # type: ignore

        if cupy.cuda.runtime.getDeviceCount() > 0:
            backend = "cupy"
            device = "cuda:0"
            return {"backend": backend, "device": device}
    except Exception:
        pass
    return {"backend": backend, "device": device}
