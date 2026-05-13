import sys
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parent
_PACKAGE_ROOT_STR = str(_PACKAGE_ROOT)

if getattr(sys, "frozen", False):
    # Running inside a PyInstaller --onefile bundle.
    # In that mode .py files are stored in the PYZ archive, not extracted to
    # disk, so inserting a path into sys.path cannot find them.  Instead,
    # install a meta-path finder that redirects bare-name imports
    # (e.g. ``from cookies import …``) to the bundled downloader_core.xxx
    # equivalents which are always present via --collect-submodules.
    import importlib
    import importlib.abc
    import importlib.machinery

    _BARE_NAMES: frozenset = frozenset([
        "api", "commandline", "cookies", "coursera_dl", "credentials",
        "define", "downloaders", "extractors", "filtering", "formatting",
        "general", "locked_cookie", "network", "parallel", "playlist",
        "utils", "workflow",
    ])

    class _CoreAliasImporter(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, fullname, path, target=None):
            if fullname in _BARE_NAMES and fullname not in sys.modules:
                return importlib.machinery.ModuleSpec(fullname, self)
            return None

        def create_module(self, spec):
            # Import the qualified version and hand it back as the bare-named module.
            return importlib.import_module(f"downloader_core.{spec.name}")

        def exec_module(self, module):
            pass  # already fully initialised by create_module

    if not any(isinstance(x, _CoreAliasImporter) for x in sys.meta_path):
        sys.meta_path.insert(0, _CoreAliasImporter())
else:
    if _PACKAGE_ROOT_STR not in sys.path:
        # Keep legacy intra-core imports working while the implementation
        # lives under a package.
        sys.path.insert(0, _PACKAGE_ROOT_STR)