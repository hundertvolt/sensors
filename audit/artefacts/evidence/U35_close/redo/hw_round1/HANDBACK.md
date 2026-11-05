# Round 1 bench hand-back

Rebuilt by `round1.py` after every step, last 2026-11-05 08:13 UTC. Each verdict is its step's newest run; after step 4a a passing pytest step reads NOT CLEAN (lower levels skipped).

| step | name | verdict | ResetReason after | started (UTC) | took | host load at end | FC/FS/NVM/pre |
|---|---|---|---|---|---|---|---|
| 1 | evidence | rc=1 |  | 2026-11-05 07:52:48 | 0h00 | 0.28 | 0/0/0/0 |
| 2 | host_env | rc=0 |  | 2026-11-05 07:56:11 | 0h14 | 4.17 | 0/0/0/0 |
| 4a | lower_levels | not run |  |  |  |  | 0/0/0/0 |
| 3g | gc_control_image | not run |  |  |  |  | 1/0/0/0 |
| 4g | flash_tier_gc_control | not run |  |  |  |  | 0/0/1/136 |
| 5g | bench_tier_gc_control | not run |  |  |  |  | 0/0/0/66 |
| 3 | final_image | not run |  |  |  |  | 1/0/0/0 |
| 4b | flash_tier | not run |  |  |  |  | 0/0/0/136 |
| 5 | bench_tier | not run |  |  |  |  | 0/0/0/66 |
| 9 | crc16_hazards | not run |  |  |  |  | 0/0/0/0 |
| 10a | soak_short | not run |  |  |  |  | 0/0/0/8 |
| 10m | soak_mid | not run |  |  |  |  | 0/0/0/8 |
| 11 | fram_8mhz | not run |  |  |  |  | 0/0/0/0 |
| 12a | boot_stretch | not run |  |  |  |  | 0/0/0/0 |
| 12b | ring_peak | not run |  |  |  |  | 0/0/0/0 |
| 12c | dns_idle_poll | not run |  |  |  |  | 0/0/0/0 |
| 12d | reset_errors_budget | not run |  |  |  |  | 0/0/0/0 |
| 12e | general_call_per_chip | not run |  |  |  |  | 0/0/0/0 |
| 12f | held_sda_resets | not run |  |  |  |  | 0/0/0/0 |
| 16b | bmp3xx_probe | not run |  |  |  |  | 0/0/0/0 |
| 13 | country_scan | not run |  |  |  |  | 0/0/0/0 |
| 10c | soak_long_clock_stretch | not run |  |  |  |  | 0/0/0/0 |
| 10d | soak_long_core_headroom | not run |  |  |  |  | 0/0/0/0 |
| 10e | soak_long_bus_triggers | not run |  |  |  |  | 0/0/0/0 |
| 10f | soak_long_hammer | not run |  |  |  |  | 0/0/0/0 |
| 10g | soak_long_http_S4 | not run |  |  |  |  | 0/0/0/0 |
| 10h | soak_long_frc_baseline | not run |  |  |  |  | 0/0/0/0 |
| 7f | gated_flash | not run |  |  |  |  | 0/72/6/0 |
| 7b | gated_bench | not run |  |  |  |  | 0/50/7/0 |
| 8f | flash_cycles_flash | not run |  |  |  |  | 1/0/0/0 |
| 8b | flash_cycles_bench | not run |  |  |  |  | 4/0/0/0 |
| 10b | hotspot_case_b | not run |  |  |  |  | 0/4/0/2 |
| 15 | rollover | not run |  |  |  |  | 2/0/0/0 |

