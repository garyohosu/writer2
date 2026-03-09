from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
CLASS_DIAGRAM_PATH = ROOT / "class.md"
SKIP_SOURCE_DIRS = {".git", ".venv", "venv", "__pycache__", "tests"}
ENUM_BASE_NAMES = {"Enum", "StrEnum", "IntEnum"}

CLASS_START_RE = re.compile(r"^\s*class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$")
ATTRIBUTE_RE = re.compile(r"^\s*[+\-#]?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:")
METHOD_RE = re.compile(r"^\s*[+\-#]?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(")
INHERITANCE_RE = re.compile(
    r"^\s*(?P<base>[A-Za-z_][A-Za-z0-9_]*)\s+<\|--\s+(?P<derived>[A-Za-z_][A-Za-z0-9_]*)"
)


@dataclass
class DiagramClassContract:
    name: str
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    enum_members: list[str] = field(default_factory=list)
    is_enum: bool = False
    is_abstract: bool = False


@dataclass
class DiagramContract:
    classes: dict[str, DiagramClassContract]
    inheritance_edges: list[tuple[str, str]]


@dataclass
class SourceClassSnapshot:
    name: str
    fields: set[str] = field(default_factory=set)
    methods: set[str] = field(default_factory=set)
    bases: set[str] = field(default_factory=set)
    is_enum: bool = False
    is_abstract: bool = False
    enum_member_names: set[str] = field(default_factory=set)
    enum_member_values: set[str] = field(default_factory=set)


def _extract_primary_mermaid_block(document: str) -> str:
    blocks = document.split("```mermaid")
    if len(blocks) < 2:
        raise AssertionError("class.md does not contain a mermaid block.")

    first_block = blocks[1].split("```", 1)[0]
    if "classDiagram" not in first_block:
        raise AssertionError("The first mermaid block is not a class diagram.")
    return first_block


def parse_class_diagram_contract(path: Path) -> DiagramContract:
    block = _extract_primary_mermaid_block(path.read_text(encoding="utf-8"))
    classes: dict[str, DiagramClassContract] = {}
    inheritance_edges: list[tuple[str, str]] = []

    current: DiagramClassContract | None = None
    for raw_line in block.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("%%") or stripped == "classDiagram":
            continue

        if current is None:
            class_match = CLASS_START_RE.match(line)
            if class_match:
                name = class_match.group("name")
                current = DiagramClassContract(name=name)
                classes[name] = current
                continue

            inheritance_match = INHERITANCE_RE.match(line)
            if inheritance_match:
                inheritance_edges.append(
                    (
                        inheritance_match.group("base"),
                        inheritance_match.group("derived"),
                    )
                )
            continue

        if stripped == "}":
            current = None
            continue

        if stripped == "<<enumeration>>":
            current.is_enum = True
            continue

        if stripped == "<<abstract>>":
            current.is_abstract = True
            continue

        method_match = METHOD_RE.match(line)
        if method_match:
            current.methods.append(method_match.group("name"))
            continue

        attribute_match = ATTRIBUTE_RE.match(line)
        if attribute_match:
            current.attributes.append(attribute_match.group("name"))
            continue

        if current.is_enum and re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", stripped):
            current.enum_members.append(stripped)

    if not classes:
        raise AssertionError("No classes were parsed from class.md.")

    return DiagramContract(classes=classes, inheritance_edges=inheritance_edges)


def discover_python_sources(root: Path) -> list[Path]:
    sources: list[Path] = []
    for path in root.rglob("*.py"):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_SOURCE_DIRS for part in relative_parts):
            continue
        sources.append(path)
    return sorted(sources)


def _last_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _last_name(node.value)
    if isinstance(node, ast.Call):
        return _last_name(node.func)
    return None


def _self_attribute_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    names.add(target.attr)
        elif isinstance(child, ast.AnnAssign):
            target = child.target
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                names.add(target.attr)
    return names


def _enum_members_from_class(node: ast.ClassDef) -> tuple[set[str], set[str]]:
    member_names: set[str] = set()
    member_values: set[str] = set()
    for child in node.body:
        if isinstance(child, ast.Assign):
            if len(child.targets) != 1 or not isinstance(child.targets[0], ast.Name):
                continue
            member_names.add(child.targets[0].id)
            if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                member_values.add(child.value.value)
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            member_names.add(child.target.id)
            if isinstance(child.value, ast.Constant) and isinstance(child.value.value, str):
                member_values.add(child.value.value)
    return member_names, member_values


