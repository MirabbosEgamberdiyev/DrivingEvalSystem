#!/bin/bash
# ==============================================================================
# UBUNTU LTS STANDALONE APPLIANCE DISK IMAGE CREATION SCRIPT
# Creates a minimal bootable raw/qcow2 image with kiosk autostart and offline wheels
# ==============================================================================

set -euo pipefail

IMAGE_NAME="driving_eval_appliance_ubuntu2204.raw"
IMAGE_SIZE="32G"
MOUNT_DIR="/mnt/autoeval_root"

echo "=== 1. Bo'sh disk obrazi yaratilmoqda (${IMAGE_SIZE}) ==="
qemu-img create -f raw "${IMAGE_NAME}" "${IMAGE_SIZE}"

echo "=== 2. Partitsiyalar bo'linmoqda (GPT: EFI, Root, Data) ==="
parted -s "${IMAGE_NAME}" mklabel gpt
parted -s "${IMAGE_NAME}" mkpart primary fat32 1MiB 512MiB      # EFI Boot
parted -s "${IMAGE_NAME}" set 1 esp on
parted -s "${IMAGE_NAME}" mkpart primary ext4 512MiB 16GiB      # System Root
parted -s "${IMAGE_NAME}" mkpart primary ext4 16GiB 100%        # Data Storage (NVMe SSD)

echo "=== 3. Loop qurilmasiga bog'lanmoqda ==="
LOOP_DEV=$(losetup -Pf --show "${IMAGE_NAME}")
echo "Bog'langan: ${LOOP_DEV}"

mkfs.vfat -F32 "${LOOP_DEV}p1"
mkfs.ext4 -L "ROOT" "${LOOP_DEV}p2"
mkfs.ext4 -L "DATA" "${LOOP_DEV}p3"

echo "=== 4. Root fayl tizimini o'rnatish (debootstrap Ubuntu 22.04 LTS) ==="
mkdir -p "${MOUNT_DIR}"
mount "${LOOP_DEV}p2" "${MOUNT_DIR}"
mkdir -p "${MOUNT_DIR}/boot/efi"
mkdir -p "${MOUNT_DIR}/data"
mount "${LOOP_DEV}p1" "${MOUNT_DIR}/boot/efi"
mount "${LOOP_DEV}p3" "${MOUNT_DIR}/data"

debootstrap --arch=amd64 jammy "${MOUNT_DIR}" http://archive.ubuntu.com/ubuntu/

echo "=== 5. Offline paketlar va muhitni sozlash ==="
cp -r /opt/driving_eval_system "${MOUNT_DIR}/opt/driving_eval_system"
cp /opt/driving_eval_system/systemd/autoeval.service "${MOUNT_DIR}/etc/systemd/system/"

chroot "${MOUNT_DIR}" /bin/bash << 'EOF'
apt-get update
apt-get install -y --no-install-recommends \
    linux-image-generic systemd xorg nodm openbox libgl1-mesa-glx alsa-utils
useradd -m -s /bin/bash autoeval
systemctl enable autoeval.service
systemctl set-default graphical.target
EOF

echo "=== 6. Tozalash va ajratish ==="
umount -R "${MOUNT_DIR}"
losetup -d "${LOOP_DEV}"

echo "=== Disk obrazi tayyor: ${IMAGE_NAME} ==="
