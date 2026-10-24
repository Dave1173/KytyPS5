# Wolverine / KytyPS5-Frank integration review (2026-10-23)

This branch is a **non-destructive staging branch** based on Dave1173/KytyPS5 main. No Frank renderer code has been cherry-picked yet, and no gameplay or build verification has been performed.

## Source baseline

- Upstream candidate: https://github.com/mn3ema/KytyPS5-Frank, branch `frank`, observed at commit `0ae1c573170bff863a569f5507b0a49fcbd6284e`.
- Its README reports playable PPSA03671 v01.001.005 on an RTX 5090 Laptop, with approximately 14–25 FPS in sampled gameplay scenes. Do **not** infer those rates on an RTX 5080 Laptop.
- Current local main: `Dave1173/KytyPS5`, U59 base. Keep the existing `feature/multigame-nvidia-rtx` branch untouched.

## Engineering priorities

1. **Stability first**: investigate Vulkan device loss attributed to out-of-range GPU buffer access when particle shaders `8fb896cb9412ab56` and `4efbcf79c36d8adf` are in flight. Verify descriptor range and effective offsets; don't silently clamp valid game reads.
2. **Synchronization**: profile guest job-thread GPU readback round trips, cache coherency, flush triggers and barriers. Preserve guest-visible ordering. Use counters for wait time and submissions per frame.
3. **Graphics correctness**: investigate remaining texture flicker, user-data and resource-table validation; preserve working bindless texture, sampler and particle fixes.
4. **Pipeline compilation**: investigate long-running VS `d1ea70c7117d4d3a` / PS `85892b3b3d0a61ba` instead of treating a permanent skipped draw as a full fix.
5. **Measured performance**: compare cold/warm shader cache, FPS, 1% lows, device-loss frequency, CPU render thread time, GPU shader time and CPU-GPU sync cost on identical saves.

## Recommended integration sequence

- Obtain a proper fork or a writable copy of Frank with its complete history and submodules.
- Diff the Frank source against this repository's main, map changed files by subsystem, and **port only isolated, understood changes**. Avoid a blind merge of two extensively changed graphics stacks.
- Add a focused test for each correctness fix before any performance experiment.
- Windows Release CI with clang-cl, CMake/Ninja and Vulkan shader validation; then an actual hardware test on an RTX 5080 Laptop.
- No claims of 30/60 FPS, DLSS or frame-generation compatibility until demonstrated.

## Known upstream toggles to use for A/B isolation

`KYTY_HOST_ZONES=0`, `KYTY_SYNC_SKIP=0`, `KYTY_COALESCE_SUBMITS=1`, `KYTY_PARTICLE_SLOT28=0` and `KYTY_FRANK_DEFAULTS=0`. Document each test's configuration.

This file is a technical baseline, not a modified emulator executable.
