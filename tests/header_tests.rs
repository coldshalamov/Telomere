use inchworm::{Header, encode_header, decode_header};

#[test]
fn header_roundtrip_across_ranges() {
    for seed_idx in [0usize, 1, 64, 12345, 1_000_000] {
        for arity in 1..50 {
            let h = Header { seed_index: seed_idx, arity };
            let enc = encode_header(h.seed_index, h.arity);
            let (sid2, arity2, _) = decode_header(&enc).expect("decode failed");
            assert_eq!(seed_idx, sid2);
            assert_eq!(arity, arity2);
        }
    }
}
