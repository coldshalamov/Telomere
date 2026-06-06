# Telomere Compression Project

## Overview
Telomere is a deterministic, generative compression tool written in Rust. It uses a brute-force seed search to find short seeds whose SHA-256 hash output matches blocks of the input data.

## Key Features
- **Generative Compression**: Replaces data blocks with seeds that hash to the data.
- **Deterministic**: Fully reproducible compression and decompression.
- **Pass-based**: Uses multiple passes to incrementally compress data.
- **CLI**: Provides `compress` and `decompress` commands.
- **Rust Implementation**: Built for performance and safety.

## Status
- **Current State**: Restored to working state. Compiles and passes core tests.
- **Verification**: `cargo test --lib` passes. Manual roundtrip verified.
- **Date**: December 2025.
