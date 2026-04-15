from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Callable, cast


SRC_ROOT = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_ROOT))


BUSINESS_TOOL_SKELETONS: tuple[str, ...] = ()

BUSINESS_TOOL_IMPLEMENTED = (
    "producer_tools.business.acoustic_analyst",
    "producer_tools.business.style_deconstructor",
    "producer_tools.business.friction_calculator",
    "producer_tools.business.lyric_architect",
    "producer_tools.business.prompt_compiler",
    "producer_tools.business.post_processor",
)

SELF_CHECK_TOOL_SKELETONS: tuple[str, ...] = ()

SELF_CHECK_TOOL_IMPLEMENTED = (
    "producer_tools.self_check.shell_probe",
    "producer_tools.self_check.py_eval",
)


def _assert_tool_contract(module_path: str) -> None:
    module = importlib.import_module(module_path)

    assert hasattr(module, "TOOL_NAME")
    assert hasattr(module, "run")
    run = cast(Callable[[dict[str, object]], dict[str, object]], module.run)
    assert callable(run)

    try:
        _ = run({"_skeleton": True})
    except NotImplementedError:
        return

    raise AssertionError("run() should be a skeleton NotImplementedError")


def _assert_tool_contract_exists(module_path: str) -> None:
    module = importlib.import_module(module_path)

    assert hasattr(module, "TOOL_NAME")
    assert hasattr(module, "run")
    run = cast(Callable[[dict[str, object]], dict[str, object]], module.run)
    assert callable(run)


def test_business_tool_skeletons_exist() -> None:
    for module_path in BUSINESS_TOOL_SKELETONS:
        _assert_tool_contract(module_path)


def test_business_tools_expose_contracts() -> None:
    for module_path in BUSINESS_TOOL_IMPLEMENTED:
        _assert_tool_contract_exists(module_path)


def test_self_check_tool_skeletons_exist() -> None:
    for module_path in SELF_CHECK_TOOL_SKELETONS:
        _assert_tool_contract(module_path)


def test_self_check_tools_expose_contracts() -> None:
    for module_path in SELF_CHECK_TOOL_IMPLEMENTED:
        _assert_tool_contract_exists(module_path)
