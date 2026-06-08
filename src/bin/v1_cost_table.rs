use serde_json::json;
use telomere::v1_record_bit_len;

const J_BITS: usize = 3;
const TIERS: usize = 1;

fn lotus_width_for_value(value: u128) -> usize {
    let mut width = 1usize;
    loop {
        let start = (1u128 << width) - 2;
        let end = (1u128 << (width + 1)) - 3;
        if value >= start && value <= end {
            return width;
        }
        width += 1;
    }
}

fn max_width_for_config(j_bits: usize, tiers: usize) -> u128 {
    let mut max_width = 1u128 << j_bits;
    for _ in 0..tiers {
        let shift = max_width + 1;
        if shift >= 128 {
            return u128::MAX;
        }
        max_width = (1u128 << shift) - 4;
    }
    max_width
}

fn arity_bits(arity: usize) -> usize {
    match arity {
        1 | 2 => 2,
        3..=5 | 0xFF => 3,
        _ => panic!("invalid arity"),
    }
}

fn j3d1_bits_for_payload_width(payload_width: usize) -> usize {
    let tier_width = lotus_width_for_value(payload_width as u128);
    J_BITS + tier_width + payload_width
}

fn min_seed_index_for_payload_width(payload_width: usize) -> Option<u64> {
    if payload_width == 0 || payload_width > 64 {
        return None;
    }
    let start_payload_value = (1u128 << payload_width) - 2;
    let seed_index = start_payload_value.saturating_sub(1);
    u64::try_from(seed_index).ok()
}

fn max_seed_index_for_payload_width(payload_width: usize) -> Option<u64> {
    if payload_width == 0 || payload_width > 64 {
        return None;
    }
    let end_payload_value = (1u128 << (payload_width + 1)) - 3;
    let seed_index = end_payload_value.saturating_sub(1);
    u64::try_from(seed_index).ok()
}

fn main() {
    let payload_rows: Vec<_> = (1usize..=256)
        .map(|payload_width| {
            let j3d1_bits = j3d1_bits_for_payload_width(payload_width);
            let rust_checked = min_seed_index_for_payload_width(payload_width)
                .map(|seed_index| {
                    (1usize..=5)
                        .map(|arity| {
                            let rust_bits = v1_record_bit_len(arity, seed_index).unwrap();
                            let probe_bits = arity_bits(arity) + j3d1_bits;
                            assert_eq!(
                                rust_bits, probe_bits,
                                "arity={arity} payload_width={payload_width} seed={seed_index}"
                            );
                            rust_bits
                        })
                        .collect::<Vec<_>>()
                })
                .is_some();

            json!({
                "payload_width": payload_width,
                "j3d1_bits": j3d1_bits,
                "arity_1_bits": arity_bits(1) + j3d1_bits,
                "arity_2_bits": arity_bits(2) + j3d1_bits,
                "arity_3_bits": arity_bits(3) + j3d1_bits,
                "arity_4_bits": arity_bits(4) + j3d1_bits,
                "arity_5_bits": arity_bits(5) + j3d1_bits,
                "rust_v1_record_bit_len_checked": rust_checked,
            })
        })
        .collect();

    let boundary_widths = [1usize, 2, 3, 4, 5, 6, 7, 8, 12, 16, 24, 32, 48, 64];
    let boundaries: Vec<_> = boundary_widths
        .iter()
        .flat_map(|width| {
            [
                min_seed_index_for_payload_width(*width).map(|seed_index| {
                    json!({
                        "payload_width": width,
                        "edge": "min",
                        "seed_index": seed_index,
                        "j3d1_bits": v1_record_bit_len(1, seed_index).unwrap() - arity_bits(1),
                    })
                }),
                max_seed_index_for_payload_width(*width).map(|seed_index| {
                    json!({
                        "payload_width": width,
                        "edge": "max",
                        "seed_index": seed_index,
                        "j3d1_bits": v1_record_bit_len(1, seed_index).unwrap() - arity_bits(1),
                    })
                }),
            ]
        })
        .flatten()
        .collect();

    let payload = json!({
        "source": "src/header.rs::v1_record_bit_len validated against sibling lotus J3D1 arithmetic",
        "j_bits": J_BITS,
        "tiers": TIERS,
        "max_payload_width_bits": max_width_for_config(J_BITS, TIERS),
        "arity_bits": {
            "1": arity_bits(1),
            "2": arity_bits(2),
            "3": arity_bits(3),
            "4": arity_bits(4),
            "5": arity_bits(5)
        },
        "literal_marker_bits": arity_bits(0xFF),
        "payload_width_rows": payload_rows,
        "tier_boundary_indices": boundaries,
    });

    println!("{}", serde_json::to_string_pretty(&payload).unwrap());
}