Wear started (the sheet's maxima per started step): FC 0 of 9, FS owned 0 of 126, NVM 0 of 14, prerequisite writes 0 of 422.

## Long runs summed (October's aggregate)

```

```

## Logs

### 2 host_env

<!-- step 2 -->
```
== step 2 start 2026-11-05 07:56:11 1793865371 load 0.03 0.08 0.09
Toolchain directory: /home/nico/pico-toolchain
MicroPython ref: v1.29.0
Board: RPI_PICO_W

== Installing/checking system packages
$ sudo --preserve-env=DEBIAN_FRONTEND apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 update
Hit:1 http://deb.debian.org/debian trixie InRelease
Hit:2 http://deb.debian.org/debian trixie-updates InRelease
Hit:3 http://deb.debian.org/debian-security trixie-security InRelease
Get:4 http://archive.raspberrypi.com/debian trixie InRelease [54.9 kB]
Get:5 http://archive.raspberrypi.com/debian trixie/main arm64 Packages [493 kB]
Fetched 548 kB in 0s (2070 kB/s)
Reading package lists...
$ sudo --preserve-env=DEBIAN_FRONTEND apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 install --download-only -y --no-install-recommends build-essential cmake pkg-config git libusb-1.0-0-dev gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib libffi-dev libcap2-bin
Reading package lists...
Building dependency tree...
Reading state information...
build-essential is already the newest version (12.12).
cmake is already the newest version (3.31.6-2).
pkg-config is already the newest version (1.8.1-4).
git is already the newest version (1:2.47.3-0+deb13u1).
libusb-1.0-0-dev is already the newest version (2:1.0.28-1).
gcc-arm-none-eabi is already the newest version (15:14.2.rel1-1).
libnewlib-arm-none-eabi is already the newest version (4.5.0.20241231-1).
libstdc++-arm-none-eabi-newlib is already the newest version (15:14.2.rel1-1+29).
libffi-dev is already the newest version (3.4.8-2).
libcap2-bin is already the newest version (1:2.75-10+deb13u1+b3).
The following packages were automatically installed and are no longer required:
  chromium-sandbox libfuse2t64 libqt5x11extras5
Use 'sudo apt autoremove' to remove them.
0 upgraded, 0 newly installed, 0 to remove and 45 not upgraded.
$ sudo --preserve-env=DEBIAN_FRONTEND apt-get -o Acquire::Retries=2 -o Acquire::http::Timeout=30 -o Acquire::https::Timeout=30 install -y --no-install-recommends build-essential cmake pkg-config git libusb-1.0-0-dev gcc-arm-none-eabi libnewlib-arm-none-eabi libstdc++-arm-none-eabi-newlib libffi-dev libcap2-bin
Reading package lists...
Building dependency tree...
Reading state information...
build-essential is already the newest version (12.12).
cmake is already the newest version (3.31.6-2).
pkg-config is already the newest version (1.8.1-4).
git is already the newest version (1:2.47.3-0+deb13u1).
libusb-1.0-0-dev is already the newest version (2:1.0.28-1).
gcc-arm-none-eabi is already the newest version (15:14.2.rel1-1).
libnewlib-arm-none-eabi is already the newest version (4.5.0.20241231-1).
libstdc++-arm-none-eabi-newlib is already the newest version (15:14.2.rel1-1+29).
libffi-dev is already the newest version (3.4.8-2).
libcap2-bin is already the newest version (1:2.75-10+deb13u1+b3).
The following packages were automatically installed and are no longer required:
  chromium-sandbox libfuse2t64 libqt5x11extras5
Use 'sudo apt autoremove' to remove them.
0 upgraded, 0 newly installed, 0 to remove and 45 not upgraded.

== Preparing MicroPython at v1.29.0
$ git rev-parse --verify HEAD   (cwd=/home/nico/pico-toolchain/micropython)
0fd6c573ea815774668bbb16b8e197c8822368b2

== Updating existing clone at /home/nico/pico-toolchain/micropython
$ git fetch --quiet --tags --force origin   (cwd=/home/nico/pico-toolchain/micropython)
$ git checkout --quiet v1.29.0   (cwd=/home/nico/pico-toolchain/micropython)
$ git ls-tree v1.29.0 lib/pico-sdk   (cwd=/home/nico/pico-toolchain/micropython)
160000 commit 98a542c1a62fb549ffb5d66a3e5892b06276b670	lib/pico-sdk

== MicroPython v1.29.0 pins pico-sdk commit 98a542c1a62fb549ffb5d66a3e5892b06276b670
$ git rev-parse --verify HEAD   (cwd=/home/nico/pico-toolchain/pico-sdk)
98a542c1a62fb549ffb5d66a3e5892b06276b670

== Updating existing clone at /home/nico/pico-toolchain/pico-sdk
$ git fetch --quiet --tags --force origin   (cwd=/home/nico/pico-toolchain/pico-sdk)
$ git checkout --quiet 98a542c1a62fb549ffb5d66a3e5892b06276b670   (cwd=/home/nico/pico-toolchain/pico-sdk)
$ git submodule update --init lib/mbedtls   (cwd=/home/nico/pico-toolchain/pico-sdk)
$ git describe --tags 98a542c1a62fb549ffb5d66a3e5892b06276b670   (cwd=/home/nico/pico-toolchain/pico-sdk)
2.3.0
$ git ls-remote --tags https://github.com/raspberrypi/picotool.git
a49dc0b3c211b8b73d4ec7967cf134710ce104c2	refs/tags/1.0.1
55fd880c3dc029b961fc1a0967a6cfdc0af02721	refs/tags/1.1.0
27be747231c525deec8cb6538e8db12391512249	refs/tags/1.1.1
f6fe6b7c321a2def8950d2a440335dfba19e2eab	refs/tags/1.1.2
8a9af99ab10b20b1c6afb30cd9384e562a6647f9	refs/tags/2.0.0
df21059f7ca6f1babc7f1f3b92122cacffc85951	refs/tags/2.1.0
de8ae5ac334e1126993f72a5c67949712fd1e1a4	refs/tags/2.1.1
a7eb3988f0645239185fadb4e25d8279478c2dbb	refs/tags/2.2.0
25aa087b2c517b4901874a99536e869d4d27b678	refs/tags/2.2.0-a4
6f6458d792b93685a11423b244a585eaa99eafcf	refs/tags/2.3.0
2041936441b48a3cc53ae3da9e805229fe8f4e18	refs/tags/2.3.1

== Matching picotool tag: 2.3.1
$ git rev-parse --verify HEAD   (cwd=/home/nico/pico-toolchain/picotool)
2041936441b48a3cc53ae3da9e805229fe8f4e18

== Updating existing clone at /home/nico/pico-toolchain/picotool
$ git fetch --quiet --tags --force origin   (cwd=/home/nico/pico-toolchain/picotool)
$ git checkout --quiet 2.3.1   (cwd=/home/nico/pico-toolchain/picotool)

== Building and installing picotool (against pico-sdk at /home/nico/pico-toolchain/pico-sdk)
$ cmake .. -DPICO_SDK_PATH=/home/nico/pico-toolchain/pico-sdk -DCMAKE_INSTALL_PREFIX=/usr/local   (cwd=/home/nico/pico-toolchain/picotool/build)
-- The C compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Using the single-header code from /home/nico/pico-toolchain/picotool/lib/nlohmann_json/single_include/
-- Found PkgConfig: /usr/bin/pkg-config (found version "1.8.1")
-- Checking for module 'libusb-1.0'
--   Found libusb-1.0, version 1.0.28
-- Found LIBUSB: /usr/lib/aarch64-linux-gnu/libusb-1.0.so
-- Configuring done (2.9s)
-- Generating done (0.1s)
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build
$ make -j4   (cwd=/home/nico/pico-toolchain/picotool/build)
[  1%] Creating directories for 'enc_bootloader'
[  3%] Creating directories for 'xip_ram_perms'
[  3%] Creating directories for 'enc_bootloader_mbedtls'
[  3%] Creating directories for 'flash_id'
[  4%] No download step for 'enc_bootloader'
[  4%] No download step for 'enc_bootloader_mbedtls'
[  6%] No download step for 'flash_id'
[  6%] No download step for 'xip_ram_perms'
[  8%] No update step for 'enc_bootloader_mbedtls'
[  8%] No update step for 'enc_bootloader'
[ 10%] No update step for 'flash_id'
[ 10%] No update step for 'xip_ram_perms'
[ 11%] No patch step for 'enc_bootloader'
[ 11%] No patch step for 'enc_bootloader_mbedtls'
[ 12%] No patch step for 'flash_id'
[ 13%] No patch step for 'xip_ram_perms'
[ 15%] Performing configure step for 'enc_bootloader'
[ 15%] Performing configure step for 'enc_bootloader_mbedtls'
[ 15%] Performing configure step for 'flash_id'
[ 16%] Performing configure step for 'xip_ram_perms'
-- The C compiler identification is GNU 14.2.0
-- The C compiler identification is GNU 14.2.0
-- The C compiler identification is GNU 14.2.0
-- The C compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- The CXX compiler identification is GNU 14.2.0
-- The ASM compiler identification is GNU
-- The ASM compiler identification is GNU
-- The ASM compiler identification is GNU
-- Found assembler: /usr/bin/cc
-- Found assembler: /usr/bin/cc
-- Found assembler: /usr/bin/cc
-- The ASM compiler identification is GNU
-- Found assembler: /usr/bin/cc
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Detecting C compiler ABI info - done
-- Detecting C compiler ABI info - done
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting C compile features - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Check for working C compiler: /usr/bin/cc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Detecting CXX compiler ABI info - done
-- Detecting CXX compiler ABI info - done
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
Using precompiled enc_bootloader.elf
Using precompiled flash_id.bin
-- Configuring done (1.7s)
-- Configuring done (1.7s)
-- Generating done (0.0s)
-- Generating done (0.0s)
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build/enc_bootloader_mbedtls
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build/picoboot_flash_id
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
Using precompiled enc_bootloader.elf
-- Detecting CXX compile features - done
-- Configuring done (1.7s)
-- Generating done (0.0s)
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build/enc_bootloader
Using precompiled xip_ram_perms.elf
-- Configuring done (1.7s)
-- Generating done (0.0s)
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build/xip_ram_perms
[ 17%] Performing build step for 'flash_id'
[ 18%] Performing build step for 'enc_bootloader_mbedtls'
[ 18%] Performing build step for 'enc_bootloader'
[ 18%] Performing build step for 'xip_ram_perms'
[ 19%] No install step for 'flash_id'
[ 20%] No install step for 'enc_bootloader_mbedtls'
[ 20%] No install step for 'enc_bootloader'
[ 20%] No install step for 'xip_ram_perms'
[ 21%] Completed 'flash_id'
[ 21%] Completed 'enc_bootloader_mbedtls'
[ 23%] Completed 'xip_ram_perms'
[ 23%] Completed 'enc_bootloader'
[ 23%] Built target enc_bootloader_mbedtls
[ 23%] Built target flash_id
[ 23%] Built target xip_ram_perms
[ 24%] Creating directories for 'otp_header_parser'
[ 24%] Built target enc_bootloader
[ 25%] Building CXX object errors/CMakeFiles/errors.dir/errors.cpp.o
[ 26%] Configuring rp2350_a2_rom_end.h
[ 27%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/aes.c.o
[ 28%] No download step for 'otp_header_parser'
[ 28%] Configuring rp2350_a3_rom_end.h
[ 29%] Configuring rp2350_a4_rom_end.h
[ 29%] No update step for 'otp_header_parser'
[ 29%] Built target unreadable_rom_data
[ 30%] No patch step for 'otp_header_parser'
[ 30%] Configuring enc_bootloader_elf.h
[ 31%] Performing configure step for 'otp_header_parser'
-- The CXX compiler identification is GNU 14.2.0
-- Detecting CXX compiler ABI info
[ 32%] Configuring enc_bootloader_mbedtls_elf.h
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Using the single-header code from /home/nico/pico-toolchain/picotool/lib/nlohmann_json/single_include/
-- Configuring done (0.9s)
-- Generating done (0.0s)
-- Build files have been written to: /home/nico/pico-toolchain/picotool/build/otp_header_parser
[ 32%] Performing build step for 'otp_header_parser'
[ 32%] Linking CXX static library liberrors.a
[ 50%] Building CXX object CMakeFiles/otp_header_parse.dir/otp_header_parse.cpp.o
[ 32%] Built target errors
[ 33%] Configuring xip_ram_perms_elf.h
[ 33%] Built target embedded_data_no_libusb
[ 34%] Configuring flash_id_bin.h
[ 35%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/aesni.c.o
[ 35%] Built target embedded_data
[ 35%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/aria.c.o
[ 35%] Building CXX object model/CMakeFiles/model.dir/model.cpp.o
[ 36%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/asn1parse.c.o
[ 37%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/asn1write.c.o
[ 37%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/base64.c.o
[ 38%] Linking CXX static library libmodel.a
[ 39%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/bignum.c.o
[ 39%] Built target model
[ 39%] Building CXX object elf/CMakeFiles/elf.dir/elf_file.cpp.o
[ 40%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/camellia.c.o
[ 40%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ccm.c.o
[ 41%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/chacha20.c.o
[ 42%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/chachapoly.c.o
[ 42%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/cipher.c.o
[ 43%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/cipher_wrap.c.o
[ 44%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/cmac.c.o
[ 44%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/constant_time.c.o
[ 45%] Linking CXX static library libelf.a
[ 45%] Built target elf
[ 46%] Building CXX object elf2uf2/CMakeFiles/elf2uf2.dir/elf2uf2.cpp.o
[ 47%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ctr_drbg.c.o
[ 48%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/des.c.o
[ 49%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/dhm.c.o
[ 49%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ecdh.c.o
[ 50%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ecdsa.c.o
[ 51%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ecjpake.c.o
[ 51%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ecp.c.o
[ 52%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ecp_curves.c.o
[100%] Linking CXX executable otp_header_parse
[100%] Built target otp_header_parse
[ 52%] No install step for 'otp_header_parser'
[ 53%] Completed 'otp_header_parser'
[ 53%] Built target otp_header_parser
[ 54%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/entropy.c.o
[ 54%] Generating /home/nico/pico-toolchain/picotool/build/rp2350_otp_contents.json
[ 54%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/entropy_poll.c.o
[ 54%] Linking CXX static library libelf2uf2.a
[ 54%] Built target elf2uf2
[ 55%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/error.c.o
[ 56%] Configuring rp2350.json.h
[ 57%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/gcm.c.o
[ 57%] Built target generate_otp_header
[ 57%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/hkdf.c.o
[ 58%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/hmac_drbg.c.o
[ 59%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/md.c.o
[ 59%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/md5.c.o
[ 60%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/memory_buffer_alloc.c.o
[ 61%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/mps_reader.c.o
[ 62%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/mps_trace.c.o
[ 62%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/nist_kw.c.o
[ 63%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/oid.c.o
[ 64%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/padlock.c.o
[ 64%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pem.c.o
[ 65%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pk.c.o
[ 66%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pk_wrap.c.o
[ 66%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pkcs12.c.o
[ 67%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pkcs5.c.o
[ 68%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pkparse.c.o
[ 68%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pkwrite.c.o
[ 69%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/platform.c.o
[ 70%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/platform_util.c.o
[ 70%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/poly1305.c.o
[ 71%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto.c.o
[ 72%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_aead.c.o
[ 72%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_cipher.c.o
[ 73%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_client.c.o
[ 74%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_ecp.c.o
[ 75%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_hash.c.o
[ 75%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_mac.c.o
[ 76%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_rsa.c.o
[ 77%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_se.c.o
[ 77%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_slot_management.c.o
[ 78%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_crypto_storage.c.o
[ 79%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/psa_its_file.c.o
[ 79%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/ripemd160.c.o
[ 80%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/rsa.c.o
[ 81%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/sha1.c.o
[ 81%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/sha256.c.o
[ 82%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/sha512.c.o
[ 83%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/threading.c.o
[ 83%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/timing.c.o
[ 84%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/version.c.o
[ 85%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/version_features.c.o
[ 85%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/bignum_core.c.o
[ 86%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/rsa_alt_helpers.c.o
[ 87%] Building C object lib/CMakeFiles/mbedtls.dir/home/nico/pico-toolchain/pico-sdk/lib/mbedtls/library/pk_ecc.c.o
[ 88%] Linking C static library libmbedtls.a
[ 88%] Built target mbedtls
[ 89%] Building CXX object bintool/CMakeFiles/bintool.dir/bintool.cpp.o
[ 89%] Building C object bintool/CMakeFiles/bintool.dir/mbedtls_wrapper.c.o
[ 90%] Linking CXX static library libbintool.a
[ 90%] Built target bintool
[ 92%] Building CXX object CMakeFiles/picotool.dir/get_enc_bootloader.cpp.o
[ 92%] Building CXX object CMakeFiles/picotool.dir/data_locs.cpp.o
[ 92%] Building CXX object CMakeFiles/picotool.dir/otp.cpp.o
[ 93%] Building CXX object CMakeFiles/picotool.dir/main.cpp.o
[ 94%] Building CXX object CMakeFiles/picotool.dir/get_xip_ram_perms.cpp.o
[ 94%] Building C object CMakeFiles/picotool.dir/lib/whereami/whereami.c.o
[ 95%] Building CXX object CMakeFiles/picotool.dir/lib/whereami/whereami++.cpp.o
[ 96%] Building CXX object CMakeFiles/picotool.dir/picoboot_connection/picoboot_connection_cxx.cpp.o
[ 97%] Building C object CMakeFiles/picotool.dir/picoboot_connection/picoboot_connection.c.o
[ 97%] Building C object CMakeFiles/picotool.dir/lib/oofatfs/src/ff.c.o
[ 98%] Building C object CMakeFiles/picotool.dir/lib/oofatfs/src/ffunicode.c.o
[ 99%] Building C object CMakeFiles/picotool.dir/lib/littlefs/lfs.c.o
[ 99%] Building C object CMakeFiles/picotool.dir/lib/littlefs/lfs_util.c.o
[100%] Linking CXX executable picotool
[100%] Built target picotool
$ sudo make install   (cwd=/home/nico/pico-toolchain/picotool/build)
[  0%] Performing build step for 'enc_bootloader'
[  0%] No install step for 'enc_bootloader'
[  1%] Completed 'enc_bootloader'
[  6%] Built target enc_bootloader
[  7%] Performing build step for 'enc_bootloader_mbedtls'
[  8%] No install step for 'enc_bootloader_mbedtls'
[  8%] Completed 'enc_bootloader_mbedtls'
[ 11%] Built target enc_bootloader_mbedtls
[ 11%] Performing build step for 'xip_ram_perms'
[ 11%] No install step for 'xip_ram_perms'
[ 12%] Completed 'xip_ram_perms'
[ 17%] Built target xip_ram_perms
[ 18%] Performing build step for 'flash_id'
[ 19%] No install step for 'flash_id'
[ 20%] Completed 'flash_id'
[ 23%] Built target flash_id
[ 23%] Performing build step for 'otp_header_parser'
[100%] Built target otp_header_parse
[ 23%] No install step for 'otp_header_parser'
[ 24%] Completed 'otp_header_parser'
[ 28%] Built target otp_header_parser
[ 29%] Built target errors
[ 31%] Built target unreadable_rom_data
[ 32%] Built target model
[ 33%] Built target elf
[ 83%] Built target mbedtls
[ 85%] Built target bintool
[ 86%] Built target generate_otp_header
[ 87%] Built target embedded_data_no_libusb
[ 89%] Built target embedded_data
[ 90%] Built target elf2uf2
[100%] Built target picotool
Install the project...
-- Install configuration: "Release"
-- Installing: /usr/local/bin/picotool
-- Installing: /usr/local/lib/cmake/picotool/picotoolTargets.cmake
-- Installing: /usr/local/lib/cmake/picotool/picotoolTargets-release.cmake
-- Installing: /usr/local/lib/cmake/picotool/picotoolConfig.cmake
-- Installing: /usr/local/lib/cmake/picotool/picotoolConfigVersion.cmake
-- Installing: /usr/local/share/picotool/enc_bootloader.elf
-- Installing: /usr/local/share/picotool/enc_bootloader_mbedtls.elf
-- Installing: /usr/local/share/picotool/rp2350_otp_contents.json
-- Installing: /usr/local/share/picotool/xip_ram_perms.elf
$ /usr/local/bin/picotool version
picotool v2.3.1 (Linux, GNU-14.2.0, Release)
Installed: picotool v2.3.1 (Linux, GNU-14.2.0, Release)

== Fetching submodules needed for BOARD=RPI_PICO_W
$ make BOARD=RPI_PICO_W submodules   (cwd=/home/nico/pico-toolchain/micropython/ports/rp2)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
make[1]: Entering directory '/home/nico/pico-toolchain/micropython/ports/rp2'
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
Updating submodules: lib/pico-sdk
Synchronizing submodule url for 'lib/pico-sdk'
make[1]: Leaving directory '/home/nico/pico-toolchain/micropython/ports/rp2'
PICO_SDK_PATH is /home/nico/pico-toolchain/micropython/lib/pico-sdk
Target board (PICO_BOARD) is 'pico_w'.
Using board configuration from /home/nico/pico-toolchain/micropython/lib/pico-sdk/src/boards/include/boards/pico_w.h
Defaulting platform (PICO_PLATFORM) to 'rp2040' based on PICO_BOARD setting.
Defaulting compiler (PICO_COMPILER) to 'pico_arm_cortex_m0plus_gcc' since not specified or detected.
Configuring toolchain based on PICO_COMPILER 'pico_arm_cortex_m0plus_gcc'
Defaulting PICO_GCC_TRIPLE to 'arm-none-eabi'
-- The C compiler identification is GNU 14.2.1
-- The CXX compiler identification is GNU 14.2.1
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/arm-none-eabi-gcc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/arm-none-eabi-g++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- The ASM compiler identification is GNU
-- Found assembler: /usr/bin/arm-none-eabi-gcc
Build type is MinSizeRel
-- Found Python3: /usr/bin/python3 (found version "3.13.5") found components: Interpreter
-- Detected native TLS (__aeabi_read_tp)
TinyUSB available at /home/nico/pico-toolchain/micropython/lib/tinyusb/hw/bsp/rp2040; enabling build support for USB.
BTstack available at /home/nico/pico-toolchain/micropython/lib/btstack
cyw43-driver available at /home/nico/pico-toolchain/micropython/lib/cyw43-driver
Pico W Bluetooth build support available.
lwIP available at /home/nico/pico-toolchain/micropython/lib/lwip
Pico W Wi-Fi build support available.
C library type is newlib
Found User C Module(s): 
Using picotool from /usr/local/bin/picotool
Updating submodules: lib/mbedtls lib/tinyusb lib/lwip lib/btstack lib/cyw43-driver lib/micropython-lib
Synchronizing submodule url for 'lib/btstack'
Synchronizing submodule url for 'lib/cyw43-driver'
Synchronizing submodule url for 'lib/lwip'
Synchronizing submodule url for 'lib/mbedtls'
Synchronizing submodule url for 'lib/micropython-lib'
Synchronizing submodule url for 'lib/tinyusb'
-- Configuring done (4.5s)
-- Generating done (0.6s)
-- Build files have been written to: /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W/submodules

== Fetching submodules needed for the Unix port
$ make submodules MICROPY_PY_LWIP=1   (cwd=/home/nico/pico-toolchain/micropython/ports/unix)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
Updating submodules: lib/mbedtls lib/lwip lib/berkeley-db-1.xx lib/micropython-lib
Synchronizing submodule url for 'lib/berkeley-db-1.xx'
Synchronizing submodule url for 'lib/lwip'
Synchronizing submodule url for 'lib/mbedtls'
Synchronizing submodule url for 'lib/micropython-lib'

== Building mpy-cross
$ make -j4   (cwd=/home/nico/pico-toolchain/micropython/mpy-cross)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
GEN build/genhdr/mpversion.h
CC ../py/modsys.c
CC main.c
LINK build/mpy-cross
   text	   data	    bss	    dec	    hex	filename
 504571	  19705	    840	 525116	  8033c	build/mpy-cross
$ /home/nico/pico-toolchain/micropython/mpy-cross/build/mpy-cross --version
MicroPython v1.29.0 on 2026-11-05; mpy-cross emitting mpy v6.3
Built: MicroPython v1.29.0 on 2026-11-05; mpy-cross emitting mpy v6.3

== Cross-compiling the verification test file to prove mpy-cross works standalone
$ /home/nico/pico-toolchain/micropython/mpy-cross/build/mpy-cross /tmp/tmpf2_60_ji/frozen_module/frozen_verify_test.py
Produced frozen_verify_test.mpy (347 bytes)

== Building the MicroPython Unix port (settrace-free, the test rig, with the frozen verification module)
$ make -j4 VARIANT=standard VARIANT_DIR=/home/nico/pico-toolchain/build_overrides/unix_kbd_intr_variant FROZEN_MANIFEST=/tmp/tmpf2_60_ji/manifest_unix.py   (cwd=/home/nico/pico-toolchain/micropython/ports/unix)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
mkdir -p build-standard/genhdr
mkdir -p build-standard/
mkdir -p build-standard/extmod/
mkdir -p build-standard/extmod/mbedtls/
mkdir -p build-standard/lib/berkeley-db-1.xx/btree/
mkdir -p build-standard/lib/berkeley-db-1.xx/mpool/
mkdir -p build-standard/lib/littlefs/
mkdir -p build-standard/lib/mbedtls/library/
mkdir -p build-standard/lib/mbedtls_errors/
mkdir -p build-standard/lib/oofatfs/
mkdir -p build-standard/py/
mkdir -p build-standard/shared/libc/
mkdir -p build-standard/shared/readline/
mkdir -p build-standard/shared/runtime/
mkdir -p build-standard/shared/timeutils/
GEN build-standard/genhdr/mpversion.h
GEN build-standard/genhdr/qstr.i.last
GEN build-standard/genhdr/qstr.split
GEN build-standard/genhdr/moduledefs.split
GEN build-standard/genhdr/root_pointers.split
GEN build-standard/genhdr/compressed.split
GEN build-standard/genhdr/root_pointers.collected
GEN build-standard/genhdr/moduledefs.collected
GEN build-standard/genhdr/compressed.collected
GEN build-standard/genhdr/qstrdefs.collected.h
Root pointer registrations updated
Module registrations updated
Compressed data updated
GEN build-standard/genhdr/root_pointers.h
GEN build-standard/genhdr/moduledefs.h
GEN build-standard/genhdr/compressed.data.h
QSTR updated
GEN build-standard/genhdr/qstrdefs.generated.h
CC ../../py/mpstate.c
CC ../../py/nlr.c
CC ../../py/nlrx86.c
CC ../../py/nlrx64.c
CC ../../py/nlrthumb.c
CC ../../py/nlraarch64.c
CC ../../py/nlrmips.c
CC ../../py/nlrpowerpc.c
CC ../../py/nlrxtensa.c
CC ../../py/nlrrv32.c
CC ../../py/nlrrv64.c
CC ../../py/nlrloong64.c
CC ../../py/nlrsetjmp.c
CC ../../py/malloc.c
CC ../../py/gc.c
CC ../../py/pystack.c
CC ../../py/qstr.c
CC ../../py/vstr.c
CC ../../py/mpprint.c
CC ../../py/unicode.c
CC ../../py/mpz.c
CC ../../py/reader.c
CC ../../py/lexer.c
CC ../../py/parse.c
CC ../../py/scope.c
CC ../../py/compile.c
CC ../../py/emitcommon.c
CC ../../py/emitbc.c
CC ../../py/asmbase.c
CC ../../py/asmx64.c
CC ../../py/emitnx64.c
CC ../../py/asmx86.c
CC ../../py/emitnx86.c
CC ../../py/asmthumb.c
CC ../../py/emitnthumb.c
CC ../../py/emitinlinethumb.c
CC ../../py/asmarm.c
CC ../../py/emitnarm.c
CC ../../py/asmxtensa.c
CC ../../py/emitnxtensa.c
CC ../../py/emitinlinextensa.c
CC ../../py/emitnxtensawin.c
CC ../../py/asmrv32.c
CC ../../py/emitnrv32.c
CC ../../py/emitinlinerv32.c
CC ../../py/emitndebug.c
CC ../../py/formatfloat.c
CC ../../py/parsenumbase.c
CC ../../py/parsenum.c
CC ../../py/emitglue.c
CC ../../py/persistentcode.c
CC ../../py/runtime.c
CC ../../py/runtime_utils.c
CC ../../py/scheduler.c
CC ../../py/nativeglue.c
CC ../../py/pairheap.c
CC ../../py/ringbuf.c
CC ../../py/cstack.c
CC ../../py/stackctrl.c
CC ../../py/argcheck.c
CC ../../py/warning.c
CC ../../py/profile.c
CC ../../py/map.c
CC ../../py/obj.c
CC ../../py/objarray.c
CC ../../py/objattrtuple.c
CC ../../py/objbool.c
CC ../../py/objboundmeth.c
CC ../../py/objcell.c
CC ../../py/objclosure.c
CC ../../py/objcode.c
CC ../../py/objcomplex.c
CC ../../py/objdeque.c
CC ../../py/objdict.c
CC ../../py/objenumerate.c
CC ../../py/objexcept.c
CC ../../py/objfilter.c
CC ../../py/objfloat.c
CC ../../py/objfun.c
CC ../../py/objgenerator.c
CC ../../py/objgetitemiter.c
CC ../../py/objint.c
CC ../../py/objint_longlong.c
CC ../../py/objint_mpz.c
CC ../../py/objlist.c
CC ../../py/objmap.c
CC ../../py/objmodule.c
CC ../../py/objobject.c
CC ../../py/objpolyiter.c
CC ../../py/objproperty.c
CC ../../py/objnone.c
CC ../../py/objnamedtuple.c
CC ../../py/objrange.c
CC ../../py/objreversed.c
CC ../../py/objringio.c
CC ../../py/objset.c
CC ../../py/objsingleton.c
CC ../../py/objslice.c
CC ../../py/objstr.c
CC ../../py/objstrunicode.c
CC ../../py/objstringio.c
CC ../../py/objtemplate.c
CC ../../py/objtuple.c
CC ../../py/objtype.c
CC ../../py/objzip.c
CC ../../py/opmethods.c
CC ../../py/sequence.c
CC ../../py/stream.c
CC ../../py/binary.c
CC ../../py/builtinimport.c
CC ../../py/builtinevex.c
CC ../../py/builtinhelp.c
CC ../../py/modarray.c
CC ../../py/modbuiltins.c
CC ../../py/modcollections.c
CC ../../py/modgc.c
CC ../../py/modio.c
CC ../../py/modmath.c
CC ../../py/modcmath.c
CC ../../py/modmicropython.c
CC ../../py/modstring.c
CC ../../py/modstruct.c
CC ../../py/modsys.c
CC ../../py/moderrno.c
CC ../../py/modthread.c
CC ../../py/modweakref.c
CC ../../py/vm.c
CC ../../py/bc.c
CC ../../py/showbc.c
CC ../../py/repl.c
CC ../../py/smallint.c
CC ../../py/frozenmod.c
CC ../../extmod/machine_adc.c
CC ../../extmod/machine_adc_block.c
CC ../../extmod/machine_bitstream.c
CC ../../extmod/machine_can.c
CC ../../extmod/machine_i2c.c
CC ../../extmod/machine_i2c_target.c
CC ../../extmod/machine_i2s.c
CC ../../extmod/machine_mem.c
CC ../../extmod/machine_pinbase.c
CC ../../extmod/machine_pulse.c
MPY argparse.py
MPY requests/__init__.py
MPY mip/__init__.py
MPY mip/__main__.py
MPY ssl.py
MPY frozen_verify_test.py
GEN build-standard/frozen_content.c
CC ../../extmod/machine_pwm.c
CC ../../extmod/machine_signal.c
CC ../../extmod/machine_spi.c
CC ../../extmod/machine_timer.c
CC ../../extmod/machine_uart.c
CC ../../extmod/machine_usb_device.c
CC ../../extmod/machine_wdt.c
CC ../../extmod/modasyncio.c
CC ../../extmod/modbinascii.c
CC ../../extmod/modbluetooth.c
CC ../../extmod/modbtree.c
CC ../../extmod/modcryptolib.c
CC ../../extmod/moddeflate.c
CC ../../extmod/modframebuf.c
CC ../../extmod/modhashlib.c
CC ../../extmod/modheapq.c
CC ../../extmod/modjson.c
CC ../../extmod/modlwip.c
CC ../../extmod/modmachine.c
CC ../../extmod/modmarshal.c
CC ../../extmod/modnetwork.c
CC ../../extmod/modonewire.c
CC ../../extmod/modopenamp.c
CC ../../extmod/modopenamp_remoteproc.c
CC ../../extmod/modopenamp_remoteproc_store.c
CC ../../extmod/modos.c
CC ../../extmod/modplatform.c
CC ../../extmod/modrandom.c
CC ../../extmod/modre.c
CC ../../extmod/modselect.c
CC ../../extmod/modsocket.c
CC ../../extmod/modtls_axtls.c
CC ../../extmod/modtls_mbedtls.c
CC ../../extmod/mbedtls/mbedtls_alt.c
CC ../../extmod/modtime.c
CC ../../extmod/moductypes.c
CC ../../extmod/modvfs.c
CC ../../extmod/modwebrepl.c
CC ../../extmod/modwebsocket.c
CC ../../extmod/network_cyw43.c
CC ../../extmod/network_esp_hosted.c
CC ../../extmod/network_lwip.c
CC ../../extmod/network_ninaw10.c
CC ../../extmod/network_ppp_lwip.c
CC ../../extmod/network_usbd_ncm.c
CC ../../extmod/network_wiznet5k.c
CC ../../extmod/os_dupterm.c
CC ../../extmod/vfs.c
CC ../../extmod/vfs_blockdev.c
CC ../../extmod/vfs_fat.c
CC ../../extmod/vfs_fat_diskio.c
CC ../../extmod/vfs_fat_file.c
CC ../../extmod/vfs_lfs.c
CC ../../extmod/vfs_rom.c
CC ../../extmod/vfs_rom_file.c
CC ../../extmod/vfs_posix.c
CC ../../extmod/vfs_posix_file.c
CC ../../extmod/vfs_reader.c
CC ../../extmod/virtpin.c
CC ../../shared/libc/abort_.c
CC ../../shared/libc/printf.c
CC ../../lib/oofatfs/ff.c
CC ../../lib/oofatfs/ffunicode.c
CC ../../lib/littlefs/lfs1.c
CC ../../lib/littlefs/lfs1_util.c
CC ../../lib/littlefs/lfs2.c
CC ../../lib/littlefs/lfs2_util.c
CC ../../lib/mbedtls_errors/mp_mbedtls_errors.c
CC ../../lib/mbedtls/library/aes.c
CC ../../lib/mbedtls/library/aesni.c
CC ../../lib/mbedtls/library/asn1parse.c
CC ../../lib/mbedtls/library/asn1write.c
CC ../../lib/mbedtls/library/base64.c
CC ../../lib/mbedtls/library/bignum_core.c
CC ../../lib/mbedtls/library/bignum_mod.c
CC ../../lib/mbedtls/library/bignum_mod_raw.c
CC ../../lib/mbedtls/library/bignum.c
CC ../../lib/mbedtls/library/camellia.c
CC ../../lib/mbedtls/library/ccm.c
CC ../../lib/mbedtls/library/chacha20.c
CC ../../lib/mbedtls/library/chachapoly.c
CC ../../lib/mbedtls/library/cipher.c
CC ../../lib/mbedtls/library/cipher_wrap.c
CC ../../lib/mbedtls/library/nist_kw.c
CC ../../lib/mbedtls/library/aria.c
CC ../../lib/mbedtls/library/cmac.c
CC ../../lib/mbedtls/library/constant_time.c
CC ../../lib/mbedtls/library/mps_reader.c
CC ../../lib/mbedtls/library/mps_trace.c
CC ../../lib/mbedtls/library/ctr_drbg.c
CC ../../lib/mbedtls/library/debug.c
CC ../../lib/mbedtls/library/des.c
CC ../../lib/mbedtls/library/dhm.c
CC ../../lib/mbedtls/library/ecdh.c
CC ../../lib/mbedtls/library/ecdsa.c
CC ../../lib/mbedtls/library/ecjpake.c
CC ../../lib/mbedtls/library/ecp.c
CC ../../lib/mbedtls/library/ecp_curves.c
CC ../../lib/mbedtls/library/entropy.c
CC ../../lib/mbedtls/library/entropy_poll.c
CC ../../lib/mbedtls/library/gcm.c
CC ../../lib/mbedtls/library/hmac_drbg.c
CC ../../lib/mbedtls/library/md5.c
CC ../../lib/mbedtls/library/md.c
CC ../../lib/mbedtls/library/oid.c
CC ../../lib/mbedtls/library/padlock.c
CC ../../lib/mbedtls/library/pem.c
CC ../../lib/mbedtls/library/pk.c
CC ../../lib/mbedtls/library/pkcs12.c
CC ../../lib/mbedtls/library/pkcs5.c
CC ../../lib/mbedtls/library/pkparse.c
CC ../../lib/mbedtls/library/pk_ecc.c
CC ../../lib/mbedtls/library/pk_wrap.c
CC ../../lib/mbedtls/library/pkwrite.c
CC ../../lib/mbedtls/library/platform.c
CC ../../lib/mbedtls/library/platform_util.c
CC ../../lib/mbedtls/library/poly1305.c
CC ../../lib/mbedtls/library/ripemd160.c
CC ../../lib/mbedtls/library/rsa.c
CC ../../lib/mbedtls/library/rsa_alt_helpers.c
CC ../../lib/mbedtls/library/sha1.c
CC ../../lib/mbedtls/library/sha256.c
CC ../../lib/mbedtls/library/sha512.c
CC ../../lib/mbedtls/library/ssl_cache.c
CC ../../lib/mbedtls/library/ssl_ciphersuites.c
CC ../../lib/mbedtls/library/ssl_client.c
CC ../../lib/mbedtls/library/ssl_cookie.c
CC ../../lib/mbedtls/library/ssl_debug_helpers_generated.c
CC ../../lib/mbedtls/library/ssl_msg.c
CC ../../lib/mbedtls/library/ssl_ticket.c
CC ../../lib/mbedtls/library/ssl_tls.c
CC ../../lib/mbedtls/library/ssl_tls12_client.c
CC ../../lib/mbedtls/library/ssl_tls12_server.c
CC ../../lib/mbedtls/library/timing.c
CC ../../lib/mbedtls/library/x509.c
CC ../../lib/mbedtls/library/x509_create.c
CC ../../lib/mbedtls/library/x509_crl.c
CC ../../lib/mbedtls/library/x509_crt.c
CC ../../lib/mbedtls/library/x509_csr.c
CC ../../lib/mbedtls/library/x509write_crt.c
CC ../../lib/mbedtls/library/x509write_csr.c
CC ../../lib/berkeley-db-1.xx/btree/bt_close.c
CC ../../lib/berkeley-db-1.xx/btree/bt_conv.c
CC ../../lib/berkeley-db-1.xx/btree/bt_debug.c
CC ../../lib/berkeley-db-1.xx/btree/bt_delete.c
CC ../../lib/berkeley-db-1.xx/btree/bt_get.c
CC ../../lib/berkeley-db-1.xx/btree/bt_open.c
CC ../../lib/berkeley-db-1.xx/btree/bt_overflow.c
CC ../../lib/berkeley-db-1.xx/btree/bt_page.c
CC ../../lib/berkeley-db-1.xx/btree/bt_put.c
CC ../../lib/berkeley-db-1.xx/btree/bt_search.c
CC ../../lib/berkeley-db-1.xx/btree/bt_seq.c
CC ../../lib/berkeley-db-1.xx/btree/bt_split.c
CC ../../lib/berkeley-db-1.xx/btree/bt_utils.c
CC ../../lib/berkeley-db-1.xx/mpool/mpool.c
CC main.c
CC gccollect.c
CC unix_mphal.c
CC mpthreadport.c
CC input.c
CC alloc.c
CC fatfs_port.c
CC mpbthciport.c
CC mpbtstackport_common.c
CC mpbtstackport_usb.c
CC mpbtstackport_h4.c
CC mpnimbleport.c
CC modtermios.c
CC modsocket.c
CC modffi.c
CC modjni.c
CC ../../shared/runtime/gchelper_generic.c
CC ../../shared/runtime/pyexec.c
CC ../../shared/timeutils/timeutils.c
CC ../../shared/readline/readline.c
CC build-standard/frozen_content.c
LINK build-standard/micropython
   text	   data	    bss	    dec	    hex	filename
 750027	  64384	  10584	 824995	  c96a3	build-standard/micropython
$ /home/nico/pico-toolchain/micropython/ports/unix/build-standard/micropython -c import sys; print(sys.implementation)
(name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')
Built: (name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')

== Importing the frozen verification module inside the Unix port and checking its result
$ /home/nico/pico-toolchain/micropython/ports/unix/build-standard/micropython -c import frozen_verify_test; print(frozen_verify_test.RESULT)
FROZEN_VERIFY_OK: micropython
FROZEN_VERIFY_OK: micropython

== Building firmware for BOARD=RPI_PICO_W (frozen manifest /tmp/tmpf2_60_ji/manifest_rp2.py)
$ make -j4 BOARD=RPI_PICO_W BOARD_DIR=/home/nico/pico-toolchain/build_overrides/lwip_connection_counts_board USER_C_MODULES=/home/nico/pico-toolchain/build_overrides/modlwip_eagain FROZEN_MANIFEST=/tmp/tmpf2_60_ji/manifest_rp2.py   (cwd=/home/nico/pico-toolchain/micropython/ports/rp2)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
PICO_SDK_PATH is /home/nico/pico-toolchain/micropython/lib/pico-sdk
Target board (PICO_BOARD) is 'pico_w'.
Using board configuration from /home/nico/pico-toolchain/micropython/lib/pico-sdk/src/boards/include/boards/pico_w.h
Defaulting platform (PICO_PLATFORM) to 'rp2040' based on PICO_BOARD setting.
Defaulting compiler (PICO_COMPILER) to 'pico_arm_cortex_m0plus_gcc' since not specified or detected.
Configuring toolchain based on PICO_COMPILER 'pico_arm_cortex_m0plus_gcc'
Defaulting PICO_GCC_TRIPLE to 'arm-none-eabi'
-- The C compiler identification is GNU 14.2.1
-- The CXX compiler identification is GNU 14.2.1
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /usr/bin/arm-none-eabi-gcc - skipped
-- Detecting C compile features
-- Detecting C compile features - done
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/arm-none-eabi-g++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- The ASM compiler identification is GNU
-- Found assembler: /usr/bin/arm-none-eabi-gcc
Build type is MinSizeRel
-- Found Python3: /usr/bin/python3 (found version "3.13.5") found components: Interpreter
-- Detected native TLS (__aeabi_read_tp)
TinyUSB available at /home/nico/pico-toolchain/micropython/lib/tinyusb/hw/bsp/rp2040; enabling build support for USB.
BTstack available at /home/nico/pico-toolchain/micropython/lib/btstack
cyw43-driver available at /home/nico/pico-toolchain/micropython/lib/cyw43-driver
Pico W Bluetooth build support available.
lwIP available at /home/nico/pico-toolchain/micropython/lib/lwip
Pico W Wi-Fi build support available.
C library type is newlib
Including User C Module(s) from /home/nico/pico-toolchain/build_overrides/modlwip_eagain/micropython.cmake
Found User C Module(s): 
Using picotool from /usr/local/bin/picotool
-- Configuring done (2.7s)
-- Generating done (0.5s)
-- Build files have been written to: /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W
make[1]: Entering directory '/home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W'
[  0%] Creating directories for 'pioasmBuild'
[  0%] Building ASM object pico-sdk/src/rp2040/boot_stage2/CMakeFiles/bs2_default.dir/compile_time_choice.S.o
[  0%] No download step for 'pioasmBuild'
[  0%] Linking ASM executable bs2_default.elf
[  1%] No update step for 'pioasmBuild'
GEN /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W/genhdr/mpversion.h
[  1%] Built target bs2_default
[  1%] Built target BUILD_VERSION_HEADER
[  1%] No patch step for 'pioasmBuild'
[  1%] Generating bs2_default.bin
[  1%] Generating genhdr/pins.h, pins_RPI_PICO_W.c
[  1%] Generating bs2_default_padded_checksummed.S
[  1%] Performing configure step for 'pioasmBuild'
Not searching for unused variables given on the command line.
loading initial cache file /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W/pico-sdk/src/rp2_common/pico_cyw43_driver/pioasm/tmp/pioasmBuild-cache-MinSizeRel.cmake
[  1%] Building ASM object pico-sdk/src/rp2040/boot_stage2/CMakeFiles/bs2_default_library.dir/bs2_default_padded_checksummed.S.o
[  1%] Generating genhdr/qstr.i.last
[  1%] Built target bs2_default_library
-- The CXX compiler identification is GNU 14.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
-- Detecting CXX compile features - done
-- Configuring done (0.9s)
-- Generating done (0.0s)
-- Build files have been written to: /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W/pioasm
[  2%] Performing build step for 'pioasmBuild'
[  2%] Generating genhdr/qstr.split
[  3%] Generating genhdr/root_pointers.split
[  3%] Generating genhdr/qstrdefs.collected.h
QSTR updated
[  3%] Generating genhdr/root_pointers.collected
Root pointer registrations updated
[  3%] Generating genhdr/qstrdefs.preprocessed.h
[  3%] Generating genhdr/root_pointers.h
[  3%] Generating genhdr/qstrdefs.generated.h
MPY _boot.py
MPY _boot_fat.py
MPY rp2.py
MPY asyncio/__init__.py
MPY asyncio/core.py
MPY asyncio/event.py
MPY asyncio/funcs.py
MPY asyncio/lock.py
MPY asyncio/stream.py
MPY uasyncio.py
MPY onewire.py
MPY ds18x20.py
MPY dht.py
MPY neopixel.py
MPY requests/__init__.py
MPY mip/__init__.py
MPY ntptime.py
MPY ssl.py
MPY webrepl.py
MPY webrepl_setup.py
MPY urequests.py
MPY aioble/__init__.py
MPY aioble/core.py
MPY aioble/device.py
MPY aioble/peripheral.py
MPY aioble/server.py
MPY aioble/central.py
MPY aioble/client.py
MPY aioble/l2cap.py
MPY aioble/security.py
MPY frozen_verify_test.py
GEN /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W/frozen_content.c
[  3%] Built target BUILD_FROZEN_CONTENT
[100%] Built target pioasm
[  3%] Performing install step for 'pioasmBuild'
[100%] Built target pioasm
Install the project...
-- Install configuration: "Release"
[  3%] Completed 'pioasmBuild'
[  3%] Built target pioasmBuild
[  3%] Generating cyw43_bus_pio_spi.pio.h
[  3%] Built target cyw43_driver_picow_cyw43_bus_pio_spi_pio_h
[  3%] Generating genhdr/moduledefs.split
[  3%] Generating genhdr/compressed.split
[  3%] Generating genhdr/moduledefs.collected
Module registrations updated
[  3%] Generating genhdr/compressed.collected
[  3%] Generating genhdr/moduledefs.h
Compressed data updated
[  3%] Generating genhdr/compressed.data.h
[  3%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/argcheck.c.o
[  3%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmbase.c.o
[  3%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmarm.c.o
[  3%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmrv32.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmthumb.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmx64.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmx86.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/asmxtensa.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/bc.c.o
[  4%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/binary.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/builtinevex.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/builtinhelp.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/builtinimport.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/compile.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/cstack.c.o
[  5%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitbc.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitcommon.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitglue.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitinlinerv32.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitinlinethumb.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitinlinextensa.c.o
[  6%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnarm.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitndebug.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnrv32.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnthumb.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnx64.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnx86.c.o
[  7%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnxtensa.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/emitnxtensawin.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/formatfloat.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/frozenmod.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/gc.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/lexer.c.o
[  8%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/malloc.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/map.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modarray.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modbuiltins.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modcmath.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modcollections.c.o
[  9%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modgc.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modio.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modmath.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modmicropython.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modstring.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modstruct.c.o
[ 10%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modsys.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modthread.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/moderrno.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/modweakref.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/mpprint.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/mpstate.c.o
[ 11%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/mpz.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nativeglue.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlr.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlraarch64.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrloong64.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrmips.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrpowerpc.c.o
[ 12%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrrv32.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrrv64.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrsetjmp.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrthumb.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrx64.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrx86.c.o
[ 13%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/nlrxtensa.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/obj.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objarray.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objattrtuple.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objbool.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objboundmeth.c.o
[ 14%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objcode.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objcell.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objclosure.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objcomplex.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objdeque.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objdict.c.o
[ 15%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objenumerate.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objexcept.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objfilter.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objfloat.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objfun.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objgenerator.c.o
[ 16%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objgetitemiter.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objint.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objint_longlong.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objint_mpz.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objlist.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objmap.c.o
[ 17%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objmodule.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objnamedtuple.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objnone.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objobject.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objpolyiter.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objproperty.c.o
[ 18%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objrange.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objreversed.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objringio.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objset.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objsingleton.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objslice.c.o
[ 19%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objstr.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objstringio.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objstrunicode.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objtemplate.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objtuple.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objtype.c.o
[ 20%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/objzip.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/opmethods.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/pairheap.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/parse.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/parsenum.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/parsenumbase.c.o
[ 21%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/persistentcode.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/profile.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/pystack.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/qstr.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/reader.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/repl.c.o
[ 22%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/ringbuf.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/runtime.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/runtime_utils.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/scheduler.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/scope.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/sequence.c.o
[ 23%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/showbc.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/smallint.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/stackctrl.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/stream.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/unicode.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/vm.c.o
[ 24%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/vstr.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/py/warning.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/libc/abort_.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/libc/printf.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/btstack/modbluetooth_btstack.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_adc.c.o
[ 25%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_adc_block.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_bitstream.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_can.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_i2c.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_i2c_target.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_i2s.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_mem.c.o
[ 26%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_pulse.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_pwm.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_signal.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_spi.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_uart.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_usb_device.c.o
[ 27%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/machine_wdt.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modbluetooth.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modframebuf.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modmachine.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modmarshal.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modnetwork.c.o
[ 28%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modonewire.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modasyncio.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modbinascii.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modcryptolib.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/moductypes.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/moddeflate.c.o
[ 29%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modhashlib.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modheapq.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modjson.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modos.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modplatform.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modrandom.c.o
[ 30%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modre.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modselect.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modsocket.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modtls_axtls.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modtls_mbedtls.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modtime.c.o
[ 31%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modvfs.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modwebsocket.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/modwebrepl.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_cyw43.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_lwip.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_ninaw10.c.o
[ 32%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_ppp_lwip.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_usbd_ncm.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/network_wiznet5k.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/os_dupterm.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_blockdev.c.o
[ 33%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_fat.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_fat_diskio.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_fat_file.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_lfs.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_rom.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_rom_file.c.o
[ 34%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_posix.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_posix_file.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/vfs_reader.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/virtpin.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/nimble/modbluetooth_nimble.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/build_overrides/modlwip_eagain/modlwip.c.o
[ 35%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/extmod/mbedtls/mbedtls_alt.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/littlefs/lfs1.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/littlefs/lfs1_util.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/littlefs/lfs2.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/littlefs/lfs2_util.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/oofatfs/ff.c.o
[ 36%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/oofatfs/ffunicode.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/netutils/dhcpserver.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/netutils/netutils.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/netutils/trace.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/readline/readline.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/gchelper_native.c.o
[ 37%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/interrupt_char.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/mpirq.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/pyexec.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/stdout_helpers.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/softtimer.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/sys_stdio_mphal.c.o
[ 38%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/timeutils/timeutils.c.o
[ 39%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/tinyusb/mp_usbd.c.o
[ 39%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/tinyusb/mp_usbd_cdc.c.o
[ 39%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/tinyusb/mp_usbd_descriptor.c.o
[ 39%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/tinyusb/mp_usbd_runtime.c.o
[ 39%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/shared/runtime/gchelper_thumb1.s.o
[ 39%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/drivers/bus/softspi.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/drivers/dht/dht.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/clocks_extra.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/datetime_patch.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/fatfs_port.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/help.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/machine_bitstream.c.o
[ 40%] Building C object CMakeFiles/firmware.dir/machine_i2c.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/machine_pin.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/machine_rtc.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/machine_spi.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/machine_timer.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/main.c.o
[ 41%] Building C object CMakeFiles/firmware.dir/modrp2.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/mphalport.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/mpnetworkport.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/mpthreadport.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/mutex_extra.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/pendsv.c.o
[ 42%] Building C object CMakeFiles/firmware.dir/rp2_flash.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/rp2_pio.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/rp2_dma.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/uart.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/usbd.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/msc_disk.c.o
[ 43%] Building C object CMakeFiles/firmware.dir/mbedtls/mbedtls_port.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/pins_RPI_PICO_W.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/mpbthciport.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/mpbtstackport.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/machine_pin_cyw43.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/frozen_content.c.o
[ 44%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/apps/mdns/mdns.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/apps/mdns/mdns_domain.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/apps/mdns/mdns_out.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/def.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/dns.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/inet_chksum.c.o
[ 45%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/init.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ip.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/acd.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/autoip.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/dhcp.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/etharp.c.o
[ 46%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/icmp.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/igmp.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/ip4.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/ip4_addr.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv4/ip4_frag.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/dhcp6.c.o
[ 47%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/ethip6.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/icmp6.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/inet6.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/ip6.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/ip6_addr.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/ip6_frag.c.o
[ 48%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/mld6.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/ipv6/nd6.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/mem.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/memp.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/netif.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/pbuf.c.o
[ 49%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/raw.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/stats.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/sys.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/tcp.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/tcp_in.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/tcp_out.c.o
[ 50%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/timeouts.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/core/udp.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ethernet.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/auth.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/ccp.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/chap-md5.c.o
[ 51%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/chap_ms.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/chap-new.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/demand.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/eap.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/ecp.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/eui64.c.o
[ 52%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/fsm.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/ipcp.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/ipv6cp.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/lcp.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/magic.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/mppe.c.o
[ 53%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/multilink.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/polarssl/md5.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/pppapi.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/ppp.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/pppcrypt.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/pppoe.c.o
[ 54%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/pppol2tp.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/pppos.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/upap.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/utils.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/lwip/src/netif/ppp/vj.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cyw43_driver/btstack_hci_transport_cyw43.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cyw43_driver/btstack_chipset_cyw43.c.o
[ 55%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/platform/embedded/hci_dump_embedded_stdout.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ad_parser.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/ancs_client.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/att_db.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/att_db_util.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/att_dispatch.c.o
[ 56%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/att_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/battery_service_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/cycling_power_service_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/cycling_speed_and_cadence_service_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/device_information_service_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/heart_rate_service_server.c.o
[ 57%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/hids_device.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/mesh/gatt-service/mesh_provisioning_service_server.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/mesh/gatt-service/mesh_proxy_service_server.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/nordic_spp_service_server.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt-service/ublox_spp_service_server.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/le_device_db_memory.c.o
[ 58%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/gatt_client.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/ble/sm.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_audio.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_base64_decoder.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_crypto.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_hid_parser.c.o
[ 59%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_linked_list.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_memory.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_memory_pool.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_resample.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_ring_buffer.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_run_loop.c.o
[ 60%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_run_loop_base.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_slip.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_tlv.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_tlv_none.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/btstack_util.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/hci.c.o
[ 61%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/hci_cmd.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/hci_dump.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/hci_transport_em9304_spi.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/hci_transport_h4.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/l2cap.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/btstack/src/l2cap_signaling.c.o
[ 62%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cyw43_driver/cyw43_bus_pio_spi.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/cyw43-driver/src/cyw43_ll.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/cyw43-driver/src/cyw43_stats.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/cyw43-driver/src/cyw43_lwip.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/cyw43-driver/src/cyw43_ctrl.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cyw43_driver/cybt_shared_bus/cybt_shared_bus.c.o
[ 63%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cyw43_driver/cybt_shared_bus/cybt_shared_bus_driver.c.o
[ 64%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_pio/pio.c.o
[ 64%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2040/pico_platform/platform.c.o
[ 64%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_platform_common/common.c.o
[ 64%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_platform_panic/panic.c.o
[ 64%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_platform_panic/custom_panic_function.S.o
[ 64%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/hardware_claim/claim.c.o
[ 65%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_sync/sync.c.o
[ 65%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_sync_spin_lock/sync_spin_lock.c.o
[ 65%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_gpio/gpio.c.o
[ 65%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_irq/irq.c.o
[ 65%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_irq/irq_handler_chain.S.o
[ 65%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_sync/sem.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_sync/lock_core.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_sync/mutex.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_sync/critical_section.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_time/time.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_time/timeout_helper.c.o
[ 66%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_timer/timer.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_util/datetime.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_util/fixed_bitset.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_util/pheap.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/common/pico_util/queue.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_dma/dma.c.o
[ 67%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_exception/exception.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls_errors/mp_mbedtls_errors.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/aes.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/aesni.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/asn1parse.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/asn1write.c.o
[ 68%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/base64.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/bignum_core.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/bignum_mod.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/bignum_mod_raw.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/bignum.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/camellia.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ccm.c.o
[ 69%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/chacha20.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/chachapoly.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/cipher.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/cipher_wrap.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/nist_kw.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/aria.c.o
[ 70%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/cmac.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/mps_reader.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/mps_trace.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ctr_drbg.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/debug.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/des.c.o
[ 71%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/dhm.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ecdh.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ecdsa.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ecjpake.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ecp.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ecp_curves.c.o
[ 72%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/entropy.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/entropy_poll.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/gcm.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/hmac_drbg.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/md5.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/md.c.o
[ 73%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/oid.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/padlock.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pem.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pk.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pkcs12.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pkcs5.c.o
[ 74%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pkparse.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pk_ecc.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pk_wrap.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/pkwrite.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/platform.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/platform_util.c.o
[ 75%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/poly1305.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ripemd160.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/rsa.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/rsa_alt_helpers.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/sha1.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/sha256.c.o
[ 76%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/sha512.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_cache.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_ciphersuites.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_tls12_client.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_tls12_server.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_client.c.o
[ 77%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_cookie.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_debug_helpers_generated.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_msg.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_ticket.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/ssl_tls.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/timing.c.o
[ 78%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/constant_time.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509_create.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509_crl.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509_crt.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509_csr.c.o
[ 79%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509write_crt.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/mbedtls/library/x509write_csr.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_adc/adc.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_boot_lock/boot_lock.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_clocks/clocks.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_pll/pll.c.o
[ 80%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_vreg/vreg.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_watchdog/watchdog.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_ticks/ticks.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_bootrom/bootrom.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_bootrom/bootrom_lock.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_flash/flash.c.o
[ 81%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_xosc/xosc.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_flash/flash.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_xip_cache/xip_cache.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_i2c/i2c.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_spi/spi.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_uart/uart.c.o
[ 82%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_aon_timer/aon_timer.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_rtc/rtc.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_multicore/multicore.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_rand/rand.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_unique_id/unique_id.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_runtime/runtime.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_runtime_init/runtime_init.c.o
[ 83%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_runtime_init/runtime_init_clocks.c.o
[ 84%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_runtime_init/runtime_init_stack_guard.c.o
[ 84%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_bit_ops/bit_ops_aeabi.S.o
[ 84%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_divider/divider_hardware.S.o
[ 84%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_double/double_aeabi_rp2040.S.o
[ 84%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_double/double_init_rom_rp2040.c.o
[ 84%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_double/double_math.c.o
[ 85%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_double/double_v1_rom_shim_rp2040.S.o
[ 85%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/hardware_divider/divider.S.o
[ 85%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_int64_ops/pico_int64_ops_aeabi.S.o
[ 85%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/acoshf.c.o
[ 85%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/asinfacosf.c.o
[ 85%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/asinhf.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/atan2f.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/atanhf.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/atanf.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/ef_rem_pio2.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/erf_lgamma.c.o
[ 86%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/fmodf.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/kf_cos.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/kf_rem_pio2.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/kf_sin.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/kf_tan.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/log1pf.c.o
[ 87%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/math.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/nearbyintf.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/roundf.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_cos.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_erf.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_frexp.c.o
[ 88%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_ldexp.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_modf.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_sin.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/sf_tan.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/wf_lgamma.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/wf_tgamma.c.o
[ 89%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/libm/ef_sqrt.c.o
[ 90%] Building C object CMakeFiles/firmware.dir/libm_extra.c.o
[ 90%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_float/float_aeabi_rp2040.S.o
[ 90%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_float/float_init_rom_rp2040.c.o
[ 90%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_float/float_v1_rom_shim_rp2040.S.o
[ 90%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_malloc/malloc.c.o
[ 90%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_mem_ops/mem_ops_aeabi.S.o
[ 91%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_atomic/atomic.c.o
[ 91%] Building CXX object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_cxx_options/new_delete.cpp.o
[ 91%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_standard_binary_info/standard_binary_info.c.o
[ 91%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_printf/printf.c.o
[ 91%] Building ASM object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_crt0/crt0.S.o
[ 91%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_clib_interface/newlib_interface.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_clib_interface/cxa_guard.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_stdio/stdio.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_stdio_uart/stdio_uart.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_thread_local/thread_local.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_stdlib/stdlib.c.o
[ 92%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/tusb.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/common/tusb_fifo.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/portable/raspberrypi/rp2040/dcd_rp2040.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/portable/raspberrypi/rp2040/rp2040_usb.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/device/usbd.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/audio/audio_device.c.o
[ 93%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/cdc/cdc_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/dfu/dfu_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/dfu/dfu_rt_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/hid/hid_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/midi/midi_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/midi/midi2_device.c.o
[ 94%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/msc/msc_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/mtp/mtp_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/net/ecm_rndis_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/net/ncm_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/printer/printer_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/usbtmc/usbtmc_device.c.o
[ 95%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/vendor/vendor_device.c.o
[ 96%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/tinyusb/src/class/video/video_device.c.o
[ 96%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/pico_fix/rp2040_usb_device_enumeration/rp2040_usb_device_enumeration.c.o
[ 96%] Building C object CMakeFiles/firmware.dir/home/nico/pico-toolchain/micropython/lib/pico-sdk/src/rp2_common/cmsis/stub/CMSIS/Device/RP2040/Source/system_RP2040.c.o
[ 96%] Linking CXX executable firmware.elf
Memory region         Used Size  Region Size  %age Used
           FLASH:      909796 B      1200 KB     74.04%
     FLASH_ROMFS:           0 B          0 B
        FLASH_FS:           0 B       848 KB      0.00%
         XIP_RAM:           0 B        16 KB      0.00%
             RAM:       71832 B       256 KB     27.40%
       SCRATCH_X:           0 B          0 B
       SCRATCH_Y:          8 KB         8 KB    100.00%
[100%] Built target firmware
make[1]: Leaving directory '/home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W'

== Cleaning up the frozen-bytecode verification build artifacts
Removing /home/nico/pico-toolchain/micropython/ports/rp2/build-RPI_PICO_W
Removing /home/nico/pico-toolchain/micropython/ports/unix/build-standard

== Building the MicroPython Unix port (settrace-free, the test rig)
$ make -j4 VARIANT=standard VARIANT_DIR=/home/nico/pico-toolchain/build_overrides/unix_kbd_intr_variant   (cwd=/home/nico/pico-toolchain/micropython/ports/unix)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
mkdir -p build-standard/genhdr
mkdir -p build-standard/
mkdir -p build-standard/extmod/
mkdir -p build-standard/extmod/mbedtls/
mkdir -p build-standard/lib/berkeley-db-1.xx/btree/
mkdir -p build-standard/lib/berkeley-db-1.xx/mpool/
mkdir -p build-standard/lib/littlefs/
mkdir -p build-standard/lib/mbedtls/library/
mkdir -p build-standard/lib/mbedtls_errors/
mkdir -p build-standard/lib/oofatfs/
mkdir -p build-standard/py/
mkdir -p build-standard/shared/libc/
mkdir -p build-standard/shared/readline/
mkdir -p build-standard/shared/runtime/
mkdir -p build-standard/shared/timeutils/
GEN build-standard/genhdr/mpversion.h
GEN build-standard/genhdr/qstr.i.last
GEN build-standard/genhdr/qstr.split
GEN build-standard/genhdr/moduledefs.split
GEN build-standard/genhdr/root_pointers.split
GEN build-standard/genhdr/compressed.split
GEN build-standard/genhdr/root_pointers.collected
GEN build-standard/genhdr/moduledefs.collected
GEN build-standard/genhdr/compressed.collected
GEN build-standard/genhdr/qstrdefs.collected.h
Root pointer registrations updated
Module registrations updated
Compressed data updated
GEN build-standard/genhdr/root_pointers.h
GEN build-standard/genhdr/moduledefs.h
QSTR updated
GEN build-standard/genhdr/compressed.data.h
GEN build-standard/genhdr/qstrdefs.generated.h
CC ../../py/mpstate.c
CC ../../py/nlr.c
CC ../../py/nlrx86.c
CC ../../py/nlrx64.c
CC ../../py/nlrthumb.c
CC ../../py/nlraarch64.c
CC ../../py/nlrmips.c
CC ../../py/nlrpowerpc.c
CC ../../py/nlrxtensa.c
CC ../../py/nlrrv32.c
CC ../../py/nlrrv64.c
CC ../../py/nlrloong64.c
CC ../../py/nlrsetjmp.c
CC ../../py/malloc.c
CC ../../py/gc.c
CC ../../py/pystack.c
CC ../../py/qstr.c
CC ../../py/vstr.c
CC ../../py/mpprint.c
CC ../../py/unicode.c
CC ../../py/mpz.c
CC ../../py/reader.c
CC ../../py/lexer.c
CC ../../py/parse.c
CC ../../py/scope.c
CC ../../py/compile.c
CC ../../py/emitcommon.c
CC ../../py/emitbc.c
CC ../../py/asmbase.c
CC ../../py/asmx64.c
CC ../../py/emitnx64.c
CC ../../py/asmx86.c
CC ../../py/emitnx86.c
CC ../../py/asmthumb.c
CC ../../py/emitnthumb.c
CC ../../py/emitinlinethumb.c
CC ../../py/asmarm.c
CC ../../py/emitnarm.c
CC ../../py/asmxtensa.c
CC ../../py/emitnxtensa.c
CC ../../py/emitinlinextensa.c
CC ../../py/emitnxtensawin.c
CC ../../py/asmrv32.c
CC ../../py/emitnrv32.c
CC ../../py/emitinlinerv32.c
CC ../../py/emitndebug.c
CC ../../py/formatfloat.c
CC ../../py/parsenumbase.c
CC ../../py/parsenum.c
CC ../../py/emitglue.c
CC ../../py/persistentcode.c
CC ../../py/runtime.c
CC ../../py/runtime_utils.c
CC ../../py/scheduler.c
CC ../../py/nativeglue.c
CC ../../py/pairheap.c
CC ../../py/ringbuf.c
CC ../../py/cstack.c
CC ../../py/stackctrl.c
CC ../../py/argcheck.c
CC ../../py/warning.c
CC ../../py/profile.c
CC ../../py/map.c
CC ../../py/obj.c
CC ../../py/objarray.c
CC ../../py/objattrtuple.c
CC ../../py/objbool.c
CC ../../py/objboundmeth.c
CC ../../py/objcell.c
CC ../../py/objclosure.c
CC ../../py/objcode.c
CC ../../py/objcomplex.c
CC ../../py/objdeque.c
CC ../../py/objdict.c
CC ../../py/objenumerate.c
CC ../../py/objexcept.c
CC ../../py/objfilter.c
CC ../../py/objfloat.c
CC ../../py/objfun.c
CC ../../py/objgenerator.c
CC ../../py/objgetitemiter.c
CC ../../py/objint.c
CC ../../py/objint_longlong.c
CC ../../py/objint_mpz.c
CC ../../py/objlist.c
CC ../../py/objmap.c
CC ../../py/objmodule.c
CC ../../py/objobject.c
CC ../../py/objpolyiter.c
CC ../../py/objproperty.c
CC ../../py/objnone.c
CC ../../py/objnamedtuple.c
CC ../../py/objrange.c
CC ../../py/objreversed.c
CC ../../py/objringio.c
CC ../../py/objset.c
CC ../../py/objsingleton.c
CC ../../py/objslice.c
CC ../../py/objstr.c
CC ../../py/objstrunicode.c
CC ../../py/objstringio.c
CC ../../py/objtemplate.c
CC ../../py/objtuple.c
CC ../../py/objtype.c
CC ../../py/objzip.c
CC ../../py/opmethods.c
CC ../../py/sequence.c
CC ../../py/stream.c
CC ../../py/binary.c
CC ../../py/builtinimport.c
CC ../../py/builtinevex.c
CC ../../py/builtinhelp.c
CC ../../py/modarray.c
CC ../../py/modbuiltins.c
CC ../../py/modcollections.c
CC ../../py/modgc.c
CC ../../py/modio.c
CC ../../py/modmath.c
CC ../../py/modcmath.c
CC ../../py/modmicropython.c
CC ../../py/modstring.c
CC ../../py/modstruct.c
CC ../../py/modsys.c
CC ../../py/moderrno.c
CC ../../py/modthread.c
CC ../../py/modweakref.c
CC ../../py/vm.c
CC ../../py/bc.c
CC ../../py/showbc.c
CC ../../py/repl.c
CC ../../py/smallint.c
CC ../../py/frozenmod.c
CC ../../extmod/machine_adc.c
CC ../../extmod/machine_adc_block.c
CC ../../extmod/machine_bitstream.c
CC ../../extmod/machine_can.c
CC ../../extmod/machine_i2c.c
CC ../../extmod/machine_i2c_target.c
CC ../../extmod/machine_i2s.c
CC ../../extmod/machine_mem.c
MPY argparse.py
MPY requests/__init__.py
MPY mip/__init__.py
MPY mip/__main__.py
MPY ssl.py
MPY asyncio/__init__.py
MPY asyncio/core.py
MPY asyncio/event.py
MPY asyncio/funcs.py
MPY asyncio/lock.py
MPY asyncio/stream.py
MPY uasyncio.py
GEN build-standard/frozen_content.c
CC ../../extmod/machine_pinbase.c
CC ../../extmod/machine_pulse.c
CC ../../extmod/machine_pwm.c
CC ../../extmod/machine_signal.c
CC ../../extmod/machine_spi.c
CC ../../extmod/machine_timer.c
CC ../../extmod/machine_uart.c
CC ../../extmod/machine_usb_device.c
CC ../../extmod/machine_wdt.c
CC ../../extmod/modasyncio.c
CC ../../extmod/modbinascii.c
CC ../../extmod/modbluetooth.c
CC ../../extmod/modbtree.c
CC ../../extmod/modcryptolib.c
CC ../../extmod/moddeflate.c
CC ../../extmod/modframebuf.c
CC ../../extmod/modhashlib.c
CC ../../extmod/modheapq.c
CC ../../extmod/modjson.c
CC ../../extmod/modlwip.c
CC ../../extmod/modmachine.c
CC ../../extmod/modmarshal.c
CC ../../extmod/modnetwork.c
CC ../../extmod/modonewire.c
CC ../../extmod/modopenamp.c
CC ../../extmod/modopenamp_remoteproc.c
CC ../../extmod/modopenamp_remoteproc_store.c
CC ../../extmod/modos.c
CC ../../extmod/modplatform.c
CC ../../extmod/modrandom.c
CC ../../extmod/modre.c
CC ../../extmod/modselect.c
CC ../../extmod/modsocket.c
CC ../../extmod/modtls_axtls.c
CC ../../extmod/modtls_mbedtls.c
CC ../../extmod/mbedtls/mbedtls_alt.c
CC ../../extmod/modtime.c
CC ../../extmod/moductypes.c
CC ../../extmod/modvfs.c
CC ../../extmod/modwebrepl.c
CC ../../extmod/modwebsocket.c
CC ../../extmod/network_cyw43.c
CC ../../extmod/network_esp_hosted.c
CC ../../extmod/network_lwip.c
CC ../../extmod/network_ninaw10.c
CC ../../extmod/network_ppp_lwip.c
CC ../../extmod/network_usbd_ncm.c
CC ../../extmod/network_wiznet5k.c
CC ../../extmod/os_dupterm.c
CC ../../extmod/vfs.c
CC ../../extmod/vfs_blockdev.c
CC ../../extmod/vfs_fat.c
CC ../../extmod/vfs_fat_diskio.c
CC ../../extmod/vfs_fat_file.c
CC ../../extmod/vfs_lfs.c
CC ../../extmod/vfs_rom.c
CC ../../extmod/vfs_rom_file.c
CC ../../extmod/vfs_posix.c
CC ../../extmod/vfs_posix_file.c
CC ../../extmod/vfs_reader.c
CC ../../extmod/virtpin.c
CC ../../shared/libc/abort_.c
CC ../../shared/libc/printf.c
CC ../../lib/oofatfs/ff.c
CC ../../lib/oofatfs/ffunicode.c
CC ../../lib/littlefs/lfs1.c
CC ../../lib/littlefs/lfs1_util.c
CC ../../lib/littlefs/lfs2.c
CC ../../lib/littlefs/lfs2_util.c
CC ../../lib/mbedtls_errors/mp_mbedtls_errors.c
CC ../../lib/mbedtls/library/aes.c
CC ../../lib/mbedtls/library/aesni.c
CC ../../lib/mbedtls/library/asn1parse.c
CC ../../lib/mbedtls/library/asn1write.c
CC ../../lib/mbedtls/library/base64.c
CC ../../lib/mbedtls/library/bignum_core.c
CC ../../lib/mbedtls/library/bignum_mod.c
CC ../../lib/mbedtls/library/bignum_mod_raw.c
CC ../../lib/mbedtls/library/bignum.c
CC ../../lib/mbedtls/library/camellia.c
CC ../../lib/mbedtls/library/ccm.c
CC ../../lib/mbedtls/library/chacha20.c
CC ../../lib/mbedtls/library/chachapoly.c
CC ../../lib/mbedtls/library/cipher.c
CC ../../lib/mbedtls/library/cipher_wrap.c
CC ../../lib/mbedtls/library/nist_kw.c
CC ../../lib/mbedtls/library/aria.c
CC ../../lib/mbedtls/library/cmac.c
CC ../../lib/mbedtls/library/constant_time.c
CC ../../lib/mbedtls/library/mps_reader.c
CC ../../lib/mbedtls/library/mps_trace.c
CC ../../lib/mbedtls/library/ctr_drbg.c
CC ../../lib/mbedtls/library/debug.c
CC ../../lib/mbedtls/library/des.c
CC ../../lib/mbedtls/library/dhm.c
CC ../../lib/mbedtls/library/ecdh.c
CC ../../lib/mbedtls/library/ecdsa.c
CC ../../lib/mbedtls/library/ecjpake.c
CC ../../lib/mbedtls/library/ecp.c
CC ../../lib/mbedtls/library/ecp_curves.c
CC ../../lib/mbedtls/library/entropy.c
CC ../../lib/mbedtls/library/entropy_poll.c
CC ../../lib/mbedtls/library/gcm.c
CC ../../lib/mbedtls/library/hmac_drbg.c
CC ../../lib/mbedtls/library/md5.c
CC ../../lib/mbedtls/library/md.c
CC ../../lib/mbedtls/library/oid.c
CC ../../lib/mbedtls/library/padlock.c
CC ../../lib/mbedtls/library/pem.c
CC ../../lib/mbedtls/library/pk.c
CC ../../lib/mbedtls/library/pkcs12.c
CC ../../lib/mbedtls/library/pkcs5.c
CC ../../lib/mbedtls/library/pkparse.c
CC ../../lib/mbedtls/library/pk_ecc.c
CC ../../lib/mbedtls/library/pk_wrap.c
CC ../../lib/mbedtls/library/pkwrite.c
CC ../../lib/mbedtls/library/platform.c
CC ../../lib/mbedtls/library/platform_util.c
CC ../../lib/mbedtls/library/poly1305.c
CC ../../lib/mbedtls/library/ripemd160.c
CC ../../lib/mbedtls/library/rsa.c
CC ../../lib/mbedtls/library/rsa_alt_helpers.c
CC ../../lib/mbedtls/library/sha1.c
CC ../../lib/mbedtls/library/sha256.c
CC ../../lib/mbedtls/library/sha512.c
CC ../../lib/mbedtls/library/ssl_cache.c
CC ../../lib/mbedtls/library/ssl_ciphersuites.c
CC ../../lib/mbedtls/library/ssl_client.c
CC ../../lib/mbedtls/library/ssl_cookie.c
CC ../../lib/mbedtls/library/ssl_debug_helpers_generated.c
CC ../../lib/mbedtls/library/ssl_msg.c
CC ../../lib/mbedtls/library/ssl_ticket.c
CC ../../lib/mbedtls/library/ssl_tls.c
CC ../../lib/mbedtls/library/ssl_tls12_client.c
CC ../../lib/mbedtls/library/ssl_tls12_server.c
CC ../../lib/mbedtls/library/timing.c
CC ../../lib/mbedtls/library/x509.c
CC ../../lib/mbedtls/library/x509_create.c
CC ../../lib/mbedtls/library/x509_crl.c
CC ../../lib/mbedtls/library/x509_crt.c
CC ../../lib/mbedtls/library/x509_csr.c
CC ../../lib/mbedtls/library/x509write_crt.c
CC ../../lib/mbedtls/library/x509write_csr.c
CC ../../lib/berkeley-db-1.xx/btree/bt_close.c
CC ../../lib/berkeley-db-1.xx/btree/bt_conv.c
CC ../../lib/berkeley-db-1.xx/btree/bt_debug.c
CC ../../lib/berkeley-db-1.xx/btree/bt_delete.c
CC ../../lib/berkeley-db-1.xx/btree/bt_get.c
CC ../../lib/berkeley-db-1.xx/btree/bt_open.c
CC ../../lib/berkeley-db-1.xx/btree/bt_overflow.c
CC ../../lib/berkeley-db-1.xx/btree/bt_page.c
CC ../../lib/berkeley-db-1.xx/btree/bt_put.c
CC ../../lib/berkeley-db-1.xx/btree/bt_search.c
CC ../../lib/berkeley-db-1.xx/btree/bt_seq.c
CC ../../lib/berkeley-db-1.xx/btree/bt_split.c
CC ../../lib/berkeley-db-1.xx/btree/bt_utils.c
CC ../../lib/berkeley-db-1.xx/mpool/mpool.c
CC main.c
CC gccollect.c
CC unix_mphal.c
CC mpthreadport.c
CC input.c
CC alloc.c
CC fatfs_port.c
CC mpbthciport.c
CC mpbtstackport_common.c
CC mpbtstackport_h4.c
CC mpbtstackport_usb.c
CC mpnimbleport.c
CC modtermios.c
CC modsocket.c
CC modffi.c
CC modjni.c
CC ../../shared/runtime/gchelper_generic.c
CC ../../shared/runtime/pyexec.c
CC ../../shared/timeutils/timeutils.c
CC ../../shared/readline/readline.c
CC build-standard/frozen_content.c
LINK build-standard/micropython
   text	   data	    bss	    dec	    hex	filename
 761027	  66392	  10584	 838003	  cc973	build-standard/micropython
$ /home/nico/pico-toolchain/micropython/ports/unix/build-standard/micropython -c import sys; print(sys.implementation)
(name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')
Built: (name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')

== Building the MicroPython Unix port (settrace, for --coverage)
$ make -j4 VARIANT=standard VARIANT_DIR=/home/nico/pico-toolchain/build_overrides/unix_kbd_intr_variant CFLAGS_EXTRA=-DMICROPY_PY_SYS_SETTRACE=1 BUILD=build-settrace   (cwd=/home/nico/pico-toolchain/micropython/ports/unix)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
mkdir -p build-settrace/genhdr
mkdir -p build-settrace/
mkdir -p build-settrace/extmod/
mkdir -p build-settrace/extmod/mbedtls/
mkdir -p build-settrace/lib/berkeley-db-1.xx/btree/
mkdir -p build-settrace/lib/berkeley-db-1.xx/mpool/
mkdir -p build-settrace/lib/littlefs/
mkdir -p build-settrace/lib/mbedtls/library/
mkdir -p build-settrace/lib/mbedtls_errors/
mkdir -p build-settrace/lib/oofatfs/
mkdir -p build-settrace/py/
mkdir -p build-settrace/shared/libc/
mkdir -p build-settrace/shared/readline/
mkdir -p build-settrace/shared/runtime/
mkdir -p build-settrace/shared/timeutils/
GEN build-settrace/genhdr/mpversion.h
GEN build-settrace/genhdr/qstr.i.last
GEN build-settrace/genhdr/qstr.split
GEN build-settrace/genhdr/moduledefs.split
GEN build-settrace/genhdr/root_pointers.split
GEN build-settrace/genhdr/compressed.split
GEN build-settrace/genhdr/root_pointers.collected
GEN build-settrace/genhdr/moduledefs.collected
GEN build-settrace/genhdr/compressed.collected
GEN build-settrace/genhdr/qstrdefs.collected.h
Root pointer registrations updated
Module registrations updated
Compressed data updated
GEN build-settrace/genhdr/root_pointers.h
GEN build-settrace/genhdr/moduledefs.h
GEN build-settrace/genhdr/compressed.data.h
QSTR updated
GEN build-settrace/genhdr/qstrdefs.generated.h
CC ../../py/mpstate.c
CC ../../py/nlr.c
CC ../../py/nlrx86.c
CC ../../py/nlrx64.c
CC ../../py/nlrthumb.c
CC ../../py/nlraarch64.c
CC ../../py/nlrmips.c
CC ../../py/nlrpowerpc.c
CC ../../py/nlrxtensa.c
CC ../../py/nlrrv32.c
CC ../../py/nlrrv64.c
CC ../../py/nlrloong64.c
CC ../../py/nlrsetjmp.c
CC ../../py/malloc.c
CC ../../py/gc.c
CC ../../py/pystack.c
CC ../../py/qstr.c
CC ../../py/vstr.c
CC ../../py/mpprint.c
CC ../../py/unicode.c
CC ../../py/mpz.c
CC ../../py/reader.c
CC ../../py/lexer.c
CC ../../py/parse.c
CC ../../py/scope.c
CC ../../py/compile.c
CC ../../py/emitcommon.c
CC ../../py/emitbc.c
CC ../../py/asmbase.c
CC ../../py/asmx64.c
CC ../../py/emitnx64.c
CC ../../py/asmx86.c
CC ../../py/emitnx86.c
CC ../../py/asmthumb.c
CC ../../py/emitnthumb.c
CC ../../py/emitinlinethumb.c
CC ../../py/asmarm.c
CC ../../py/emitnarm.c
CC ../../py/asmxtensa.c
CC ../../py/emitnxtensa.c
CC ../../py/emitinlinextensa.c
CC ../../py/emitnxtensawin.c
CC ../../py/asmrv32.c
CC ../../py/emitnrv32.c
CC ../../py/emitinlinerv32.c
CC ../../py/emitndebug.c
CC ../../py/formatfloat.c
CC ../../py/parsenumbase.c
CC ../../py/parsenum.c
CC ../../py/emitglue.c
CC ../../py/persistentcode.c
CC ../../py/runtime.c
CC ../../py/runtime_utils.c
CC ../../py/scheduler.c
CC ../../py/nativeglue.c
CC ../../py/pairheap.c
CC ../../py/ringbuf.c
CC ../../py/cstack.c
CC ../../py/stackctrl.c
CC ../../py/argcheck.c
CC ../../py/warning.c
CC ../../py/profile.c
CC ../../py/map.c
CC ../../py/obj.c
CC ../../py/objarray.c
CC ../../py/objattrtuple.c
CC ../../py/objbool.c
CC ../../py/objboundmeth.c
CC ../../py/objcell.c
CC ../../py/objclosure.c
CC ../../py/objcode.c
CC ../../py/objcomplex.c
CC ../../py/objdeque.c
CC ../../py/objdict.c
CC ../../py/objenumerate.c
CC ../../py/objexcept.c
CC ../../py/objfilter.c
CC ../../py/objfloat.c
CC ../../py/objfun.c
CC ../../py/objgenerator.c
CC ../../py/objgetitemiter.c
CC ../../py/objint.c
CC ../../py/objint_longlong.c
CC ../../py/objint_mpz.c
CC ../../py/objlist.c
CC ../../py/objmap.c
CC ../../py/objmodule.c
CC ../../py/objobject.c
CC ../../py/objpolyiter.c
CC ../../py/objproperty.c
CC ../../py/objnone.c
CC ../../py/objnamedtuple.c
CC ../../py/objrange.c
CC ../../py/objreversed.c
CC ../../py/objringio.c
CC ../../py/objset.c
CC ../../py/objsingleton.c
CC ../../py/objslice.c
CC ../../py/objstr.c
CC ../../py/objstrunicode.c
CC ../../py/objstringio.c
CC ../../py/objtemplate.c
CC ../../py/objtuple.c
CC ../../py/objtype.c
CC ../../py/objzip.c
CC ../../py/opmethods.c
CC ../../py/sequence.c
CC ../../py/stream.c
CC ../../py/binary.c
CC ../../py/builtinimport.c
CC ../../py/builtinevex.c
CC ../../py/builtinhelp.c
CC ../../py/modarray.c
CC ../../py/modbuiltins.c
CC ../../py/modcollections.c
CC ../../py/modgc.c
CC ../../py/modio.c
CC ../../py/modmath.c
CC ../../py/modcmath.c
CC ../../py/modmicropython.c
CC ../../py/modstring.c
CC ../../py/modstruct.c
CC ../../py/modsys.c
CC ../../py/moderrno.c
CC ../../py/modthread.c
CC ../../py/modweakref.c
CC ../../py/vm.c
CC ../../py/bc.c
CC ../../py/showbc.c
CC ../../py/repl.c
CC ../../py/smallint.c
CC ../../py/frozenmod.c
CC ../../extmod/machine_adc.c
CC ../../extmod/machine_adc_block.c
CC ../../extmod/machine_bitstream.c
CC ../../extmod/machine_can.c
CC ../../extmod/machine_i2c.c
CC ../../extmod/machine_i2c_target.c
CC ../../extmod/machine_i2s.c
CC ../../extmod/machine_mem.c
CC ../../extmod/machine_pinbase.c
MPY argparse.py
MPY requests/__init__.py
MPY mip/__init__.py
MPY mip/__main__.py
MPY ssl.py
MPY asyncio/__init__.py
MPY asyncio/core.py
MPY asyncio/event.py
MPY asyncio/funcs.py
MPY asyncio/lock.py
MPY asyncio/stream.py
MPY uasyncio.py
GEN build-settrace/frozen_content.c
CC ../../extmod/machine_pulse.c
CC ../../extmod/machine_pwm.c
CC ../../extmod/machine_signal.c
CC ../../extmod/machine_spi.c
CC ../../extmod/machine_timer.c
CC ../../extmod/machine_uart.c
CC ../../extmod/machine_usb_device.c
CC ../../extmod/machine_wdt.c
CC ../../extmod/modasyncio.c
CC ../../extmod/modbinascii.c
CC ../../extmod/modbluetooth.c
CC ../../extmod/modbtree.c
CC ../../extmod/modcryptolib.c
CC ../../extmod/moddeflate.c
CC ../../extmod/modframebuf.c
CC ../../extmod/modhashlib.c
CC ../../extmod/modheapq.c
CC ../../extmod/modjson.c
CC ../../extmod/modlwip.c
CC ../../extmod/modmachine.c
CC ../../extmod/modmarshal.c
CC ../../extmod/modnetwork.c
CC ../../extmod/modonewire.c
CC ../../extmod/modopenamp.c
CC ../../extmod/modopenamp_remoteproc.c
CC ../../extmod/modopenamp_remoteproc_store.c
CC ../../extmod/modos.c
CC ../../extmod/modplatform.c
CC ../../extmod/modrandom.c
CC ../../extmod/modre.c
CC ../../extmod/modselect.c
CC ../../extmod/modsocket.c
CC ../../extmod/modtls_axtls.c
CC ../../extmod/modtls_mbedtls.c
CC ../../extmod/mbedtls/mbedtls_alt.c
CC ../../extmod/modtime.c
CC ../../extmod/moductypes.c
CC ../../extmod/modvfs.c
CC ../../extmod/modwebrepl.c
CC ../../extmod/modwebsocket.c
CC ../../extmod/network_cyw43.c
CC ../../extmod/network_esp_hosted.c
CC ../../extmod/network_lwip.c
CC ../../extmod/network_ninaw10.c
CC ../../extmod/network_ppp_lwip.c
CC ../../extmod/network_usbd_ncm.c
CC ../../extmod/network_wiznet5k.c
CC ../../extmod/os_dupterm.c
CC ../../extmod/vfs.c
CC ../../extmod/vfs_blockdev.c
CC ../../extmod/vfs_fat.c
CC ../../extmod/vfs_fat_diskio.c
CC ../../extmod/vfs_fat_file.c
CC ../../extmod/vfs_lfs.c
CC ../../extmod/vfs_rom.c
CC ../../extmod/vfs_rom_file.c
CC ../../extmod/vfs_posix.c
CC ../../extmod/vfs_posix_file.c
CC ../../extmod/vfs_reader.c
CC ../../extmod/virtpin.c
CC ../../shared/libc/abort_.c
CC ../../shared/libc/printf.c
CC ../../lib/oofatfs/ff.c
CC ../../lib/oofatfs/ffunicode.c
CC ../../lib/littlefs/lfs1.c
CC ../../lib/littlefs/lfs2.c
CC ../../lib/littlefs/lfs1_util.c
CC ../../lib/littlefs/lfs2_util.c
CC ../../lib/mbedtls_errors/mp_mbedtls_errors.c
CC ../../lib/mbedtls/library/aes.c
CC ../../lib/mbedtls/library/aesni.c
CC ../../lib/mbedtls/library/asn1parse.c
CC ../../lib/mbedtls/library/asn1write.c
CC ../../lib/mbedtls/library/base64.c
CC ../../lib/mbedtls/library/bignum_core.c
CC ../../lib/mbedtls/library/bignum_mod.c
CC ../../lib/mbedtls/library/bignum_mod_raw.c
CC ../../lib/mbedtls/library/bignum.c
CC ../../lib/mbedtls/library/camellia.c
CC ../../lib/mbedtls/library/ccm.c
CC ../../lib/mbedtls/library/chacha20.c
CC ../../lib/mbedtls/library/chachapoly.c
CC ../../lib/mbedtls/library/cipher.c
CC ../../lib/mbedtls/library/cipher_wrap.c
CC ../../lib/mbedtls/library/nist_kw.c
CC ../../lib/mbedtls/library/aria.c
CC ../../lib/mbedtls/library/cmac.c
CC ../../lib/mbedtls/library/constant_time.c
CC ../../lib/mbedtls/library/mps_reader.c
CC ../../lib/mbedtls/library/mps_trace.c
CC ../../lib/mbedtls/library/ctr_drbg.c
CC ../../lib/mbedtls/library/debug.c
CC ../../lib/mbedtls/library/des.c
CC ../../lib/mbedtls/library/dhm.c
CC ../../lib/mbedtls/library/ecdh.c
CC ../../lib/mbedtls/library/ecdsa.c
CC ../../lib/mbedtls/library/ecjpake.c
CC ../../lib/mbedtls/library/ecp.c
CC ../../lib/mbedtls/library/ecp_curves.c
CC ../../lib/mbedtls/library/entropy.c
CC ../../lib/mbedtls/library/entropy_poll.c
CC ../../lib/mbedtls/library/gcm.c
CC ../../lib/mbedtls/library/hmac_drbg.c
CC ../../lib/mbedtls/library/md5.c
CC ../../lib/mbedtls/library/md.c
CC ../../lib/mbedtls/library/oid.c
CC ../../lib/mbedtls/library/padlock.c
CC ../../lib/mbedtls/library/pem.c
CC ../../lib/mbedtls/library/pk.c
CC ../../lib/mbedtls/library/pkcs12.c
CC ../../lib/mbedtls/library/pkcs5.c
CC ../../lib/mbedtls/library/pkparse.c
CC ../../lib/mbedtls/library/pk_ecc.c
CC ../../lib/mbedtls/library/pk_wrap.c
CC ../../lib/mbedtls/library/pkwrite.c
CC ../../lib/mbedtls/library/platform.c
CC ../../lib/mbedtls/library/platform_util.c
CC ../../lib/mbedtls/library/poly1305.c
CC ../../lib/mbedtls/library/ripemd160.c
CC ../../lib/mbedtls/library/rsa.c
CC ../../lib/mbedtls/library/rsa_alt_helpers.c
CC ../../lib/mbedtls/library/sha1.c
CC ../../lib/mbedtls/library/sha256.c
CC ../../lib/mbedtls/library/sha512.c
CC ../../lib/mbedtls/library/ssl_cache.c
CC ../../lib/mbedtls/library/ssl_ciphersuites.c
CC ../../lib/mbedtls/library/ssl_client.c
CC ../../lib/mbedtls/library/ssl_cookie.c
CC ../../lib/mbedtls/library/ssl_debug_helpers_generated.c
CC ../../lib/mbedtls/library/ssl_msg.c
CC ../../lib/mbedtls/library/ssl_ticket.c
CC ../../lib/mbedtls/library/ssl_tls.c
CC ../../lib/mbedtls/library/ssl_tls12_client.c
CC ../../lib/mbedtls/library/ssl_tls12_server.c
CC ../../lib/mbedtls/library/timing.c
CC ../../lib/mbedtls/library/x509.c
CC ../../lib/mbedtls/library/x509_create.c
CC ../../lib/mbedtls/library/x509_crl.c
CC ../../lib/mbedtls/library/x509_crt.c
CC ../../lib/mbedtls/library/x509_csr.c
CC ../../lib/mbedtls/library/x509write_crt.c
CC ../../lib/mbedtls/library/x509write_csr.c
CC ../../lib/berkeley-db-1.xx/btree/bt_close.c
CC ../../lib/berkeley-db-1.xx/btree/bt_conv.c
CC ../../lib/berkeley-db-1.xx/btree/bt_debug.c
CC ../../lib/berkeley-db-1.xx/btree/bt_delete.c
CC ../../lib/berkeley-db-1.xx/btree/bt_get.c
CC ../../lib/berkeley-db-1.xx/btree/bt_open.c
CC ../../lib/berkeley-db-1.xx/btree/bt_overflow.c
CC ../../lib/berkeley-db-1.xx/btree/bt_page.c
CC ../../lib/berkeley-db-1.xx/btree/bt_put.c
CC ../../lib/berkeley-db-1.xx/btree/bt_search.c
CC ../../lib/berkeley-db-1.xx/btree/bt_seq.c
CC ../../lib/berkeley-db-1.xx/btree/bt_split.c
CC ../../lib/berkeley-db-1.xx/btree/bt_utils.c
CC ../../lib/berkeley-db-1.xx/mpool/mpool.c
CC main.c
CC gccollect.c
CC unix_mphal.c
CC mpthreadport.c
CC input.c
CC alloc.c
CC fatfs_port.c
CC mpbthciport.c
CC mpbtstackport_common.c
CC mpbtstackport_h4.c
CC mpbtstackport_usb.c
CC mpnimbleport.c
CC modtermios.c
CC modsocket.c
CC modffi.c
CC modjni.c
CC ../../shared/runtime/gchelper_generic.c
CC ../../shared/runtime/pyexec.c
CC ../../shared/timeutils/timeutils.c
CC ../../shared/readline/readline.c
CC build-settrace/frozen_content.c
LINK build-settrace/micropython
   text	   data	    bss	    dec	    hex	filename
 781939	  80392	  10608	 872939	  d51eb	build-settrace/micropython
$ /home/nico/pico-toolchain/micropython/ports/unix/build-settrace/micropython -c import sys; print(sys.implementation)
(name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')
Built: (name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')

== Building the MicroPython Unix port (the lwIP host build, the patched modlwip over loopback lwIP)
$ make -j4 VARIANT=standard VARIANT_DIR=/home/nico/pico-toolchain/build_overrides/unix_lwip_host_variant BUILD=build-lwip MICROPY_PY_LWIP=1 MICROPY_PY_LWIP_LOOPBACK=1 MICROPY_PY_SOCKET=0   (cwd=/home/nico/pico-toolchain/micropython/ports/unix)
Use make V=1 or set BUILD_VERBOSE in your environment to increase build verbosity.
mkdir -p build-lwip/genhdr
mkdir -p build-lwip//home/nico/pico-toolchain/build_overrides/unix_lwip_host_variant/
mkdir -p build-lwip/extmod/
mkdir -p build-lwip/extmod/mbedtls/
mkdir -p build-lwip/lib/berkeley-db-1.xx/btree/
mkdir -p build-lwip/lib/berkeley-db-1.xx/mpool/
mkdir -p build-lwip/lib/littlefs/
mkdir -p build-lwip/lib/lwip/src/apps/mdns/
mkdir -p build-lwip/lib/lwip/src/core/
mkdir -p build-lwip/lib/lwip/src/core/ipv4/
mkdir -p build-lwip/lib/lwip/src/core/ipv6/
mkdir -p build-lwip/lib/lwip/src/netif/
mkdir -p build-lwip/lib/lwip/src/netif/ppp/
mkdir -p build-lwip/lib/lwip/src/netif/ppp/polarssl/
mkdir -p build-lwip/lib/mbedtls/library/
mkdir -p build-lwip/lib/mbedtls_errors/
mkdir -p build-lwip/lib/oofatfs/
mkdir -p build-lwip/py/
mkdir -p build-lwip/shared/libc/
mkdir -p build-lwip/shared/netutils/
mkdir -p build-lwip/shared/readline/
mkdir -p build-lwip/shared/runtime/
mkdir -p build-lwip/shared/timeutils/
GEN build-lwip/genhdr/mpversion.h
GEN build-lwip/genhdr/qstr.i.last
GEN build-lwip/genhdr/qstr.split
GEN build-lwip/genhdr/moduledefs.split
GEN build-lwip/genhdr/root_pointers.split
GEN build-lwip/genhdr/compressed.split
GEN build-lwip/genhdr/root_pointers.collected
GEN build-lwip/genhdr/moduledefs.collected
GEN build-lwip/genhdr/compressed.collected
GEN build-lwip/genhdr/qstrdefs.collected.h
Root pointer registrations updated
Module registrations updated
Compressed data updated
GEN build-lwip/genhdr/root_pointers.h
QSTR updated
GEN build-lwip/genhdr/moduledefs.h
GEN build-lwip/genhdr/compressed.data.h
GEN build-lwip/genhdr/qstrdefs.generated.h
CC ../../py/mpstate.c
CC ../../py/nlr.c
CC ../../py/nlrx86.c
CC ../../py/nlrx64.c
CC ../../py/nlrthumb.c
CC ../../py/nlraarch64.c
CC ../../py/nlrmips.c
CC ../../py/nlrpowerpc.c
CC ../../py/nlrxtensa.c
CC ../../py/nlrrv32.c
CC ../../py/nlrrv64.c
CC ../../py/nlrloong64.c
CC ../../py/nlrsetjmp.c
CC ../../py/malloc.c
CC ../../py/gc.c
CC ../../py/pystack.c
CC ../../py/qstr.c
CC ../../py/vstr.c
CC ../../py/mpprint.c
CC ../../py/unicode.c
CC ../../py/mpz.c
CC ../../py/reader.c
CC ../../py/lexer.c
CC ../../py/parse.c
CC ../../py/scope.c
CC ../../py/compile.c
CC ../../py/emitcommon.c
CC ../../py/emitbc.c
CC ../../py/asmbase.c
CC ../../py/asmx64.c
CC ../../py/emitnx64.c
CC ../../py/asmx86.c
CC ../../py/emitnx86.c
CC ../../py/asmthumb.c
CC ../../py/emitnthumb.c
CC ../../py/emitinlinethumb.c
CC ../../py/asmarm.c
CC ../../py/emitnarm.c
CC ../../py/asmxtensa.c
CC ../../py/emitnxtensa.c
CC ../../py/emitinlinextensa.c
CC ../../py/emitnxtensawin.c
CC ../../py/asmrv32.c
CC ../../py/emitnrv32.c
CC ../../py/emitinlinerv32.c
CC ../../py/emitndebug.c
CC ../../py/formatfloat.c
CC ../../py/parsenumbase.c
CC ../../py/parsenum.c
CC ../../py/emitglue.c
CC ../../py/persistentcode.c
CC ../../py/runtime.c
CC ../../py/runtime_utils.c
CC ../../py/scheduler.c
CC ../../py/nativeglue.c
CC ../../py/pairheap.c
CC ../../py/ringbuf.c
CC ../../py/cstack.c
CC ../../py/stackctrl.c
CC ../../py/argcheck.c
CC ../../py/warning.c
CC ../../py/profile.c
CC ../../py/map.c
CC ../../py/obj.c
CC ../../py/objarray.c
CC ../../py/objattrtuple.c
CC ../../py/objbool.c
CC ../../py/objboundmeth.c
CC ../../py/objcell.c
CC ../../py/objclosure.c
CC ../../py/objcode.c
CC ../../py/objcomplex.c
CC ../../py/objdeque.c
CC ../../py/objdict.c
CC ../../py/objenumerate.c
CC ../../py/objexcept.c
CC ../../py/objfilter.c
CC ../../py/objfloat.c
CC ../../py/objfun.c
CC ../../py/objgenerator.c
CC ../../py/objgetitemiter.c
CC ../../py/objint.c
CC ../../py/objint_longlong.c
CC ../../py/objint_mpz.c
CC ../../py/objlist.c
CC ../../py/objmap.c
CC ../../py/objmodule.c
CC ../../py/objobject.c
CC ../../py/objpolyiter.c
CC ../../py/objproperty.c
CC ../../py/objnone.c
CC ../../py/objnamedtuple.c
CC ../../py/objrange.c
CC ../../py/objreversed.c
CC ../../py/objringio.c
CC ../../py/objset.c
CC ../../py/objsingleton.c
CC ../../py/objslice.c
CC ../../py/objstr.c
CC ../../py/objstrunicode.c
CC ../../py/objstringio.c
CC ../../py/objtemplate.c
CC ../../py/objtuple.c
CC ../../py/objtype.c
CC ../../py/objzip.c
CC ../../py/opmethods.c
CC ../../py/sequence.c
CC ../../py/stream.c
CC ../../py/binary.c
CC ../../py/builtinimport.c
CC ../../py/builtinevex.c
CC ../../py/builtinhelp.c
CC ../../py/modarray.c
CC ../../py/modbuiltins.c
CC ../../py/modcollections.c
CC ../../py/modgc.c
CC ../../py/modio.c
CC ../../py/modmath.c
CC ../../py/modcmath.c
CC ../../py/modmicropython.c
CC ../../py/modstring.c
CC ../../py/modstruct.c
CC ../../py/modsys.c
CC ../../py/moderrno.c
CC ../../py/modthread.c
CC ../../py/modweakref.c
CC ../../py/vm.c
CC ../../py/bc.c
CC ../../py/showbc.c
CC ../../py/repl.c
CC ../../py/smallint.c
CC ../../py/frozenmod.c
CC ../../extmod/machine_adc.c
CC ../../extmod/machine_adc_block.c
CC ../../extmod/machine_bitstream.c
CC ../../extmod/machine_can.c
CC ../../extmod/machine_i2c.c
CC ../../extmod/machine_i2c_target.c
CC ../../extmod/machine_i2s.c
CC ../../extmod/machine_mem.c
MPY argparse.py
MPY requests/__init__.py
MPY mip/__init__.py
MPY mip/__main__.py
MPY ssl.py
MPY asyncio/__init__.py
MPY asyncio/core.py
MPY asyncio/event.py
MPY asyncio/funcs.py
MPY asyncio/lock.py
MPY asyncio/stream.py
MPY uasyncio.py
GEN build-lwip/frozen_content.c
CC ../../extmod/machine_pinbase.c
CC ../../extmod/machine_pulse.c
CC ../../extmod/machine_pwm.c
CC ../../extmod/machine_signal.c
CC ../../extmod/machine_spi.c
CC ../../extmod/machine_timer.c
CC ../../extmod/machine_uart.c
CC ../../extmod/machine_usb_device.c
CC ../../extmod/machine_wdt.c
CC ../../extmod/modasyncio.c
CC ../../extmod/modbinascii.c
CC ../../extmod/modbluetooth.c
CC ../../extmod/modbtree.c
CC ../../extmod/modcryptolib.c
CC ../../extmod/moddeflate.c
CC ../../extmod/modframebuf.c
CC ../../extmod/modhashlib.c
CC ../../extmod/modheapq.c
CC ../../extmod/modjson.c
CC /home/nico/pico-toolchain/build_overrides/unix_lwip_host_variant/src/extmod/modlwip.c
CC ../../extmod/modmachine.c
CC ../../extmod/modmarshal.c
CC ../../extmod/modnetwork.c
CC ../../extmod/modonewire.c
CC ../../extmod/modopenamp.c
CC ../../extmod/modopenamp_remoteproc.c
CC ../../extmod/modopenamp_remoteproc_store.c
CC ../../extmod/modos.c
CC ../../extmod/modplatform.c
CC ../../extmod/modrandom.c
CC ../../extmod/modre.c
CC ../../extmod/modselect.c
CC ../../extmod/modsocket.c
CC ../../extmod/modtls_axtls.c
CC ../../extmod/modtls_mbedtls.c
CC ../../extmod/mbedtls/mbedtls_alt.c
CC ../../extmod/modtime.c
CC ../../extmod/moductypes.c
CC ../../extmod/modvfs.c
CC ../../extmod/modwebrepl.c
CC ../../extmod/modwebsocket.c
CC ../../extmod/network_cyw43.c
CC ../../extmod/network_esp_hosted.c
CC ../../extmod/network_lwip.c
CC ../../extmod/network_ninaw10.c
CC ../../extmod/network_ppp_lwip.c
CC ../../extmod/network_usbd_ncm.c
CC ../../extmod/network_wiznet5k.c
CC ../../extmod/os_dupterm.c
CC ../../extmod/vfs.c
CC ../../extmod/vfs_blockdev.c
CC ../../extmod/vfs_fat.c
CC ../../extmod/vfs_fat_diskio.c
CC ../../extmod/vfs_fat_file.c
CC ../../extmod/vfs_lfs.c
CC ../../extmod/vfs_rom.c
CC ../../extmod/vfs_rom_file.c
CC ../../extmod/vfs_posix.c
CC ../../extmod/vfs_posix_file.c
CC ../../extmod/vfs_reader.c
CC ../../extmod/virtpin.c
CC ../../shared/libc/abort_.c
CC ../../shared/libc/printf.c
CC ../../lib/oofatfs/ff.c
CC ../../lib/oofatfs/ffunicode.c
CC ../../lib/littlefs/lfs1.c
CC ../../lib/littlefs/lfs1_util.c
CC ../../lib/littlefs/lfs2.c
CC ../../lib/littlefs/lfs2_util.c
CC ../../lib/mbedtls_errors/mp_mbedtls_errors.c
CC ../../lib/mbedtls/library/aes.c
CC ../../lib/mbedtls/library/aesni.c
CC ../../lib/mbedtls/library/asn1parse.c
CC ../../lib/mbedtls/library/asn1write.c
CC ../../lib/mbedtls/library/base64.c
CC ../../lib/mbedtls/library/bignum_core.c
CC ../../lib/mbedtls/library/bignum_mod.c
CC ../../lib/mbedtls/library/bignum_mod_raw.c
CC ../../lib/mbedtls/library/bignum.c
CC ../../lib/mbedtls/library/camellia.c
CC ../../lib/mbedtls/library/ccm.c
CC ../../lib/mbedtls/library/chacha20.c
CC ../../lib/mbedtls/library/chachapoly.c
CC ../../lib/mbedtls/library/cipher.c
CC ../../lib/mbedtls/library/cipher_wrap.c
CC ../../lib/mbedtls/library/nist_kw.c
CC ../../lib/mbedtls/library/aria.c
CC ../../lib/mbedtls/library/cmac.c
CC ../../lib/mbedtls/library/constant_time.c
CC ../../lib/mbedtls/library/mps_reader.c
CC ../../lib/mbedtls/library/mps_trace.c
CC ../../lib/mbedtls/library/ctr_drbg.c
CC ../../lib/mbedtls/library/debug.c
CC ../../lib/mbedtls/library/des.c
CC ../../lib/mbedtls/library/dhm.c
CC ../../lib/mbedtls/library/ecdh.c
CC ../../lib/mbedtls/library/ecdsa.c
CC ../../lib/mbedtls/library/ecjpake.c
CC ../../lib/mbedtls/library/ecp.c
CC ../../lib/mbedtls/library/ecp_curves.c
CC ../../lib/mbedtls/library/entropy.c
CC ../../lib/mbedtls/library/entropy_poll.c
CC ../../lib/mbedtls/library/gcm.c
CC ../../lib/mbedtls/library/hmac_drbg.c
CC ../../lib/mbedtls/library/md5.c
CC ../../lib/mbedtls/library/md.c
CC ../../lib/mbedtls/library/oid.c
CC ../../lib/mbedtls/library/padlock.c
CC ../../lib/mbedtls/library/pem.c
CC ../../lib/mbedtls/library/pk.c
CC ../../lib/mbedtls/library/pkcs12.c
CC ../../lib/mbedtls/library/pkcs5.c
CC ../../lib/mbedtls/library/pkparse.c
CC ../../lib/mbedtls/library/pk_ecc.c
CC ../../lib/mbedtls/library/pk_wrap.c
CC ../../lib/mbedtls/library/pkwrite.c
CC ../../lib/mbedtls/library/platform.c
CC ../../lib/mbedtls/library/platform_util.c
CC ../../lib/mbedtls/library/poly1305.c
CC ../../lib/mbedtls/library/ripemd160.c
CC ../../lib/mbedtls/library/rsa.c
CC ../../lib/mbedtls/library/rsa_alt_helpers.c
CC ../../lib/mbedtls/library/sha1.c
CC ../../lib/mbedtls/library/sha256.c
CC ../../lib/mbedtls/library/sha512.c
CC ../../lib/mbedtls/library/ssl_cache.c
CC ../../lib/mbedtls/library/ssl_ciphersuites.c
CC ../../lib/mbedtls/library/ssl_client.c
CC ../../lib/mbedtls/library/ssl_cookie.c
CC ../../lib/mbedtls/library/ssl_debug_helpers_generated.c
CC ../../lib/mbedtls/library/ssl_msg.c
CC ../../lib/mbedtls/library/ssl_ticket.c
CC ../../lib/mbedtls/library/ssl_tls.c
CC ../../lib/mbedtls/library/ssl_tls12_client.c
CC ../../lib/mbedtls/library/ssl_tls12_server.c
CC ../../lib/mbedtls/library/timing.c
CC ../../lib/mbedtls/library/x509.c
CC ../../lib/mbedtls/library/x509_create.c
CC ../../lib/mbedtls/library/x509_crl.c
CC ../../lib/mbedtls/library/x509_crt.c
CC ../../lib/mbedtls/library/x509_csr.c
CC ../../lib/mbedtls/library/x509write_crt.c
CC ../../lib/mbedtls/library/x509write_csr.c
CC ../../shared/netutils/netutils.c
CC ../../lib/lwip/src/apps/mdns/mdns.c
CC ../../lib/lwip/src/apps/mdns/mdns_domain.c
CC ../../lib/lwip/src/apps/mdns/mdns_out.c
CC ../../lib/lwip/src/core/def.c
CC ../../lib/lwip/src/core/dns.c
CC ../../lib/lwip/src/core/inet_chksum.c
CC ../../lib/lwip/src/core/init.c
CC ../../lib/lwip/src/core/ip.c
CC ../../lib/lwip/src/core/mem.c
CC ../../lib/lwip/src/core/memp.c
CC ../../lib/lwip/src/core/netif.c
CC ../../lib/lwip/src/core/pbuf.c
CC ../../lib/lwip/src/core/raw.c
CC ../../lib/lwip/src/core/stats.c
CC ../../lib/lwip/src/core/sys.c
CC ../../lib/lwip/src/core/tcp.c
CC ../../lib/lwip/src/core/tcp_in.c
CC ../../lib/lwip/src/core/tcp_out.c
CC ../../lib/lwip/src/core/timeouts.c
CC ../../lib/lwip/src/core/udp.c
CC ../../lib/lwip/src/core/ipv4/acd.c
CC ../../lib/lwip/src/core/ipv4/autoip.c
CC ../../lib/lwip/src/core/ipv4/dhcp.c
CC ../../lib/lwip/src/core/ipv4/etharp.c
CC ../../lib/lwip/src/core/ipv4/icmp.c
CC ../../lib/lwip/src/core/ipv4/igmp.c
CC ../../lib/lwip/src/core/ipv4/ip4_addr.c
CC ../../lib/lwip/src/core/ipv4/ip4.c
CC ../../lib/lwip/src/core/ipv4/ip4_frag.c
CC ../../lib/lwip/src/core/ipv6/dhcp6.c
CC ../../lib/lwip/src/core/ipv6/ethip6.c
CC ../../lib/lwip/src/core/ipv6/icmp6.c
CC ../../lib/lwip/src/core/ipv6/inet6.c
CC ../../lib/lwip/src/core/ipv6/ip6_addr.c
CC ../../lib/lwip/src/core/ipv6/ip6.c
CC ../../lib/lwip/src/core/ipv6/ip6_frag.c
CC ../../lib/lwip/src/core/ipv6/mld6.c
CC ../../lib/lwip/src/core/ipv6/nd6.c
CC ../../lib/lwip/src/netif/ethernet.c
CC ../../lib/lwip/src/netif/ppp/auth.c
CC ../../lib/lwip/src/netif/ppp/ccp.c
CC ../../lib/lwip/src/netif/ppp/chap-md5.c
CC ../../lib/lwip/src/netif/ppp/chap_ms.c
CC ../../lib/lwip/src/netif/ppp/chap-new.c
CC ../../lib/lwip/src/netif/ppp/demand.c
CC ../../lib/lwip/src/netif/ppp/eap.c
CC ../../lib/lwip/src/netif/ppp/ecp.c
CC ../../lib/lwip/src/netif/ppp/eui64.c
CC ../../lib/lwip/src/netif/ppp/fsm.c
CC ../../lib/lwip/src/netif/ppp/ipcp.c
CC ../../lib/lwip/src/netif/ppp/ipv6cp.c
CC ../../lib/lwip/src/netif/ppp/lcp.c
CC ../../lib/lwip/src/netif/ppp/magic.c
CC ../../lib/lwip/src/netif/ppp/mppe.c
CC ../../lib/lwip/src/netif/ppp/multilink.c
CC ../../lib/lwip/src/netif/ppp/polarssl/md5.c
CC ../../lib/lwip/src/netif/ppp/pppapi.c
CC ../../lib/lwip/src/netif/ppp/ppp.c
CC ../../lib/lwip/src/netif/ppp/pppcrypt.c
CC ../../lib/lwip/src/netif/ppp/pppoe.c
CC ../../lib/lwip/src/netif/ppp/pppol2tp.c
CC ../../lib/lwip/src/netif/ppp/pppos.c
CC ../../lib/lwip/src/netif/ppp/upap.c
CC ../../lib/lwip/src/netif/ppp/utils.c
CC ../../lib/lwip/src/netif/ppp/vj.c
CC ../../lib/berkeley-db-1.xx/btree/bt_close.c
CC ../../lib/berkeley-db-1.xx/btree/bt_conv.c
CC ../../lib/berkeley-db-1.xx/btree/bt_debug.c
CC ../../lib/berkeley-db-1.xx/btree/bt_delete.c
CC ../../lib/berkeley-db-1.xx/btree/bt_get.c
CC ../../lib/berkeley-db-1.xx/btree/bt_open.c
CC ../../lib/berkeley-db-1.xx/btree/bt_overflow.c
CC ../../lib/berkeley-db-1.xx/btree/bt_page.c
CC ../../lib/berkeley-db-1.xx/btree/bt_put.c
CC ../../lib/berkeley-db-1.xx/btree/bt_search.c
CC ../../lib/berkeley-db-1.xx/btree/bt_seq.c
CC ../../lib/berkeley-db-1.xx/btree/bt_split.c
CC ../../lib/berkeley-db-1.xx/btree/bt_utils.c
CC ../../lib/berkeley-db-1.xx/mpool/mpool.c
CC main.c
CC gccollect.c
CC unix_mphal.c
CC mpthreadport.c
CC input.c
CC alloc.c
CC fatfs_port.c
CC mpbthciport.c
CC mpbtstackport_common.c
CC mpbtstackport_h4.c
CC mpbtstackport_usb.c
CC mpnimbleport.c
CC modtermios.c
CC modsocket.c
CC modffi.c
CC modjni.c
CC /home/nico/pico-toolchain/build_overrides/unix_lwip_host_variant/lwip_host_port.c
CC ../../shared/runtime/gchelper_generic.c
CC ../../shared/runtime/pyexec.c
CC ../../shared/timeutils/timeutils.c
CC ../../shared/readline/readline.c
CC build-lwip/frozen_content.c
LINK build-lwip/micropython
   text	   data	    bss	    dec	    hex	filename
 870840	  66996	  49072	 986908	  f0f1c	build-lwip/micropython
$ /home/nico/pico-toolchain/micropython/ports/unix/build-lwip/micropython -c import sys; print(sys.implementation)
(name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')
Built: (name='micropython', version=(1, 29, 0, ''), _machine='linux [GCC 14.2.0] version', _mpy=774, _build='standard', _thread='unsafe')

== All verification checks passed
  1-3. mpy-cross built and cross-compiled the verification test file standalone: /home/nico/pico-toolchain/micropython/mpy-cross/build/mpy-cross
  4-5. Unix port built with the test file frozen in, and the frozen module ran with the expected result
  6. RPI_PICO_W firmware built with the same test file frozen in (build-only, zero errors/warnings)
  7. Frozen-bytecode verification build artifacts cleaned up
  8. Vanilla Unix port rebuilt as the standing test rig: /home/nico/pico-toolchain/micropython/ports/unix/build-standard/micropython
     The settrace build flavour for --coverage and the lwIP host build flavour, each proven post-build: /home/nico/pico-toolchain/micropython/ports/unix/build-settrace/micropython, /home/nico/pico-toolchain/micropython/ports/unix/build-lwip/micropython
$ git rev-parse HEAD   (cwd=/home/nico/pico-toolchain/micropython)
0fd6c573ea815774668bbb16b8e197c8822368b2
$ arm-none-eabi-gcc --version
arm-none-eabi-gcc (15:14.2.rel1-1) 14.2.1 20241119
Copyright (C) 2024 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

$ gcc --version
gcc (Debian 14.2.0-19) 14.2.0
Copyright (C) 2024 Free Software Foundation, Inc.
This is free software; see the source for copying conditions.  There is NO
warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.


== no node/node-record.json in /home/nico/pico-toolchain - Node trees kept until the next Node install records the one in use

== Installing Python project dependencies (uv sync)
$ uv sync   (cwd=/home/nico/programming/sensors-bench)
warning: `VIRTUAL_ENV=/home/nico/.cache/uv/environments-v2/setup-toolchain-39b1f08291146203` does not match the project environment path `.venv` and will be ignored; use `--active` to target the active environment instead
Resolved 22 packages in 3ms
Audited 20 packages in 0.60ms
$ curl -fsSL --max-time 60 https://nodejs.org/dist/latest-v24.x/SHASUMS256.txt
b3d0f7cc30d28e44748f84ddb24c97a8735927440faeffc96e34454914167a79  node-v24.22.2-aix-ppc64.tar.gz
f08a17daf9be2671801724a9fe91b8e43d5800d610c61909b3f68fd2e983ad53  node-v24.22.2-arm64.msi
aa9549349e47dffaa42dcf95d6e06ade8c4bdafc980979883b88767670df385a  node-v24.22.2-darwin-arm64.tar.gz
1f5ac075be50bed4780ea3be19a007fda95ea4d527d28d76d0b91de47d915115  node-v24.22.2-darwin-arm64.tar.xz
d5e336d588c45be0c37dbd52cc29895593009ca4997a77a1fd02815131ed0e52  node-v24.22.2-darwin-x64.tar.gz
6965578fd823e72c1b5387f5ab84cb25368f886e02eb8779e6f0fce6b91c27b7  node-v24.22.2-darwin-x64.tar.xz
c5cc7d27906f5b22405a24726a05b9a20c728360225aebed284836c4ae315af5  node-v24.22.2-headers.tar.gz
a0674722441097205363f7f4a79117e54aae164229dc2c92036123a74d26216a  node-v24.22.2-headers.tar.xz
95c264150aceb7f3437a29fd6984924f5f8d1511ea3cbd6c508b83f6c555dae2  node-v24.22.2-linux-arm64.tar.gz
eb187837a2230d4047161ac0be008584e16b46f726e9c9490ee35dc6b17d9ba8  node-v24.22.2-linux-arm64.tar.xz
f5640e1b656b67f600e38cf9c5f278eb428c9498994f5ca41d6406fba060a9f3  node-v24.22.2-linux-ppc64le.tar.gz
5da1205ce97f9718fea9c73cce22b4bf59d7a5d1ed701059104c75ee069ac04b  node-v24.22.2-linux-ppc64le.tar.xz
37286fcb7ef0b431b75ff9dced517fd73b2d4a0e9c460242d4c9798b8b9b4247  node-v24.22.2-linux-s390x.tar.gz
66e2640ca1a4ae8dbaac89b47480e7d6d5d0737960dae29eb5043277f494bd88  node-v24.22.2-linux-s390x.tar.xz
11ebd16c8d7819c0675211225505273d7aea305a8dd85a9c0aeb1fbec2343320  node-v24.22.2-linux-x64-musl.tar.gz
d1601d1defdbb0f02963c89bd979e858aa97f0a3d08a55a1eeb4ddd2b8fa374a  node-v24.22.2-linux-x64-musl.tar.xz
361718c444e49af2ca5a110c83ba6a8901143f23ab285ebbef0341f391f482a9  node-v24.22.2-linux-x64.tar.gz
48cc0e21e048790e54c0cf5749c2725005313d652651c40b7a21feb9697aaf75  node-v24.22.2-linux-x64.tar.xz
e975e566b13aaa6b4b10689d0fea6fd8332b43a1474b9f0c970242e0c2b99bf9  node-v24.22.2.pkg
b2f5443a34a38d863e87c0f5f80c03630fc16917dfe16f26c1cec44c0b542959  node-v24.22.2.tar.gz
8fe2ec1723bb9f8d0b683907c82708debbeda64af21cb2aa214c4241eed0a061  node-v24.22.2.tar.xz
916c99ce9fa52385219cb5b7477bc751ca5a19c5c5944c78e218ac19dc2cee74  node-v24.22.2-win-arm64.7z
f47968c213105077f64c6510f007632c0ca2574802a0b5067c327c49abe1c468  node-v24.22.2-win-arm64.zip
65bfeb55413899b678432d19f437e866a05f7756ef4c7f629ea731fa35aa52ba  node-v24.22.2-win-x64.7z
ca1bff5d8ead13c9f2ea404a176db46bd430704d5b5113734049fa365e7799e2  node-v24.22.2-win-x64.zip
9231bf64d19bef391dd5ee8af65411d3799c3c44a842d2320849cc1da60b6b6d  node-v24.22.2-x64.msi
e2d6e75a0bfe4c176316d7c732eb8def9d94570c759eaeab335473a015abb7ea  win-arm64/node.exe
2c0c3215d59c09d7c136da4949696dae121a299e9bdfc64cd9130a58610af63d  win-arm64/node.lib
fcd9a837f9fb0210f483604aeaf06199eed8308eafefeaf8b750efd862162bae  win-arm64/node_pdb.7z
6207164e574f170f5282c4a9c628428818794fed58c8f073f0f9beef50d71ae5  win-arm64/node_pdb.zip
1c331340fa6cac5e4294725959070a143fa0507195a78ad77eed7943f719aac9  win-x64/node.exe
a0a84aa03917b578d286010b7521837e9ff1136ffb2e4a406c14316c33fd06f7  win-x64/node.lib
a0b4ed194f9a5390f872cb42fdf29ca085686ad25cdf26ea0829751412703269  win-x64/node_pdb.7z
8f305bee61b83fb404c5e38748d038712f2fabbd284d797d9d9598ee0ef35154  win-x64/node_pdb.zip

== Installing Node 24.x (node-v24.22.2-linux-arm64.tar.xz) into /home/nico/pico-toolchain/node
$ curl -fsSL --max-time 600 -o /tmp/tmprh39kdrk/node-v24.22.2-linux-arm64.tar.xz https://nodejs.org/dist/latest-v24.x/node-v24.22.2-linux-arm64.tar.xz
$ tar -xJf /tmp/tmprh39kdrk/node-v24.22.2-linux-arm64.tar.xz -C /home/nico/pico-toolchain/node/.node-v24.22.2-linux-arm64.tar.xz.partial

== Node installed: /home/nico/pico-toolchain/node/node-v24.22.2-linux-arm64/bin
$ /home/nico/pico-toolchain/node/node-v24.22.2-linux-arm64/bin/node --version
v24.22.2

== Node in use: /home/nico/pico-toolchain/node/node-v24.22.2-linux-arm64/bin/node v24.22.2

== Installing website tooling dependencies (npm ci)
$ npm ci   (cwd=/home/nico/programming/sensors-bench)

added 261 packages, and audited 262 packages in 11s

84 packages are looking for funding
  run `npm fund` for details

10 moderate severity vulnerabilities

To address issues that do not require attention, run:
  npm audit fix

To address all issues (including breaking changes), run:
  npm audit fix --force

Run `npm audit` for details.

== Installing the Playwright Chromium build vitest runs against
$ npx playwright install chromium   (cwd=/home/nico/programming/sensors-bench)
$ npx playwright install-deps chromium   (cwd=/home/nico/programming/sensors-bench)
Installing dependencies...
Switching to root user to install dependencies...
Hit:1 http://deb.debian.org/debian trixie InRelease
Hit:2 http://deb.debian.org/debian trixie-updates InRelease
Hit:3 http://deb.debian.org/debian-security trixie-security InRelease
Hit:4 http://archive.raspberrypi.com/debian trixie InRelease
Reading package lists...
Reading package lists...
Building dependency tree...
Reading state information...
libasound2t64 is already the newest version (1.2.14-1+rpt1+deb13u1).
libatk-bridge2.0-0t64 is already the newest version (2.56.2-1+deb13u2).
libatk1.0-0t64 is already the newest version (2.56.2-1+deb13u2).
libatspi2.0-0t64 is already the newest version (2.56.2-1+deb13u2).
libcairo2 is already the newest version (1.18.4-1+rpt1).
libcups2t64 is already the newest version (2.4.10-3+rpt2+deb13u2).
libdbus-1-3 is already the newest version (1.16.2-2).
libdrm2 is already the newest version (2.4.134-3~bpo13+1+rpt1).
libgbm1 is already the newest version (26.2.2-1~bpo13+0~rpt1).
libglib2.0-0t64 is already the newest version (2.84.4-3~deb13u5).
libnspr4 is already the newest version (2:4.36-1).
libpango-1.0-0 is already the newest version (1.56.3-1).
libx11-6 is already the newest version (2:1.8.12-1).
libxcb1 is already the newest version (1.17.0-2+b1).
libxcomposite1 is already the newest version (1:0.4.6-1).
libxdamage1 is already the newest version (1:1.1.6-1+b2).
libxext6 is already the newest version (2:1.3.4-1+b3).
libxfixes3 is already the newest version (1:6.0.0-2+b4).
libxkbcommon0 is already the newest version (1.13.1-1~bpo13+1+rpt1).
libxrandr2 is already the newest version (2:1.5.4-1+b3).
xvfb is already the newest version (2:21.1.16-1.3+rpt1+deb13u4).
fonts-noto-color-emoji is already the newest version (2.051-0+deb13u1).
fonts-unifont is already the newest version (1:15.1.01-1).
libfontconfig1 is already the newest version (2.15.0-2.3).
libfreetype6 is already the newest version (2.13.3+dfsg-1+deb13u1).
xfonts-scalable is already the newest version (1:1.0.3-1.3).
fonts-liberation is already the newest version (1:2.1.5-3).
fonts-ipafont-gothic is already the newest version (00303-23).
fonts-wqy-zenhei is already the newest version (0.9.45-8).
fonts-tlwg-loma-otf is already the newest version (1:0.7.3-1).
fonts-freefont-ttf is already the newest version (20211204+svn4273-2).
The following packages were automatically installed and are no longer required:
  chromium-sandbox libfuse2t64 libqt5x11extras5
Use 'sudo apt autoremove' to remove them.
The following packages will be upgraded:
  libnss3
1 upgraded, 0 newly installed, 0 to remove and 44 not upgraded.
Need to get 1,291 kB of archives.
After this operation, 1,024 B disk space will be freed.
Get:1 http://deb.debian.org/debian-security trixie-security/main arm64 libnss3 arm64 2:3.110-1+deb13u5 [1,291 kB]
apt-listchanges: Reading changelogs...
dpkg-preconfigure: unable to re-open stdin: No such file or directory
Fetched 1,291 kB in 0s (12.6 MB/s)
(Reading database ... 
(Reading database ... 5%
(Reading database ... 10%
(Reading database ... 15%
(Reading database ... 20%
(Reading database ... 25%
(Reading database ... 30%
(Reading database ... 35%
(Reading database ... 40%
(Reading database ... 45%
(Reading database ... 50%
(Reading database ... 55%
(Reading database ... 60%
(Reading database ... 65%
(Reading database ... 70%
(Reading database ... 75%
(Reading database ... 80%
(Reading database ... 85%
(Reading database ... 90%
(Reading database ... 95%
(Reading database ... 100%
(Reading database ... 152669 files and directories currently installed.)
Preparing to unpack .../libnss3_2%3a3.110-1+deb13u5_arm64.deb ...
Unpacking libnss3:arm64 (2:3.110-1+deb13u5) over (2:3.110-1+deb13u4) ...
Setting up libnss3:arm64 (2:3.110-1+deb13u5) ...
Processing triggers for libc-bin (2.41-12+rpt1+deb13u4) ...

== nico is already in the dialout group

== Flash environment ready: /dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66130100f372d34-if00 reachable via scripts/mpremote_connect.sh
$ sudo -k -n /usr/bin/nmcli --version
nmcli tool, version 1.52.1
$ sudo -k -n /usr/sbin/iw --version
iw version 6.9
$ sudo -k -n /usr/sbin/iptables --version
iptables v1.8.11 (nf_tables)
$ sudo -k -n /usr/sbin/tc -V
tc utility, iproute2-6.15.0, libbpf 1.5.0
$ sudo -k -n /usr/bin/tee --version
tee (GNU coreutils) 9.7
Packaged by Debian (9.7-3)
Copyright (C) 2025 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Mike Parker, Richard M. Stallman, and David MacKenzie.
$ sudo -k -n /usr/local/bin/picotool version
picotool v2.3.1 (Linux, GNU-14.2.0, Release)
$ sudo -k -n /usr/bin/timeout --version
timeout (GNU coreutils) 9.7
Packaged by Debian (9.7-3)
Copyright (C) 2025 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Written by Pádraig Brady.
$ sudo -k -n /usr/bin/systemd-run --version
systemd 257 (257.13-1~deb13u1)
+PAM +AUDIT +SELINUX +APPARMOR +IMA +IPE +SMACK +SECCOMP +GCRYPT -GNUTLS +OPENSSL +ACL +BLKID +CURL +ELFUTILS +FIDO2 +IDN2 -IDN +IPTC +KMOD +LIBCRYPTSETUP +LIBCRYPTSETUP_PLUGINS +LIBFDISK +PCRE2 +PWQUALITY +P11KIT +QRENCODE +TPM2 +BZIP2 +LZ4 +XZ +ZLIB +ZSTD +BPF_FRAMEWORK +BTF -XKBCOMMON -UTMP +SYSVINIT +LIBARCHIVE
$ sudo -k -n /usr/bin/systemctl --version
systemd 257 (257.13-1~deb13u1)
+PAM +AUDIT +SELINUX +APPARMOR +IMA +IPE +SMACK +SECCOMP +GCRYPT -GNUTLS +OPENSSL +ACL +BLKID +CURL +ELFUTILS +FIDO2 +IDN2 -IDN +IPTC +KMOD +LIBCRYPTSETUP +LIBCRYPTSETUP_PLUGINS +LIBFDISK +PCRE2 +PWQUALITY +P11KIT +QRENCODE +TPM2 +BZIP2 +LZ4 +XZ +ZLIB +ZSTD +BPF_FRAMEWORK +BTF -XKBCOMMON -UTMP +SYSVINIT +LIBARCHIVE
$ sudo -k -n /home/nico/programming/sensors-bench/.venv/bin/python /home/nico/programming/sensors-bench/tests_hardware/spoof_udp.py --help
usage: spoof_udp.py [-h] --src SRC --dst DST [--sport SPORT] --dport DPORT
                    --payload-hex PAYLOAD_HEX

Sends one hand-built IPv4+UDP datagram from a forged source, for the bench's
off-subnet NTP/DNS spoof attempt (needs root: raw IPPROTO_RAW). Refuses any
--src outside RFC 5737's documentation ranges, so it can only ever forge a
documentation address, never a real host's.

options:
  -h, --help            show this help message and exit
  --src SRC             forged source address (RFC 5737 documentation range
                        only)
  --dst DST             destination address
  --sport SPORT         source UDP port
  --dport DPORT         destination UDP port
  --payload-hex PAYLOAD_HEX
                        UDP payload as hex
$ sudo modprobe br_netfilter
$ sudo sysctl -w net.bridge.bridge-nf-call-iptables=1
net.bridge.bridge-nf-call-iptables = 1
$ sudo tee /etc/modules-load.d/sensors-bench-br-netfilter.conf
br_netfilter
$ sudo chmod 644 /etc/modules-load.d/sensors-bench-br-netfilter.conf
$ sudo tee /etc/sysctl.d/99-sensors-bench-br-netfilter.conf
net.bridge.bridge-nf-call-iptables=1
$ sudo chmod 644 /etc/sysctl.d/99-sensors-bench-br-netfilter.conf

== br_netfilter loaded and net.bridge.bridge-nf-call-iptables=1 set, persisted via /etc/modules-load.d/sensors-bench-br-netfilter.conf, /etc/sysctl.d/99-sensors-bench-br-netfilter.conf
$ nmcli -t -f NAME connection show
br0
br0-eth0
br0-wifi-ap
lo
SensorNode
Wired connection 1
sensors-bench-fa9707

$ nmcli -g connection.interface-name connection show br0-eth0
eth0
$ nmcli -g 802-11-wireless.channel connection show br0-wifi-ap
6
$ ip -o link show eth0
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq master br0 state UP mode DEFAULT group default qlen 1000\    link/ether d8:3a:dd:28:ea:5a brd ff:ff:ff:ff:ff:ff
$ nmcli --escape no -g bridge.mac-address connection show br0
D8:3A:DD:28:EA:5A

build-essential 12.12
cmake 3.31.6-2
gcc-arm-none-eabi 15:14.2.rel1-1
git 1:2.47.3-0+deb13u1
libcap2-bin 1:2.75-10+deb13u1+b3
libffi-dev 3.4.8-2
libnewlib-arm-none-eabi 4.5.0.20241231-1
libstdc++-arm-none-eabi-newlib 15:14.2.rel1-1+29
libusb-1.0-0-dev 2:1.0.28-1
pkg-config 1.8.1-4
== step 2 end rc=0 2026-11-05 08:10:22 851s load 4.17 4.10 2.53
== read-across: GET /status after step 2
SUM status not read: no JSON answer
```
<!-- end step -->

### 1 evidence

<!-- step 1 -->
```
== step 1 start 2026-11-05 07:52:48 1793865168 load 0.18 0.07 0.09
SUM status not read: no JSON answer
Resolved 22 packages in 3ms
Audited 20 packages in 0.67ms
warning: `--no-sync` is a no-op for Python scripts with inline metadata, which always run in isolation
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
ImportError: no module named 'asy_spi_driver'
rc=1
== step 1 end rc=1 2026-11-05 07:53:08 20s load 0.28 0.10 0.10
== read-across: GET /status after step 1
SUM status not read: no JSON answer
```
<!-- end step -->
