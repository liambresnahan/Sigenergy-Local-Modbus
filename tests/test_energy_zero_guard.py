"""Regression tests for protected energy zero-bounce handling."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "sigen"
    / "sensor.py"
)


def _source_tree() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _assigned_string_set(tree: ast.Module, name: str) -> set[str]:
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    call = assignment.value
    assert isinstance(call, ast.Call)
    values = call.args[0]
    assert isinstance(values, ast.Set)
    return {
        element.value
        for element in values.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }


class TestEnergyZeroGuard(unittest.TestCase):
    """Ensure lifetime and daily energy counters keep distinct reset rules."""

    def test_dc_charger_total_is_protected_as_lifetime_energy(self) -> None:
        tree = _source_tree()

        self.assertIn(
            "dc_charger_total_charging_capacity",
            _assigned_string_set(tree, "_PROTECTED_LIFETIME_ENERGY_KEYS"),
        )
        self.assertNotIn(
            "dc_charger_total_charging_capacity",
            _assigned_string_set(tree, "_PROTECTED_DAILY_ENERGY_KEYS"),
        )

    def test_midnight_reset_exception_is_limited_to_daily_energy(self) -> None:
        tree = _source_tree()
        sensor_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "SigenergySensor"
        )
        guard = next(
            node
            for node in sensor_class.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "_apply_energy_zero_guard"
        )

        midnight_calls = [
            node
            for node in ast.walk(guard)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_is_near_daily_reset"
        ]
        self.assertEqual(1, len(midnight_calls))

        midnight_if = next(
            node
            for node in ast.walk(guard)
            if isinstance(node, ast.If)
            and any(call is midnight_calls[0] for call in ast.walk(node.test))
        )
        self.assertTrue(
            any(
                isinstance(node, ast.Name) and node.id == "is_daily"
                for node in ast.walk(midnight_if.test)
            )
        )


if __name__ == "__main__":
    unittest.main()
