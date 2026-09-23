"""Minimal valid media blobs for MinIO uploads (no external assets)."""

from __future__ import annotations

import struct
import zlib


def tiny_jpeg(*, color: tuple[int, int, int] = (120, 160, 200)) -> bytes:
    """1x1 JPEG: known-good greyscale baseline + COM marker with color hint."""
    # Minimal valid 1x1 greyscale JPEG (public-domain snippet).
    base = bytes.fromhex(
        "ffd8ffe000104a46494600010100000100010000"
        "ffdb004300080606070605080707070909080a0c141d0c0b0b0c1912130f141d1a1f1e1d"
        "1a1c1c20242e2720222c231c1c2837292c30313434341f27393d38323c2e333432"
        "ffc0000b080001000101011100"
        "ffc4001f0000010501010101010100000000000000000102030405060708090a0b"
        "ffc400b5100002010303020403050504040000017d010203000411051221314106135161"
        "07227114328191a1082342b1c11552d1f02433627282090a161718191a25262728292a"
        "3435363738393a434445464748494a535455565758595a636465666768696a73747576"
        "7778797a838485868788898a92939495969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6"
        "b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3"
        "f4f5f6f7f8f9faffda0008010100003f007fffdd9"
    )
    r, g, b = color
    comment = f"seed-rgb:{r},{g},{b}".encode()
    com = b"\xff\xfe" + struct.pack(">H", len(comment) + 2) + comment
    return base[:2] + com + base[2:]


def tiny_png(*, rgb: tuple[int, int, int] = (180, 140, 100)) -> bytes:
    """1x1 RGB PNG — preferred for seed photos (guaranteed valid)."""
    r, g, b = rgb
    raw = bytes([0, r, g, b])  # filter none + pixel
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )


def tiny_wav(*, frequency_hz: int = 440, duration_ms: int = 80) -> bytes:
    """Very short mono 8-bit PCM WAV (square wave)."""
    sample_rate = 8000
    num_samples = max(1, sample_rate * duration_ms // 1000)
    half_period = max(1, sample_rate // (2 * max(1, frequency_hz)))
    samples = bytearray()
    for i in range(num_samples):
        samples.append(200 if (i // half_period) % 2 == 0 else 50)

    data = bytes(samples)
    data_size = len(data)
    bits_per_sample = 8
    channels = 1
    block_align = channels * bits_per_sample // 8
    byte_rate = sample_rate * block_align
    riff_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        riff_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + data
