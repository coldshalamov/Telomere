use telomere::Config;

#[test]
fn config_validation_accepts_fast_default_shape() {
    let cfg = Config {
        block_size: 4,
        max_seed_len: 1,
        max_arity: 5,
        hash_bits: 13,
        ..Config::default()
    };

    cfg.validate().unwrap();
}

#[test]
fn config_validation_rejects_out_of_range_fields() {
    let cases = [
        Config {
            block_size: 0,
            ..Config::default()
        },
        Config {
            max_seed_len: 0,
            ..Config::default()
        },
        Config {
            max_seed_len: 4,
            ..Config::default()
        },
        Config {
            max_arity: 0,
            ..Config::default()
        },
        Config {
            max_arity: 6,
            ..Config::default()
        },
        Config {
            hash_bits: 0,
            ..Config::default()
        },
        Config {
            hash_bits: 65,
            ..Config::default()
        },
        Config {
            memory_limit: 0,
            ..Config::default()
        },
    ];

    for cfg in cases {
        assert!(
            cfg.validate().is_err(),
            "invalid config unexpectedly passed"
        );
    }
}
