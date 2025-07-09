use inchworm::{CompressionPath, PathGloss};

#[test]
fn insert_and_lookup_basic() {
    let mut pg = PathGloss::default();
    let path = CompressionPath {
        id: 1,
        seeds: vec![vec![1], vec![2]],
        span_hashes: vec![[0; 32]],
        total_gain: 8,
        created_at: 0,
        replayed: 0,
    };
    assert!(pg.try_insert(path.clone()));
    let found = pg.lookup(&[0; 32]).unwrap();
    assert_eq!(found.id, 1);
}

#[test]
fn respects_max_paths() {
    let mut pg = PathGloss { max_paths: 1, ..Default::default() };
    let p1 = CompressionPath {
        id: 1,
        seeds: vec![vec![1], vec![2]],
        span_hashes: vec![[1; 32]],
        total_gain: 5,
        created_at: 0,
        replayed: 0,
    };
    let p2 = CompressionPath {
        id: 2,
        seeds: vec![vec![3], vec![4]],
        span_hashes: vec![[2; 32]],
        total_gain: 10,
        created_at: 1,
        replayed: 0,
    };
    assert!(pg.try_insert(p1));
    assert!(pg.try_insert(p2));
    assert_eq!(pg.paths.len(), 1);
    assert_eq!(pg.paths[0].id, 2);
}
