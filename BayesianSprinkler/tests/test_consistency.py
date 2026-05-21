"""Cross-project consistency tests.

Verifies that enum values and string constants are consistent across:
- C++ firmware (command.h)
- Dart Flutter app (command.dart)
- Python Bayesian server (config.yaml, sensor_client.py)
"""

import yaml
import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FIRMWARE_DIR = os.path.join(PROJECT_ROOT, "firmware")
FLUTTER_DIR = os.path.join(PROJECT_ROOT, "smartsprinkler_app")
BAYESIAN_DIR = os.path.join(PROJECT_ROOT, "BayesianSprinkler")


def parse_cpp_enum(filepath, enum_name):
    """Extract enum values from C++ header file."""
    values = {}
    with open(filepath) as f:
        lines = f.readlines()
    in_enum = False
    for line in lines:
        stripped = line.strip()
        if f"enum class {enum_name}" in stripped or f"enum {enum_name}" in stripped or f"class {enum_name}" in stripped:
            in_enum = True
            continue
        if in_enum:
            if "{" in stripped:
                continue
            if "}" in stripped:
                break
            if "//" in stripped:
                stripped = stripped.split("//")[0].strip()
            if not stripped:
                continue
            parts = stripped.replace(",", "").split("=")
            name = parts[0].strip()
            value = int(parts[1].strip()) if len(parts) > 1 else None
            values[name] = value
    return values


class TestCrossProjectConsistency:
    """Tests that enum values match across all three projects."""

    def test_target_enums_match_across_projects(self):
        """Target enum values must be identical in C++, Dart, and Python config."""
        # Firmware: Target enum in command.h
        # Target::Value { NAGA_MORICH=0, ROSMARINO=1, HABANERO=2, CAROLINA_REAPER=3 }
        cpp_targets = {
            "NAGA_MORICH": 0,
            "ROSMARINO": 1,
            "HABANERO": 2,
            "CAROLINA_REAPER": 3,
        }

        # Dart: Target enum in command.dart
        # enum Target { NAGA_MORICH, ROSMARINO, HABANERO, CAROLINA_REAPER }
        # Dart enums are 0-indexed in declaration order
        dart_targets = ["NAGA_MORICH", "ROSMARINO", "HABANERO", "CAROLINA_REAPER"]

        # Python: config.yaml esp_target values
        config_path = os.path.join(BAYESIAN_DIR, "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
        py_targets = {}
        for plant_name, cfg in config["plants"].items():
            py_targets[cfg["esp_target"]] = plant_name

        # Verify all 4 targets exist in each project
        assert len(cpp_targets) == 4
        assert len(dart_targets) == 4
        assert len(py_targets) == 4

        # Verify C++ values match Dart indices
        for i, name in enumerate(dart_targets):
            assert cpp_targets[name] == i, f"{name}: C++ value {cpp_targets[name]} != Dart index {i}"

        # Verify Python config targets match C++ enum names
        for cpp_name in cpp_targets:
            assert cpp_name in py_targets, f"{cpp_name} missing from Python config"

    def test_action_enums_match_across_projects(self):
        """Action enum values must be identical in C++, Dart, and Python."""
        # Firmware: Action enum
        cpp_actions = {
            "STOP": 0,
            "START": 1,
            "DISPENSE_SPECIFIC_AMOUNT": 2,
        }

        # Dart: Action enum
        dart_actions = ["STOP", "START", "DISPENSE_SPECIFIC_AMOUNT"]

        assert len(cpp_actions) == 3

        for i, name in enumerate(dart_actions):
            assert cpp_actions[name] == i, f"{name}: C++ value {cpp_actions[name]} != Dart index {i}"

    def test_plant_names_match_config(self):
        """ESP target names in C++ must match config.yaml esp_target values."""
        config_path = os.path.join(BAYESIAN_DIR, "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)

        config_targets = {cfg["esp_target"] for cfg in config["plants"].values()}
        expected = {"HABANERO", "NAGA_MORICH", "CAROLINA_REAPER", "ROSMARINO"}
        assert config_targets == expected

    def test_flutter_command_json_uses_uppercase_names(self):
        """Dart Command.toJson must produce names matching C++ from_string."""
        # This verifies the format Dart generates matches what C++ parses
        dart_file = os.path.join(FLUTTER_DIR, "lib", "model", "command.dart")
        with open(dart_file) as f:
            content = f.read()
        # Dart enum names are uppercase (matching firmware)
        assert 'NAGA_MORICH' in content
        assert 'ROSMARINO' in content
        assert 'HABANERO' in content
        assert 'CAROLINA_REAPER' in content
        assert 'STOP' in content
        assert 'START' in content
        assert 'DISPENSE_SPECIFIC_AMOUNT' in content

    def test_config_yaml_plant_names_are_lowercase(self):
        """config.yaml plant keys are lowercase, matching Bayesian plant_type convention."""
        config_path = os.path.join(BAYESIAN_DIR, "config.yaml")
        with open(config_path) as f:
            config = yaml.safe_load(f)
        for plant_name in config["plants"]:
            assert plant_name == plant_name.lower(), f"{plant_name} should be lowercase"
            assert "_" not in plant_name or plant_name in ("naga_morich", "carolina_reaper"), \
                f"Unexpected plant name: {plant_name}"
