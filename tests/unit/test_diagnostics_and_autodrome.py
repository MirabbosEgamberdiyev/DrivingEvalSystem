"""Unit tests for Stage 3: Real vs Mock Diagnostics, Temperature, and Dynamic Autodrome."""

from driving_eval.core.config_schema import SystemConfig
from driving_eval.db.repository import DatabaseRepository
from driving_eval.hardware.system_metrics import get_system_temperature_c
from driving_eval.ui_qml.bridge.real_bridge import RealBridge


def test_system_temperature_telemetry():
    """Verifies that get_system_temperature_c returns either float in valid range or None, never a hardcoded fake."""
    temp = get_system_temperature_c()
    if temp is not None:
        assert isinstance(temp, float)
        assert -20.0 <= temp <= 125.0
    else:
        # None is expected when ACPI thermal zone is unsupported (e.g. some VMs or desktops)
        assert temp is None


def test_real_bridge_diagnostics_live_telemetry(qapp, tmp_path):
    """Verifies that requestDiagnostics emits genuine telemetry with disconnected/simulation tags."""
    db_file = tmp_path / "diag_test.db"
    repo = DatabaseRepository(db_file)

    # Case A: Real mode (environment = production, sim_mode = False), no physical hardware
    config = SystemConfig.load_from_yaml("config/config.yaml")
    config.app.environment = "production"
    config.sensors.gps.sim_mode = False
    bridge = RealBridge(config=config, repository=repo)

    received_data = {}

    def on_diag(data):
        received_data.update(data)

    bridge.systemDiagnosticsUpdated.connect(on_diag)
    bridge.requestDiagnostics()

    assert "cpu_usage_pct" in received_data
    assert "ram_usage_pct" in received_data
    assert "disk_free_gb" in received_data
    assert "system_temp_c" in received_data
    assert "system_temp_str" in received_data
    assert received_data["system_temp_str"] in [f"{received_data['system_temp_c']} °C", "MA'LUMOT YO'Q"]

    # When hardware is not connected, status must be DISCONNECTED (not fake ONLINE / FIX_OK)
    for cam in received_data["cameras"]:
        assert cam["status"] == "DISCONNECTED"

    assert received_data["gps"]["status"] == "DISCONNECTED"
    assert received_data["obd"]["status"] == "DISCONNECTED"
    assert received_data["imu"]["status"] == "DISCONNECTED"

    # Case B: Simulation mode (environment = simulation, sim_mode = True)
    config_sim = SystemConfig.load_from_yaml("config/config.yaml")
    config_sim.app.environment = "simulation"
    config_sim.sensors.gps.sim_mode = True
    bridge_sim = RealBridge(config=config_sim, repository=repo)

    received_sim = {}
    bridge_sim.systemDiagnosticsUpdated.connect(lambda d: received_sim.update(d))
    bridge_sim.requestDiagnostics()

    for cam in received_sim["cameras"]:
        assert cam["status"] == "[SIMULATION]"

    assert received_sim["gps"]["status"] == "[SIMULATION]"
    assert received_sim["obd"]["status"] == "[SIMULATION]"
    assert received_sim["imu"]["status"] == "[SIMULATION]"


def test_autodrome_dynamic_loading(qapp, tmp_path):
    """Verifies that getAutodromeConfig and getAutodromeExercises read config/autodrome.json dynamically."""
    db_file = tmp_path / "autodrome_test.db"
    repo = DatabaseRepository(db_file)
    config = SystemConfig.load_from_yaml("config/config.yaml")
    bridge = RealBridge(config=config, repository=repo)

    poly_cfg = bridge.getAutodromeConfig()
    assert poly_cfg["name"] == "Tashkent Central Autodrome"
    assert poly_cfg["datum"] == "WGS84"
    assert poly_cfg["base_lat"] == 41.311081
    assert poly_cfg["base_lon"] == 69.240562
    assert "Poligon:" in poly_cfg["summary"]

    exercises = bridge.getAutodromeExercises()
    assert len(exercises) == 8
    expected_ids = ["START", "ESTAKADA", "ZMEIKA", "TURN_90", "PARALLEL_PARKING", "GARAGE_REVERSE", "STOP", "FINISH"]
    for i, ex in enumerate(exercises):
        assert ex["id"] == expected_ids[i]
        assert "name" in ex
        assert "desc" in ex
        assert "radius" in ex
        assert ex["active"] is True