def build_source_snapshot(paths: list[Path]) -> dict[str, SourceClassSnapshot]:
    snapshot: dict[str, SourceClassSnapshot] = {}
    for path in paths:
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in module.body:
            if not isinstance(node, ast.ClassDef):
                continue

            class_snapshot = snapshot.setdefault(node.name, SourceClassSnapshot(name=node.name))
            base_names = {_last_name(base) for base in node.bases}
            class_snapshot.bases.update(name for name in base_names if name)

            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_snapshot.methods.add(child.name)
                    if child.name == "__init__":
                        class_snapshot.fields.update(_self_attribute_names(child))
                    if any(_last_name(dec) == "abstractmethod" for dec in child.decorator_list):
                        class_snapshot.is_abstract = True
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    class_snapshot.fields.add(child.target.id)
                elif isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name):
                            class_snapshot.fields.add(target.id)

            if class_snapshot.bases.intersection(ENUM_BASE_NAMES):
                class_snapshot.is_enum = True
                enum_names, enum_values = _enum_members_from_class(node)
                class_snapshot.enum_member_names.update(enum_names)
                class_snapshot.enum_member_values.update(enum_values)

            if class_snapshot.bases.intersection({"ABC", "ABCMeta"}):
                class_snapshot.is_abstract = True

    return snapshot


@pytest.fixture(scope="module")
def diagram_contract() -> DiagramContract:
    return parse_class_diagram_contract(CLASS_DIAGRAM_PATH)


@pytest.fixture(scope="module")
def source_snapshot() -> dict[str, SourceClassSnapshot]:
    sources = discover_python_sources(ROOT)
    if not sources:
        pytest.skip(
            "No Python implementation files were found. "
            "These contract tests activate once source files are added."
        )
    return build_source_snapshot(sources)


def test_class_diagram_contract_is_parseable(diagram_contract: DiagramContract) -> None:
    assert "RunDaily" in diagram_contract.classes
    assert "BaseAgent" in diagram_contract.classes
    assert "PublicationMode" in diagram_contract.classes
    assert diagram_contract.classes["BaseAgent"].is_abstract is True
    assert diagram_contract.classes["PublicationMode"].is_enum is True
    assert ("BaseAgent", "PlotAgent") in diagram_contract.inheritance_edges


def test_all_diagram_classes_exist(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    expected_classes = set(diagram_contract.classes)
    implemented_classes = set(source_snapshot)
    missing = sorted(expected_classes - implemented_classes)
    assert not missing, f"Classes missing from implementation: {missing}"


def test_enum_contracts_match_class_diagram(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    mismatches: list[str] = []
    for contract in diagram_contract.classes.values():
        if not contract.is_enum:
            continue

        implementation = source_snapshot[contract.name]
        if not implementation.is_enum:
            mismatches.append(f"{contract.name} is not implemented as an Enum subclass")
            continue

        actual_members = implementation.enum_member_names | implementation.enum_member_values
        missing_members = sorted(set(contract.enum_members) - actual_members)
        if missing_members:
            mismatches.append(f"{contract.name} is missing enum members: {missing_members}")

    assert not mismatches, " ; ".join(mismatches)


def test_abstract_classes_are_marked_abstract(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    mismatches: list[str] = []
    for contract in diagram_contract.classes.values():
        if not contract.is_abstract:
            continue

        implementation = source_snapshot[contract.name]
        if not implementation.is_abstract:
            mismatches.append(f"{contract.name} is not marked abstract in implementation")

    assert not mismatches, " ; ".join(mismatches)


def test_method_contracts_match_class_diagram(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    mismatches: list[str] = []
    for contract in diagram_contract.classes.values():
        implementation = source_snapshot[contract.name]
        missing_methods = sorted(set(contract.methods) - implementation.methods)
        if missing_methods:
            mismatches.append(f"{contract.name} is missing methods: {missing_methods}")

    assert not mismatches, " ; ".join(mismatches)


def test_attribute_contracts_match_class_diagram(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    mismatches: list[str] = []
    for contract in diagram_contract.classes.values():
        if contract.is_enum:
            continue

        implementation = source_snapshot[contract.name]
        missing_fields = sorted(set(contract.attributes) - implementation.fields)
        if missing_fields:
            mismatches.append(f"{contract.name} is missing attributes: {missing_fields}")

    assert not mismatches, " ; ".join(mismatches)


def test_inheritance_contracts_match_class_diagram(
    diagram_contract: DiagramContract,
    source_snapshot: dict[str, SourceClassSnapshot],
) -> None:
    mismatches: list[str] = []
    for base_name, derived_name in diagram_contract.inheritance_edges:
        if derived_name not in source_snapshot:
            mismatches.append(f"{derived_name} is missing; cannot verify inheritance from {base_name}")
            continue

        implementation = source_snapshot[derived_name]
        if base_name not in implementation.bases:
            mismatches.append(f"{derived_name} does not inherit from {base_name}")

    assert not mismatches, " ; ".join(mismatches)
