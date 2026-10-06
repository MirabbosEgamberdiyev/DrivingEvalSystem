"""Unit and integration tests for Setup Wizard service and QML bridge."""

import tempfile
from pathlib import Path

import yaml

from driving_eval.core.state_machine import ApplicationState, ApplicationStateMachine
from driving_eval.ui_qml.bridge.setup_wizard_bridge import SetupWizardBridge
from driving_eval.wizard.setup_service import SetupStep, SetupWizardService


def test_setup_wizard_full_stage_progression():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_file = Path(tmp_dir) / "config.yaml"
        # Seed test config
        cfg_file.write_text(
            yaml.dump({
                "system": {"default_language": "uz-Latn"},
                "cameras": {
                    "front": {"source": "0", "resolution": [1920, 1080], "fps": 30},
                    "rear": {"source": "1", "resolution": [1920, 1080], "fps": 30},
                    "left": {"source": "2", "resolution": [1920, 1080], "fps": 30},
                    "right": {"source": "3", "resolution": [1920, 1080], "fps": 30},
                },
            }),
            encoding="utf-8",
        )

        app_sm = ApplicationStateMachine(initial_state=ApplicationState.SETUP_REQUIRED)
        wizard = SetupWizardService(config_path=cfg_file, app_state_machine=app_sm)

        # Initial Step 0: LANGUAGE_EULA
        assert wizard.current_step == SetupStep.LANGUAGE_EULA
        assert wizard.current_step_index == 0
        assert wizard.total_steps == 7
        assert wizard.can_proceed() is False  # Cannot proceed without agreeing to EULA

        # 1. Confirm Language & Agree EULA
        wizard.confirm_language_and_eula("uz-Cyrl", agreed=True)
        assert wizard.can_proceed() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == SetupStep.HARDWARE_USB.value

        # 2. Hardware & USB Analysis
        assert wizard.current_step == SetupStep.HARDWARE_USB
        hw = wizard.analyze_hardware_and_usb()
        assert hw.cpu_cores > 0
        assert hw.ram_gb > 0.0
        assert hw.free_disk_gb > 0.0
        assert len(hw.camera_distribution) == 4
        assert wizard.can_proceed() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == SetupStep.CAMERA_STREAMS.value

        # 3. 4 Camera Streams
        assert wizard.current_step == SetupStep.CAMERA_STREAMS
        wizard.configure_camera_mapping("FRONT", "0", [1920, 1080], 30)
        wizard.configure_camera_mapping("REAR", "1", [1920, 1080], 30)
        wizard.configure_camera_mapping("LEFT", "2", [1920, 1080], 30)
        wizard.configure_camera_mapping("RIGHT", "3", [1920, 1080], 30)
        assert wizard.can_proceed() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == SetupStep.CALIBRATION.value

        # 4. Calibration Check
        assert wizard.current_step == SetupStep.CALIBRATION
        calib = wizard.verify_calibration()
        assert len(calib.cameras_checked) == 4
        assert calib.is_valid is True
        assert wizard.can_proceed() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == SetupStep.AUTODROME_ZONES.value

        # 5. Autodrome Zones
        assert wizard.current_step == SetupStep.AUTODROME_ZONES
        assert wizard.configure_autodrome_zones() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == SetupStep.AUDIO_TEST.value

        # 6. Audio Test
        assert wizard.current_step == SetupStep.AUDIO_TEST
        assert wizard.can_proceed() is False  # Audio not tested yet
        # Run test audio (will use fallback winsound or mock in audio service)
        wizard.test_audio_output()
        assert wizard.can_proceed() is True
        ok, next_step = wizard.next_step()
        assert ok is True
        assert next_step == "FINAL_SUMMARY"

        # 7. Final Summary & Save
        assert wizard.current_step == SetupStep.FINAL_SUMMARY
        save_ok = wizard.finalize_and_save_configuration()
        assert save_ok is True

        # State machine transition to READY
        assert app_sm.current_state == ApplicationState.READY

        # Verify config saved atomically
        saved_cfg = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
        assert saved_cfg["system"]["default_language"] == "uz-Cyrl"
        assert saved_cfg["cameras"]["front"]["source"] == "0"


def test_setup_wizard_navigation_and_boundaries():
    wizard = SetupWizardService()
    assert wizard.current_step_index == 0

    # prev_step at start returns False
    ok, _ = wizard.prev_step()
    assert ok is False

    # cannot advance without completing current step
    ok, _ = wizard.next_step()
    assert ok is False


def test_setup_wizard_qml_bridge():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cfg_file = Path(tmp_dir) / "config.yaml"
        cfg_file.write_text("system: {}\n", encoding="utf-8")

        wizard = SetupWizardService(config_path=cfg_file)
        bridge = SetupWizardBridge(wizard_service=wizard)

        assert bridge.getCurrentStepIndex() == 0
        assert bridge.getTotalSteps() == 7
        assert bridge.canProceed() is False

        # Select language and agree to EULA
        bridge.selectLanguage("uz-Cyrl")
        bridge.setEulaAgreed(True)
        assert bridge.canProceed() is True
        assert bridge.getSelectedLanguage() == "uz-Cyrl"

        # Run hardware scan via slot
        bridge.runHardwareScan()

        # Camera source slot
        bridge.setCameraSource("FRONT", "0")

        # Calibration check slot
        bridge.runCalibrationCheck()

        # Audio test slot
        bridge.playAudioTest()

        # Step navigation
        bridge.nextStep()
        assert bridge.getCurrentStepIndex() == 1

        bridge.prevStep()
        assert bridge.getCurrentStepIndex() == 0

        # Save slot
        bridge.saveAndComplete()
