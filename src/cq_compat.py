"""Compatibility shim that neutralizes cq_warehouse's unsafe Shape copy patch.

``cq_warehouse.extensions``, on import, replaces several ``cadquery`` ``Shape`` methods
(``copy``, ``_apply_transform``, ``located``, ``moved``) with implementations that run
``copy.deepcopy``. cadquery 2.7.0 implements deepcopy via ``__getstate__``/``__setstate__``
using ``BinTools.Write_s``/``Read_s``; on OCCT 7.8 the read side aborts on some geometry
with ``BinTools_SurfaceSet::ReadGeometry: UnExpected BRep_PointRepresentation``. Because the
patch is global, any copy or transform in the process can hit it once cq_warehouse is
loaded.

``import_cq_warehouse_extensions`` imports the extensions for their legitimate ``Workplane``
side effects (``insertHole`` etc.) and then restores cadquery's native, serialization-free
``BRepBuilderAPI_Copy``-based methods.
"""

import sys

import cadquery.occ_impl.shapes as _shapes

# Methods cq_warehouse.extensions overwrites that route through copy.deepcopy.
_PATCHED_METHODS = ("copy", "_apply_transform", "located", "moved")

_restored = False


def import_cq_warehouse_extensions() -> None:
    """Import ``cq_warehouse.extensions`` and restore native ``Shape`` copy/transform.

    Idempotent: only the first call does work, so it is safe to call from multiple import
    sites.
    """
    global _restored
    if _restored:
        return

    shape = _shapes.Shape
    already_loaded = "cq_warehouse.extensions" in sys.modules
    native = {name: getattr(shape, name) for name in _PATCHED_METHODS}

    import cq_warehouse.extensions  # noqa: F401 -- side effect: Workplane.insertHole etc.

    if already_loaded:
        # The snapshot above was taken after the patch was already installed, so it holds
        # the patched methods. Reinstate serialization-free implementations instead.
        _install_native_fallback(shape)
    else:
        for name, func in native.items():
            setattr(shape, name, func)

    _restored = True


def _install_native_fallback(shape) -> None:
    """Re-implement serialization-free copy/transform when the native snapshot was
    unavailable (extensions imported before the shim ran). ``located``/``moved`` call
    ``self.copy()`` and so become safe once ``copy`` is native."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy, BRepBuilderAPI_Transform

    def copy(self, mesh: bool = False):
        return self.__class__(BRepBuilderAPI_Copy(self.wrapped, True, mesh).Shape())

    def _apply_transform(self, tr):
        return self.__class__(BRepBuilderAPI_Transform(self.wrapped, tr, True).Shape())

    shape.copy = copy
    shape._apply_transform = _apply_transform
