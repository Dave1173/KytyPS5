#!/usr/bin/env python3
"""Apply two experimental Wolverine renderer changes to KytyPS5 ebb180a.
No game files or copyrighted console libraries are part of this script.
"""
from pathlib import Path
import subprocess
import sys

BASE = "ebb180a1d9ddb740598632d417da2f67a25dd318"


def replace_once(contents, before, after, name):
    number = contents.count(before)
    if number != 1:
        raise RuntimeError(f"{name}: expected one matching source fragment, found {number}")
    return contents.replace(before, after, 1)


def edit(root, relative, update):
    path = root / relative
    original = path.read_text(encoding="utf-8")
    changed = update(original)
    if changed == original:
        raise RuntimeError(f"No changes made: {relative}")
    path.write_text(changed, encoding="utf-8", newline="\n")
    print(f"Patched {relative}")


def header(source):
    before = (
        "\tvoid               UnmarkRegionAsGpuModified(uint64_t vaddr, uint64_t size);\n"
        "\tvoid               UntrackMemory(uint64_t vaddr, uint64_t size);"
    )
    after = before.replace(
        "\tvoid               UntrackMemory",
        "\tvoid               TakeGpuPagesForCpu(uint64_t vaddr, uint64_t size);\n"
        "\tvoid               UntrackMemory",
    )
    return replace_once(source, before, after, "memoryTracker.h")


def implementation(source):
    anchor = "void MemoryTracker::UntrackMemory(uint64_t vaddr, uint64_t size) {"
    insert = (
        "void MemoryTracker::TakeGpuPagesForCpu(uint64_t vaddr, uint64_t size) {\n"
        "\tCheckNotInUploadCallback();\n"
        "\tIterate<true>(vaddr, size, [](RegionManager* manager, uint64_t offset, uint64_t bytes) {\n"
        "\t\tstd::scoped_lock lock(manager->lock);\n"
        "\t\tconst auto address = manager->GetCpuAddr() + offset;\n"
        "\t\tmanager->ChangeState<DirtySource::Gpu, false>(address, bytes);\n"
        "\t\tmanager->ChangeState<DirtySource::Cpu, true>(address, bytes);\n"
        "\t});\n"
        "}\n\n"
    )
    return replace_once(source, anchor, insert + anchor, "memoryTracker.cpp")


def buffer_cache(source):
    # Clean-page readback on the GPU thread.
    for ending in ("return;", "return 0;"):
        before = (
            "\tif (m_memory_tracker.IsRegionGpuModified(page_begin, page_end - page_begin) &&\n"
            "\t    !HasGpuDirtyBytes(page_begin, page_end - page_begin)) {\n"
            "\t\tm_memory_tracker.UnmarkRegionAsGpuModified(page_begin, page_end - page_begin);\n"
            "\t\tif (is_write) {\n"
            "\t\t\tm_memory_tracker.MarkRegionAsCpuModified(vaddr, size);\n"
            "\t\t}\n"
            "\t\tstats.SetOutcome(ReadbackStats::Unmarked);\n"
            f"\t\t{ending}\n"
            "\t}"
        )
        after = (
            "\tif (m_memory_tracker.IsRegionGpuModified(page_begin, page_end - page_begin) &&\n"
            "\t    !HasGpuDirtyBytes(page_begin, page_end - page_begin)) {\n"
            "\t\tif (is_write) {\n"
            "\t\t\tm_memory_tracker.TakeGpuPagesForCpu(vaddr, size);\n"
            "\t\t} else {\n"
            "\t\t\tm_memory_tracker.UnmarkRegionAsGpuModified(page_begin, page_end - page_begin);\n"
            "\t\t}\n"
            "\t\tstats.SetOutcome(ReadbackStats::Unmarked);\n"
            f"\t\t{ending}\n"
            "\t}"
        )
        source = replace_once(source, before, after, f"bufferCache clean path {ending}")

    before = (
        "\tm_memory_tracker.UnmarkRegionAsGpuModified(page_begin, page_end - page_begin);\n"
        "\tif (is_write) {\n"
        "\t\tm_memory_tracker.MarkRegionAsCpuModified(vaddr, size);\n"
        "\t}\n"
        "\tm_direct_readbacks++;"
    )
    after = (
        "\tif (is_write) {\n"
        "\t\tm_memory_tracker.TakeGpuPagesForCpu(vaddr, size);\n"
        "\t} else {\n"
        "\t\tm_memory_tracker.UnmarkRegionAsGpuModified(page_begin, page_end - page_begin);\n"
        "\t}\n"
        "\tm_direct_readbacks++;"
    )
    return replace_once(source, before, after, "bufferCache direct readback")


def texture_cache(source):
    start = "void TextureCache::InvalidateMemoryFromGPU(uint64_t address, uint64_t size) {"
    end = "\nbool TextureCache::HasImagesInRegion"
    before, separator, tail = source.partition(start)
    if not separator:
        raise RuntimeError("TextureCache::InvalidateMemoryFromGPU was not found")
    function, separator, after = tail.partition(end)
    if not separator:
        raise RuntimeError("TextureCache::HasImagesInRegion was not found")
    original = (
        "\t\tif (image.info.data.address != address) {\n"
        "\t\t\tcontinue;\n"
        "\t\t}"
    )
    updated = (
        "\t\t// Invalidate byte-overlapping image aliases, not only identical base addresses.\n"
        "\t\tif (image.info.data.Empty() || image.info.data.End() <= address ||\n"
        "\t\t    image.info.data.address >= address + size) {\n"
        "\t\t\tcontinue;\n"
        "\t\t}"
    )
    function = replace_once(function, original, updated, "textureCache overlap")
    return before + start + function + end + after


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: apply_patches.py <KytyPS5 source checkout>")
    root = Path(sys.argv[1]).resolve()
    actual = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != BASE:
        raise RuntimeError(f"Wrong source revision: {actual}; expected {BASE}")
    files = [
        ("src/graphics/host_gpu/memoryTracker.h", header),
        ("src/graphics/host_gpu/memoryTracker.cpp", implementation),
        ("src/graphics/host_gpu/renderer/cache/bufferCache.cpp", buffer_cache),
        ("src/graphics/host_gpu/renderer/cache/textureCache.cpp", texture_cache),
    ]
    # Fail before writing anything if any source anchor is missing.
    changes = []
    for name, updater in files:
        path = root / name
        old = path.read_text(encoding="utf-8")
        new = updater(old)
        if new == old:
            raise RuntimeError(f"Unchanged source: {name}")
        changes.append((path, name, new))
    for path, name, new in changes:
        path.write_text(new, encoding="utf-8", newline="\n")
        print(f"Patched {name}")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    subprocess.run(["git", "-C", str(root), "diff", "--stat"], check=True)
    print("Both source fixes applied. No original emulator binaries were changed.")


if __name__ == "__main__":
    main()
