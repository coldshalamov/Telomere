use inchworm::Header;

#[test]
fn pack_unpack_roundtrip() {
    let cases = [
        Header { seed_len: 0, nest_len: 0, arity: 0 },
        Header { seed_len: 1, nest_len: 0x1FFFFF, arity: 3 },
    ];
    for h in cases.iter() {
        assert_eq!(Header::unpack(h.pack()), *h);
    }
}
