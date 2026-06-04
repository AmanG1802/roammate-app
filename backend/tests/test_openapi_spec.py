"""
Spec conformance tests.

1. test_spec_is_valid             — openapi.yaml parses and passes OpenAPI 3.0 validation.
2. test_spec_coverage             — sanity: ≥80 paths, all 3 security schemes present.
3. test_all_paths_have_summary    — every operation must have a summary.
4. test_all_operations_have_op_id — every operation must have an operationId.
5. test_registry_covers_spec      — every spec operationId has a handler in registry.py.
                                     CI fails here if a spec operation has no implementation.

Run with:  pytest tests/test_openapi_spec.py -v
"""
import os
from pathlib import Path

import pytest
import yaml

SPEC_PATH = Path(__file__).resolve().parent.parent / "openapi.yaml"


@pytest.fixture(scope="module")
def spec():
    assert SPEC_PATH.exists(), (
        f"Spec file not found at {SPEC_PATH}. "
        "Create it at docs/api/openapi.yaml per the spec-first workflow."
    )
    with open(SPEC_PATH) as f:
        return yaml.safe_load(f)


def test_spec_is_valid():
    """The committed openapi.yaml passes OpenAPI 3.0 schema validation."""
    from openapi_spec_validator import validate
    from openapi_spec_validator.readers import read_from_filename
    spec_dict, _ = read_from_filename(str(SPEC_PATH))
    validate(spec_dict)


def test_spec_coverage(spec):
    """Basic sanity: enough paths and both auth schemes are declared."""
    paths = spec.get("paths", {})
    assert len(paths) >= 80, (
        f"Spec only has {len(paths)} paths — expected 80+. "
        "Check that all endpoint modules are documented."
    )
    security_schemes = spec.get("components", {}).get("securitySchemes", {})
    assert "bearerAuth" in security_schemes, "bearerAuth security scheme missing from spec"
    assert "cookieAuth" in security_schemes, "cookieAuth security scheme missing from spec"
    assert "adminAuth" in security_schemes, "adminAuth security scheme missing from spec"


def test_all_paths_have_summary(spec):
    """Every HTTP operation must have a summary field."""
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method in ("get", "post", "patch", "put", "delete") and isinstance(operation, dict):
                if not operation.get("summary"):
                    missing.append(f"{method.upper()} {path}")
    assert not missing, (
        f"These operations are missing a 'summary' in openapi.yaml:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )


def test_all_operations_have_op_id(spec):
    """Every HTTP operation must declare an operationId."""
    missing = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method in ("get", "post", "patch", "put", "delete") and isinstance(operation, dict):
                if not operation.get("operationId"):
                    missing.append(f"{method.upper()} {path}")
    assert not missing, (
        "These operations are missing 'operationId' in openapi.yaml:\n"
        + "\n".join(f"  {m}" for m in missing)
    )


def test_registry_covers_spec(spec):
    """
    Every spec operationId must have a handler registered in registry.py.

    This is the primary spec-first CI gate. If a spec operation has no handler
    implementation, the server will also refuse to start — this test catches it
    before deployment.
    """
    from app.api.registry import HANDLERS

    _HTTP = {"get", "post", "patch", "put", "delete", "head", "options"}
    unimplemented = []
    for path, methods in spec.get("paths", {}).items():
        for method, operation in methods.items():
            if method in _HTTP and isinstance(operation, dict):
                op_id = operation.get("operationId")
                if op_id and op_id not in HANDLERS:
                    unimplemented.append(f"{method.upper()} {path}  (operationId={op_id!r})")

    assert not unimplemented, (
        "Spec operations with no handler in app/api/registry.py:\n"
        + "\n".join(f"  {op}" for op in unimplemented)
    )
