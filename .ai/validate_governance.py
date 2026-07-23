#!/usr/bin/env python3
"""Validate the active governance files without touching application data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".ai" / "WORKFLOW.yml"
PROJECT = ROOT / ".ai" / "PROJECT.yml"
AGENTS = ROOT / "AGENTS.md"
ACTIVE_TEXT_FILES = [
    AGENTS,
    ROOT / "README.md",
    WORKFLOW,
    PROJECT,
    ROOT / ".ai" / "templates" / "TASK_STATUS.yml",
    ROOT / "docs" / "model-governance" / "MODEL_STORAGE.md",
]
REMOVED_ACTIVE_TERMS = (
    "IA autora remota",
    "IA auditora",
    "executor local",
    "handoff obrigatório",
    "Versão do retorno",
)


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"duplicate key: {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    construct_unique_mapping,
)


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as source:
        return yaml.load(source, Loader=UniqueKeyLoader)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    yaml_files = sorted((ROOT / ".ai").rglob("*.yml"))
    parsed: dict[Path, Any] = {}
    for path in yaml_files:
        try:
            parsed[path] = load_yaml(path)
        except (OSError, yaml.YAMLError) as error:
            errors.append(f"{path.relative_to(ROOT)}: {error}")

    workflow = parsed.get(WORKFLOW, {})
    project = parsed.get(PROJECT, {})
    require(isinstance(workflow, dict), "WORKFLOW.yml must be a mapping", errors)
    require(isinstance(project, dict), "PROJECT.yml must be a mapping", errors)

    for section in (
        "authority",
        "startup",
        "task_state",
        "execution",
        "git",
        "validation",
        "merge",
        "safety",
        "portability",
        "completion",
    ):
        require(section in workflow, f"WORKFLOW.yml missing section: {section}", errors)

    mandatory = workflow.get("safety", {}).get("mandatory", {})
    required_protections = (
        "no_direct_main_edit",
        "no_preexisting_work_overwrite",
        "no_automatic_stash",
        "no_force_push",
        "no_hard_reset",
        "no_secret_commit_or_report",
        "no_arbitrary_conflict_resolution",
        "corrections_only_in_authorized_scope",
        "report_only_executed_results",
    )
    for protection in required_protections:
        require(
            mandatory.get(protection) is True,
            f"mandatory safety protection is absent or disabled: {protection}",
            errors,
        )

    require(
        workflow.get("authority", {}).get("canonical_source") == ".ai/WORKFLOW.yml",
        "WORKFLOW.yml must identify itself as the canonical operational source",
        errors,
    )
    require(
        ".ai/WORKFLOW.yml" in AGENTS.read_text(encoding="utf-8"),
        "AGENTS.md must point to the canonical workflow",
        errors,
    )

    for path in ACTIVE_TEXT_FILES:
        if not path.exists():
            errors.append(f"missing active governance file: {path.relative_to(ROOT)}")
            continue
        content = path.read_text(encoding="utf-8")
        for term in REMOVED_ACTIVE_TERMS:
            if term.casefold() in content.casefold():
                errors.append(
                    f"{path.relative_to(ROOT)} contains removed active term: {term}"
                )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Governance validation succeeded: {len(yaml_files)} YAML files checked.")
    print("Duplicate YAML keys: none.")
    print("Mandatory safety protections: present.")
    print("Removed active workflow references: none.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
