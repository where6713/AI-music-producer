from apps.cli.translation import translate_result


def test_translate_result_formats_known_messages() -> None:
    message = translate_result(
        "plan_missing",
        "error",
        {"plan_path": "plans/phase03.md"},
    )

    assert message == "Plan file not found: plans/phase03.md"


def test_translate_result_handles_missing_context_keys() -> None:
    message = translate_result("resume", "ok")

    assert message == "Resuming from checkpoint (step={step})"


def test_translate_result_falls_back_on_unknown_action() -> None:
    message = translate_result("unknown_action", "unknown_status")

    assert message == "Action unknown_action returned status unknown_status."
