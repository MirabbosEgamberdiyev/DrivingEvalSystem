"""Hardware fingerprinting and tolerant machine identification on Windows and Linux.

Collects 4 distinct hardware signatures:
1. Motherboard UUID
2. CPU Processor ID
3. Primary Disk Serial
4. Network Adapter MAC Address

Implements a 3-of-4 quorum (75% tolerance): replacing 1 hardware component
(e.g., hard drive or network adapter) preserves valid license operation.
"""

import hashlib
import logging
import platform
import subprocess
import uuid
from dataclasses import dataclass

logger = logging.getLogger("driving_eval.licensing.machine_id")


@dataclass
class MachineFingerprint:
    """Hardware components fingerprint hashes."""

    board_hash: str
    cpu_hash: str
    disk_hash: str
    mac_hash: str

    def to_dict(self) -> dict[str, str]:
        return {
            "board": self.board_hash,
            "cpu": self.cpu_hash,
            "disk": self.disk_hash,
            "mac": self.mac_hash,
        }

    @property
    def canonical_id(self) -> str:
        """Human-readable truncated machine identifier."""
        return f"MCH-{self.board_hash[:6]}-{self.cpu_hash[:6]}-{self.disk_hash[:6]}-{self.mac_hash[:6]}".upper()

    def match(self, other: "MachineFingerprint", min_matching: int = 3) -> tuple[bool, int]:
        """Evaluates hardware match with tolerance.

        Returns (is_valid, matching_components_count).
        Requires at least min_matching components out of 4 to match.
        """
        matches = 0
        if self.board_hash == other.board_hash:
            matches += 1
        if self.cpu_hash == other.cpu_hash:
            matches += 1
        if self.disk_hash == other.disk_hash:
            matches += 1
        if self.mac_hash == other.mac_hash:
            matches += 1

        is_valid = matches >= min_matching
        return is_valid, matches


def _hash_component(raw_value: str, fallback_prefix: str) -> str:
    cleaned = raw_value.strip().replace(" ", "").replace("\r", "").replace("\n", "")
    if not cleaned or cleaned.lower() in ("to be filled by o.e.m.", "none", "0", "default string"):
        cleaned = f"{fallback_prefix}_DEFAULT_STATION"
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:32]


def _get_windows_wmic_or_powershell(wmic_args: list[str], ps_cmd: str) -> str:
    """Attempts WMIC command, falling back to PowerShell Get-CimInstance."""
    # 1. Try wmic
    try:
        res = subprocess.run(
            ["wmic"] + wmic_args,
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
            if len(lines) >= 2:
                return lines[1]
    except Exception:
        pass

    # 2. Try powershell
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=2.5,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass

    return ""


def get_motherboard_uuid() -> str:
    """Extracts system motherboard/system UUID."""
    if platform.system() == "Windows":
        val = _get_windows_wmic_or_powershell(
            ["csproduct", "get", "uuid"],
            "(Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID",
        )
        if val:
            return val
    elif platform.system() == "Linux":
        for path in ("/sys/class/dmi/id/product_uuid", "/etc/machine-id"):
            try:
                with open(path, encoding="utf-8") as f:
                    c = f.read().strip()
                    if c:
                        return c
            except Exception:
                continue

    return f"BOARD_FALLBACK_{platform.node()}"


def get_cpu_id() -> str:
    """Extracts CPU Processor ID."""
    if platform.system() == "Windows":
        val = _get_windows_wmic_or_powershell(
            ["cpu", "get", "processorid"],
            "(Get-CimInstance -ClassName Win32_Processor).ProcessorId",
        )
        if val:
            return val
    elif platform.system() == "Linux":
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if "Serial" in line or "model name" in line:
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass

    return f"CPU_FALLBACK_{platform.processor() or 'GENERIC'}"


def get_disk_serial() -> str:
    """Extracts primary storage disk serial number."""
    if platform.system() == "Windows":
        val = _get_windows_wmic_or_powershell(
            ["diskdrive", "get", "serialnumber"],
            "(Get-CimInstance -ClassName Win32_DiskDrive | Select-Object -First 1).SerialNumber",
        )
        if val:
            return val
    elif platform.system() == "Linux":
        try:
            res = subprocess.run(["lsblk", "-ndo", "SERIAL"], capture_output=True, text=True, timeout=2.0, check=False)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.splitlines()[0].strip()
        except Exception:
            pass

    return "DISK_FALLBACK_NVME_PRIMARY"


def get_mac_address() -> str:
    """Extracts primary physical network interface MAC address."""
    raw_node = uuid.getnode()
    mac = ":".join(f"{(raw_node >> ele) & 0xff:02x}" for ele in range(0, 48, 8)[::-1])
    return mac


def get_current_machine_fingerprint(
    override_board: str | None = None,
    override_cpu: str | None = None,
    override_disk: str | None = None,
    override_mac: str | None = None,
) -> MachineFingerprint:
    """Collects current hardware signatures and generates normalized MachineFingerprint."""
    raw_board = override_board if override_board is not None else get_motherboard_uuid()
    raw_cpu = override_cpu if override_cpu is not None else get_cpu_id()
    raw_disk = override_disk if override_disk is not None else get_disk_serial()
    raw_mac = override_mac if override_mac is not None else get_mac_address()

    return MachineFingerprint(
        board_hash=_hash_component(raw_board, "BOARD"),
        cpu_hash=_hash_component(raw_cpu, "CPU"),
        disk_hash=_hash_component(raw_disk, "DISK"),
        mac_hash=_hash_component(raw_mac, "MAC"),
    )


def parse_fingerprint_dict(data: dict[str, str]) -> MachineFingerprint:
    return MachineFingerprint(
        board_hash=data.get("board", ""),
        cpu_hash=data.get("cpu", ""),
        disk_hash=data.get("disk", ""),
        mac_hash=data.get("mac", ""),
    )
