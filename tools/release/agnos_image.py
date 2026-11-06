#!/usr/bin/env python3
"""Reconstruct a pinned AGNOS Android-sparse system image on the host, without mounting it."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import lzma
import os
from pathlib import Path
import stat
import struct

HEADER = struct.Struct('<IHHHHIIII')
CHUNK = struct.Struct('<HHII')
MAGIC = 0xED26FF3A
RAW, FILL, DONT_CARE = 0xCAC1, 0xCAC2, 0xCAC3
BLOCK = 1024 * 1024
MAX_RAW_BYTES = 8 * 1024 * 1024 * 1024


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as source:
        for data in iter(lambda: source.read(BLOCK), b''):
            h.update(data)
    return h.hexdigest()


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f'duplicate manifest key: {key}')
        out[key] = value
    return out


def pinned_system(manifest: Path, expected_manifest_sha256: str) -> dict:
    fd = os.open(manifest, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('manifest is not a regular file')
        data = source.read(1024 * 1024 + 1)
    if len(data) > 1024 * 1024 or hashlib.sha256(data).hexdigest() != expected_manifest_sha256:
        raise ValueError('manifest differs from external SHA-256 anchor')
    parts = json.loads(data, object_pairs_hook=unique_pairs)
    systems = [p for p in parts if p.get('name') == 'system']
    if len(systems) != 1 or not systems[0].get('sparse'):
        raise ValueError('exactly one sparse system component required')
    part = systems[0]
    if not isinstance(part.get('size'), int) or not 0 < part['size'] <= MAX_RAW_BYTES:
        raise ValueError('invalid bounded raw image size')
    for key in ('hash', 'hash_raw'):
        value = part.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError(f'invalid {key} SHA-256')
    return part


class HashedInput:
    def __init__(self, stream):
        self.stream = stream
        self.hash = hashlib.sha256()
        self.bytes_read = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.hash.update(data)
        self.bytes_read += len(data)
        return data


def publish_open_file(fd: int, output: Path) -> None:
    """Atomically link the verified open inode, refusing an existing destination."""
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.linkat(fd, ctypes.c_char_p(b''), -100,
                         ctypes.c_char_p(os.fsencode(output)), 0x1000)  # AT_EMPTY_PATH
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(output))


def reconstruct(compressed: Path, output: Path, manifest: Path, expected_manifest_sha256: str) -> dict:
    part = pinned_system(manifest, expected_manifest_sha256)
    if compressed.is_symlink() or not compressed.is_file() or compressed.stat().st_size == 0:
        raise ValueError('missing or non-regular compressed image')
    if output.exists() or output.is_symlink() or output == compressed:
        raise ValueError('output exists or aliases input')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + '.partial')
    if temp.exists() or temp.is_symlink():
        raise ValueError('partial output already exists; reconcile interrupted operation')
    sparse_hash, raw_hash = hashlib.sha256(), hashlib.sha256()
    logical_bytes = 0
    zero = bytes(BLOCK)
    created_temp = False
    try:
        fd = os.open(compressed, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, 'rb') as compressed_stream:
            if not stat.S_ISREG(os.fstat(compressed_stream.fileno()).st_mode):
                raise ValueError('compressed input is not regular')
            compressed_size = os.fstat(compressed_stream.fileno()).st_size
            hashed_input = HashedInput(compressed_stream)
            with lzma.LZMAFile(hashed_input, 'rb') as source, temp.open('xb') as target:
                created_temp = True
                target_inode = (os.fstat(target.fileno()).st_dev, os.fstat(target.fileno()).st_ino)
                def read_exact(length: int) -> bytes:
                    data = source.read(length)
                    if len(data) != length:
                        raise ValueError('truncated sparse image')
                    sparse_hash.update(data)
                    return data

                magic, major, minor, header_size, chunk_header_size, block_size, total_blocks, total_chunks, _ = HEADER.unpack(read_exact(HEADER.size))
                if magic != MAGIC or (major, minor) != (1, 0) or not HEADER.size <= header_size <= 4096 or not CHUNK.size <= chunk_header_size <= 4096:
                    raise ValueError('invalid Android sparse header')
                if not 0 < block_size <= BLOCK or block_size % 4 or total_blocks * block_size != part['size'] or not 0 < total_chunks <= 1_000_000:
                    raise ValueError('sparse geometry differs from manifest')
                read_exact(header_size - HEADER.size)
                for _ in range(total_chunks):
                    kind, _, count, total_size = CHUNK.unpack(read_exact(CHUNK.size))
                    read_exact(chunk_header_size - CHUNK.size)
                    size = count * block_size
                    if logical_bytes + size > part['size'] or total_size < chunk_header_size:
                        raise ValueError('sparse chunk exceeds image geometry')
                    payload = total_size - chunk_header_size
                    if kind == RAW:
                        if payload != size:
                            raise ValueError('raw chunk length mismatch')
                        remaining = size
                        while remaining:
                            data = read_exact(min(remaining, BLOCK))
                            target.write(data)
                            raw_hash.update(data)
                            remaining -= len(data)
                    elif kind == FILL:
                        if payload != 4:
                            raise ValueError('fill chunk length mismatch')
                        word = read_exact(4)
                        remaining = size
                        data = word * (BLOCK // 4)
                        while remaining:
                            piece = data[:min(remaining, BLOCK)]
                            target.write(piece)
                            raw_hash.update(piece)
                            remaining -= len(piece)
                    elif kind == DONT_CARE:
                        if payload:
                            raise ValueError('skip chunk unexpectedly has payload')
                        target.seek(size, os.SEEK_CUR)
                        remaining = size
                        while remaining:
                            n = min(remaining, BLOCK)
                            raw_hash.update(zero[:n])
                            remaining -= n
                    else:
                        raise ValueError(f'unsupported sparse chunk type {kind:#x}')
                    logical_bytes += size
                if logical_bytes != part['size'] or source.read(1):
                    raise ValueError('sparse image has missing or trailing content')
                target.truncate(logical_bytes)
                target.flush()
                os.fsync(target.fileno())
                if hashed_input.bytes_read != compressed_size or sparse_hash.hexdigest() != part['hash'] or raw_hash.hexdigest() != part['hash_raw']:
                    raise ValueError('compressed length, sparse or raw image SHA-256 mismatch')
                publish_open_file(target.fileno(), output)
        if temp.exists() and (temp.lstat().st_dev, temp.lstat().st_ino) == target_inode:
            temp.unlink()
    except BaseException:
        if created_temp and temp.exists() and (temp.lstat().st_dev, temp.lstat().st_ino) == target_inode:
            temp.unlink(missing_ok=True)
        raise
    return {'manifest_sha256': expected_manifest_sha256, 'component': 'system', 'compressed_sha256': hashed_input.hash.hexdigest(), 'compressed_bytes': hashed_input.bytes_read, 'sparse_stream_sha256': sparse_hash.hexdigest(), 'raw_image_sha256': raw_hash.hexdigest(), 'raw_image_bytes': logical_bytes, 'output': str(output), 'verification': 'PASS_SPARSE_AND_RAW_HASH'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compressed', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--expected-manifest-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(reconstruct(args.compressed, args.output, args.manifest, args.expected_manifest_sha256), indent=2, sort_keys=True))
