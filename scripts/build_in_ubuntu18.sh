#!/usr/bin/env bash
set -Eeo pipefail
# Android 5.1 envsetup.sh references optional unset shell variables (e.g. TOP).
# Bash nounset is incompatible with sourcing legacy envsetup.sh.
export DEBIAN_FRONTEND=noninteractive
export TZ=UTC
apt-get update
apt-get install -y --no-install-recommends \
  ca-certificates git curl python python2.7 python3 build-essential bc \
  bison flex gperf zip unzip rsync lzop pngcrush xsltproc \
  libxml2-utils libssl-dev libncurses5-dev lib32ncurses5-dev \
  gcc-multilib g++-multilib zlib1g-dev lib32z1-dev \
  openjdk-8-jdk libgl1-mesa-dev fontconfig
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"
mkdir -p /workspace/omni /workspace/bin
curl --fail -sSL https://storage.googleapis.com/git-repo-downloads/repo -o /workspace/bin/repo
chmod +x /workspace/bin/repo
export PATH="/workspace/bin:$PATH"
git config --global user.name "A51w CI"
git config --global user.email "a51w-ci@localhost"
cd /workspace/omni
repo init --depth=1 -u https://github.com/minimal-manifest-twrp/platform_manifest_twrp_omni.git -b twrp-5.1
repo sync -c --no-tags --no-clone-bundle -j4
mkdir -p device/oppo/a51w
cp -a /workspace/input/device/oppo/a51w/. device/oppo/a51w/
export ALLOW_MISSING_DEPENDENCIES=true
export LC_ALL=C
source build/envsetup.sh
lunch omni_a51w-eng
make -j4 recoveryimage
mkdir -p /workspace/input/dist-a51w
cp out/target/product/a51w/recovery.img /workspace/input/dist-a51w/recovery.img
python3 /workspace/input/scripts/validate_recovery.py /workspace/input/dist-a51w/recovery.img
echo A51W_TWRP_COMPILE_PASS
