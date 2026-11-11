## 1. Board bring-up

- [x] 1.1 Flash stock MicroPython v1.29.0 (`RPI_PICO2_W`); read MAC `98:fe:54:1a:80:d7`.
- [x] 1.2 Join `krys_dom_IoT`; DHCP reservation `.52` (user, Terraform pfsense-router).
- [x] 1.3 DNS: `raspberry-pi-pico-2-wh-02.iot` A + PTR resolve (terraform-configs `iot/pico-2-wh-records`; the override needed `-replace`, the provider cannot rename `host|domain` in place).

## 2. Code and tooling

- [x] 2.1 Chip-aware watchdog scratch base in `lib/supervisor.py`.
- [x] 2.2 `firmware/build.sh` (MPY_TAG/BOARD, per-tag cache) and manifest `$(BOARD_DIR)`.
- [x] 2.3 `firmware/flash.sh` for RP2350 (drive, layout, chip check, PORT guard).
- [x] 2.4 `tools/deploy.sh` PORT guard and config-free frozen probe; mpy-cross 1.29.0.
- [x] 2.5 Build frozen firmware, flash, deploy and run headless on the Pico 2 W.

## 3. Cutover

- [ ] 3.1 krysdom-api `observability` scrape target → `raspberry-pi-pico-2-wh-02.iot:9100`.
- [ ] 3.2 Move the panel from the Pico W to the Pico 2 WH; verify first frame and both keys.
- [ ] 3.3 Verify `up{job="pico-epaper-dashboard"}` = 1 and an hourly refresh `ok`.
