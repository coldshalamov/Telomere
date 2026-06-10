//! Ground-truth cost probe for the active v2 record format.
//!
//! Prints exact on-wire bit costs straight from the real `telomere` / `lotus`
//! functions, and cross-checks them against a closed-form Lotus J3D2 model so
//! the math doc can be anchored to code, not hand arithmetic.
//!
//! Run: `cargo run --bin v2_cost_probe`

use lotus::{lotus_encoded_bit_len, BitWriter};
use telomere::{
    compress_streaming_v2_with_telemetry, encode_v2_file, v2_fixed_seed_span_record_bit_len,
    v2_literal_record_into_writer, v2_seed_span_record_bit_len, HasherKind, TlmrV2LayerDescriptor,
    LOTUS_J_BITS, LOTUS_TIERS,
};

/// Deterministic high-entropy fill (splitmix64) so the end-to-end run sees an
/// incompressible buffer without pulling in the `rand` dev-dependency.
fn fill_incompressible(buf: &mut [u8]) {
    let mut x: u64 = 0x9E37_79B9_7F4A_7C15;
    for chunk in buf.chunks_mut(8) {
        x = x.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = x;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^= z >> 31;
        let bytes = z.to_le_bytes();
        for (slot, b) in chunk.iter_mut().zip(bytes.iter()) {
            *slot = *b;
        }
    }
}

/// Closed-form Lotus codeword width: smallest w >= 1 with
/// value in [2^w - 2, 2^(w+1) - 3]. Equivalent to floor(log2(value + 2)).
fn width(value: u128) -> usize {
    let mut w = 1usize;
    loop {
        let start = (1u128 << w) - 2;
        let end = (1u128 << (w + 1)) - 3;
        if value >= start && value <= end {
            return w;
        }
        w += 1;
    }
}

/// Closed-form total bits for Lotus(value) under (j_bits, tiers).
fn lotus_bits_closed(value: u64, j_bits: usize, tiers: usize) -> usize {
    let payload_value = value as u128 + 1;
    let payload_width = width(payload_value);
    let mut total_tier = 0usize;
    let mut cur = payload_width;
    for _ in 0..tiers {
        let tw = width(cur as u128);
        total_tier += tw;
        cur = tw;
    }
    j_bits + total_tier + payload_width
}

