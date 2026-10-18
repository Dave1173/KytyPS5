# NVIDIA RTX / Streamline integration plan

Status: **design and investigation only**. This branch does not yet enable DLSS or Frame Generation.

## Goals
- Preserve existing Vulkan rendering and game compatibility as the default.
- Add an optional NVIDIA Streamline backend, gated by runtime feature detection.
- Integrate DLSS Super Resolution only after identifying valid source color, depth, exposure, jitter, and motion-vector inputs.
- Integrate DLSS Frame Generation only after verified per-frame motion vectors, depth, HUD-less color, swapchain/present synchronization, and appropriate frame pacing are available.
- Provide graceful fallback when unsupported, including Intel/AMD GPUs or incompatible game render paths.
- Keep game-specific workarounds isolated, not global.

## Prerequisites / technical risks
KytyPS5 uses a Vulkan renderer. NVIDIA Streamline supports Vulkan integration, but SDK headers/DLLs alone do not provide the missing emulator-generated motion vectors and depth semantics. Emulated PS5 graphics may not expose stable per-object motion vectors in a form DLSS expects. Incorrect data can cause severe artifacts and crashes.

NVIDIA Streamline DLSS-G requires correctly tagged depth, motion vectors, and backbuffer, and recommends HUD-less and UI buffers. Hardware-accelerated GPU scheduling must be enabled on Windows. Vulkan optical flow support and queue configuration must be checked. Dynamic Multi Frame Generation is currently D3D12-only in NVIDIA's guide; do not expose that mode for Vulkan without official support.

Do not commit proprietary DLSS binaries. Obtain signed official runtime binaries from NVIDIA's releases as required by their distribution guidance, and verify compatibility and licensing.

## Implementation phases
1. Inspect Vulkan instance/device creation, swapchain present path, frame graph, shaders, depth/motion data, and existing postprocessing.
2. Introduce optional build-time integration and runtime capability checks, **disabled by default**.
3. Implement and validate DLSS Super Resolution using actual renderer data (no fabricated motion vectors).
4. Implement DLSS Frame Generation and Reflex frame pacing only if prerequisites are met, with per-game enable/disable and rollback.
5. Run automated Windows builds, then actual game validation on NVIDIA hardware.

## Validation targets
- Astro Bot: boot, menus, gameplay, UI and water rendering
- Astro's Playroom: boot and gameplay
- Marvel's Wolverine: startup and memory fault regression, graphics and gameplay
- Other games: ensure changes do not regress known-working titles

No claim of successful game boot, working DLSS, frame generation, or performance improvement is made by this planning commit.

## References
- https://github.com/NVIDIA-RTX/Streamline
- https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuide.md
- https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideDLSS_G.md
- https://github.com/NVIDIA-RTX/Streamline/blob/main/docs/ProgrammingGuideManualHooking.md
