Lock Frontend Firmware
===

Status: work in progress as the board is being brought up. Blinks the DBG LED.

Building
===

You'll need a Rust toolchain (cargo, rustc), for example via rustup.

```
$ # Important! Go to the lockfw subdirectory. `firmware` is just a workspace, attempting to build it will fail.
$ cd firmware/lockfw
$ # Install fancy linker frontend for extra stack protection. You only need to
$ do this once.
$ cargo install flip-link
$ cargo build
```

Flashing
===

First, install `elf2uf2-rs`: `cargo install elf2uf2-rs`.

1. Connect the device over USB.
2. Hold down the 'Boot' switch while connecting the board, or reset it while holding down the 'Boot' switch.
3. The device will appear as USB mass storage device.
4. Mount the device:
  a. Linux: `sudo mount /dev/sdX1 /mnt/pendrive -o uid=$(id -u)` if you don't have an automounter
  b. Everything else: should just mount/appear automatically
5. `cd lockfw; cargo run`
6. Unmount/eject the device (Linux: `sudo umount /mnt/pendrive`)
7. The device will reset and run your new firmware.
