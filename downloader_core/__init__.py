import sys
from pathlib import Path


_PACKAGE_ROOT = Path(__file__).resolve().parent
_PACKAGE_ROOT_STR = str(_PACKAGE_ROOT)

if _PACKAGE_ROOT_STR not in sys.path:
    # Keep legacy intra-core imports working while the implementation lives under a package.
    sys.path.insert(0, _PACKAGE_ROOT_STR)