fn main() {
    println!("=== Lotus J3D2 cost: closed form vs real lotus_encoded_bit_len ===");
    println!("j_bits={LOTUS_J_BITS} tiers={LOTUS_TIERS}");
    println!("{:>12} {:>10} {:>10} {:>6}", "value", "real", "closed", "ok");
    let sample = [
        0u64, 1, 2, 3, 4, 5, 6, 7, 13, 14, 15, 16, 31, 32, 63, 64, 127, 128, 255, 256, 1000, 65534,
        65535, 1_000_000,
    ];
    for v in sample {
        let real = lotus_encoded_bit_len(v, LOTUS_J_BITS, LOTUS_TIERS).unwrap();
        let closed = lotus_bits_closed(v, LOTUS_J_BITS, LOTUS_TIERS);
        println!(
            "{:>12} {:>10} {:>10} {:>6}",
            v,
            real,
            closed,
            if real == closed { "yes" } else { "NO" }
        );
    }

    println!("\n=== Record tags (Lotus J3D2) ===");
    println!("tag=0 (seed-span) bits = {}", lotus_encoded_bit_len(0, LOTUS_J_BITS, LOTUS_TIERS).unwrap());
    println!("tag=1 (literal)   bits = {}", lotus_encoded_bit_len(1, LOTUS_J_BITS, LOTUS_TIERS).unwrap());

    println!("\n=== Literal-run record: real total bit_len and overhead ===");
    println!("(overhead = total_bits - 8*len; includes tag + Lotus(len-1) + byte-align pad)");
    println!("{:>8} {:>12} {:>12} {:>16}", "len", "total_bits", "overhead", "overhead/byte");
    for len in [1usize, 2, 3, 4, 8, 16, 32, 64, 256, 1024, 4096, 16384, 65535] {
        let bytes = vec![0u8; len];
        // Measure the streaming form starting at a byte boundary (writer at 0),
        // which is the worst-case alignment the encoder actually hits when a
        // literal run begins right after a byte-aligned record boundary.
        let mut w = BitWriter::new();
        let bits = v2_literal_record_into_writer(&mut w, &bytes).unwrap();
        let overhead = bits - 8 * len;
        println!(
            "{:>8} {:>12} {:>12} {:>16.4}",
            len,
            bits,
            overhead,
            overhead as f64 / len as f64
        );
    }

    println!("\n=== Seed-span records (max_seed_len = 1; seed_index in 0..=255) ===");
    println!("variable = tag + Lotus(span-1) + Lotus(seed_idx); fixed = tag + Lotus(seed_idx)");
    println!(
        "{:>10} {:>10} {:>16} {:>14} {:>14}",
        "span_len", "seed_idx", "variable_bits", "fixed_bits", "span_bits(8L)"
    );
    for &span in &[1usize, 2, 3, 4, 8, 16] {
        for &seed in &[0u8, 1, 16, 128, 255] {
            let var = v2_seed_span_record_bit_len(span, &[seed], 1).unwrap();
            let fixed = v2_fixed_seed_span_record_bit_len(&[seed], 1).unwrap();
            println!(
                "{:>10} {:>10} {:>16} {:>14} {:>14}",
                span,
                seed,
                var,
                fixed,
                span * 8
            );
        }
    }

    println!("\n=== Worst-case seed-index cost by max_seed_len (largest index in bucket) ===");
    println!("{:>13} {:>12} {:>14}", "max_seed_len", "max_index", "Lotus_bits");
    // cumulative seed counts: 1-byte ends at 255, 2-byte at 65791, etc.
    let mut cum: u64 = 0;
    for sl in 1usize..=4 {
        cum += 1u64 << (8 * sl);
        let max_index = cum - 1;
        let bits = lotus_encoded_bit_len(max_index, LOTUS_J_BITS, LOTUS_TIERS).unwrap();
        println!("{:>13} {:>12} {:>14}", sl, max_index, bits);
    }

    println!("\n=== Container overhead (magic + version + header + N layer descriptors) ===");
    println!("Measured by encoding a v2 file with a 1-byte payload and subtracting payload.");
    println!("{:>8} {:>16} {:>20}", "layers", "file_bytes", "container_bytes");
    let payload = vec![0u8; 1];
    for nlayers in [1usize, 2, 5, 10] {
        let desc = TlmrV2LayerDescriptor::for_decoded_bytes(&[0u8; 8], HasherKind::Sha256, 1, 8, 4, 13);
        let layers: Vec<_> = (0..nlayers).map(|_| desc.clone()).collect();
        // original_len is just metadata here; use 8.
        let file = encode_v2_file(HasherKind::Sha256, 13, 8, &layers, &payload).unwrap();
        let container = file.len() - payload.len();
        println!("{:>8} {:>16} {:>20}", nlayers, file.len(), container);
    }

    println!("\n=== Seed-index coding: Lotus vs flat fixed-width (per seed bucket) ===");
    println!("For a bounded seed universe the index is uniform; Lotus over-charges high indices.");
    println!(
        "{:>13} {:>10} {:>10} {:>10} {:>12} {:>12}",
        "max_seed_len", "n_seeds", "min_Lotus", "max_Lotus", "mean_Lotus", "flat_width"
    );
    let mut cum_start: u64 = 0;
    for sl in 1usize..=2 {
        let n = 1u64 << (8 * sl); // seeds of exactly this length
        let lo = cum_start;
        let hi = cum_start + n - 1;
        let mut sum = 0u64;
        let mut mn = u64::MAX;
        let mut mx = 0u64;
        for idx in lo..=hi {
            let b = lotus_encoded_bit_len(idx, LOTUS_J_BITS, LOTUS_TIERS).unwrap() as u64;
            sum += b;
            mn = mn.min(b);
            mx = mx.max(b);
        }
        let mean = sum as f64 / n as f64;
        // Flat width to address the whole cumulative universe [0, hi].
        let flat = (64 - hi.leading_zeros()) as usize; // ceil(log2(hi+1))
        println!(
            "{:>13} {:>10} {:>10} {:>10} {:>12.3} {:>12}",
            sl, n, mn, mx, mean, flat
        );
        cum_start += n;
    }

    println!("\n=== Net break-even cluster size k* (adjacent hits needed) ===");
    println!("k* = ceil(O_run / (8B - R)); a cluster of <k* adjacent hits BLOATS after run-split.");
    println!("O_run = one extra literal-run header. R = seed-record bits.");
    println!("Two formats: CURRENT v2 fixed-span (R=6+Lotus(seed)) and MINIMAL (R=1+8).");
    // Representative O_run: a split typically creates a sub-255-byte run -> 24 bits;
    // also show the 32-bit (sub-64KB) case.
    let o_run_v2 = 24i64; // ceil_to_byte(9 + Lotus(len-1)) for len<=255
    let o_run_min = {
        // minimal literal header: 1-bit flag + Lotus(len-1) + pad-to-byte, len<=255
        // worst ~ 1 + 16 -> pad to 24
        24i64
    };
    println!(
        "{:>3} {:>9} {:>14} {:>10} {:>16} {:>10}",
        "B", "8B_bits", "R_v2_best", "k*_v2_best", "R_min(1+8)", "k*_min"
    );
    for b in 1i64..=8 {
        let span_bits = 8 * b;
        let r_v2_best = 6 + lotus_encoded_bit_len(0, LOTUS_J_BITS, LOTUS_TIERS).unwrap() as i64; // seed=0
        let r_min = 1 + 8;
        let kstar = |o: i64, r: i64| -> String {
            let denom = span_bits - r;
            if denom <= 0 {
                "never".to_string()
            } else {
                (((o + denom - 1) / denom).max(1)).to_string()
            }
        };
        println!(
            "{:>3} {:>9} {:>14} {:>10} {:>16} {:>10}",
            b,
            span_bits,
            r_v2_best,
            kstar(o_run_v2, r_v2_best),
            r_min,
            kstar(o_run_min, r_min)
        );
    }

    println!("\n=== Header field cost breakdown (single layer, hash_bits=13) ===");
    // magic+version = 5 bytes raw. Then header Lotus fields + hash + descriptor.
    let desc = TlmrV2LayerDescriptor::for_decoded_bytes(&[0u8; 8], HasherKind::Sha256, 1, 8, 4, 13);
    let file = encode_v2_file(HasherKind::Sha256, 13, 8, std::slice::from_ref(&desc), &payload).unwrap();
    println!("total file bytes (1-byte payload) = {}", file.len());
    println!("  raw magic+version             = 5 bytes");
    println!("  header+descriptor+pad+payload = {} bytes", file.len() - 5);

    println!("\n=== END-TO-END: real encoder on 1,000,000 incompressible bytes ===");
    println!("compress_streaming_v2_with_telemetry(B=2, max_seed_len=1, max_arity=5, passes=10, hash_bits=13)");
    let n = 1_000_000usize;
    let mut data = vec![0u8; n];
    fill_incompressible(&mut data);
    let (file, tel) =
        compress_streaming_v2_with_telemetry(&data, HasherKind::Sha256, 1, 16, 2, 5, 10, 13)
            .unwrap();
    let net_pct = 100.0 * (1.0 - file.len() as f64 / n as f64);
    println!("raw bytes              = {n}");
    println!("final file bytes       = {}  (net {:.4}%)", file.len(), net_pct);
    println!("container_bytes        = {}", tel.container_bytes);
    println!("final_payload_bytes    = {}", tel.final_payload_bytes);
    println!("layers kept            = {}", tel.layers.len());
    println!("total selected_count   = {}", tel.selected_count);
    println!("total literal_bytes    = {}", tel.literal_bytes);
    println!("stop_reason            = {}", tel.stop_reason);
    for (i, layer) in tel.layers.iter().enumerate() {
        println!(
            "  layer {}: bytes_in={} payload_bytes={} selected={} literal_bytes={}",
            i + 1,
            layer.bytes_in,
            layer.payload_bytes,
            layer.selected_count,
            layer.literal_bytes
        );
    }
}
