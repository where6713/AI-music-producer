from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import get_type_hints


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


tool_contracts = importlib.import_module("producer_tools.contracts")


BUSINESS_TOOLS = (
    "producer_tools.business.acoustic_analyst",
    "producer_tools.business.style_deconstructor",
    "producer_tools.business.friction_calculator",
    "producer_tools.business.lyric_architect",
    "producer_tools.business.prompt_compiler",
    "producer_tools.business.post_processor",
)

SELF_CHECK_TOOLS = (
    "producer_tools.self_check.shell_probe",
    "producer_tools.self_check.py_eval",
)


def _assert_contract_annotations(module_path: str) -> None:
    module = importlib.import_module(module_path)
    hints = get_type_hints(module.run, globalns=module.__dict__)
    assert hints["payload"] == tool_contracts.ToolPayload
    assert hints["return"] == tool_contracts.ToolResult


def test_tool_contract_annotations_match_contracts() -> None:
    for module_path in BUSINESS_TOOLS + SELF_CHECK_TOOLS:
        _assert_contract_annotations(module_path)


def test_tool_contract_protocol_shape() -> None:
    hints = get_type_hints(tool_contracts.ToolContract)
    assert hints["TOOL_NAME"] is str
    assert hints["run"] == tool_contracts.ToolCallable
