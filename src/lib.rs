pub fn compress(
    data: &[u8],
    seed_len_range: RangeInclusive<u8>,
    seed_limit: Option<u64>,
    status_interval: u64,
    hash_counter: &mut u64,
    json_out: bool,
    gloss: Option<&GlossTable>,
    verbosity: u8,
    gloss_only: bool,
    mut coverage: Option<&mut [bool]>,
    mut partials: Option<&mut Vec<(Vec<u8>, Header)>>,
) -> Vec<u8> {
    let start = Instant::now();
    let mut chain: Vec<Region> = data
        .chunks(BLOCK_SIZE)
        .map(|b| Region::Raw(b.to_vec()))
        .collect();
    let original_regions = chain.len();
    let original_bytes = data.len();
    let mut brute_matches = 0u64;
    let mut gloss_matches = 0u64;
    let mut sha_cache: HashMap<Vec<u8>, [u8; 32]> = HashMap::new();
    let mut arity_counts: HashMap<u8, u64> = HashMap::new();

    if gloss_only {
        let mut output = Vec::new();
        let mut i = 0;
        while i < chain.len() {
            let mut matched = false;
            if let Some(table) = gloss {
                for arity in (2..=4u8).rev() {
                    if i + arity as usize <= chain.len() {
                        let slice = &chain[i..i + arity as usize];
                        let target = decompress_regions(slice);
                        if let Some((idx, entry)) = table.find_with_index(&target) {
                            if verbosity >= 2 {
                                eprintln!(
                                    "gloss match: seed={} arity={} nest={} index={}",
                                    hex::encode(&entry.seed),
                                    arity,
                                    entry.header.nest_len,
                                    i
                                );
                            }
                            output.push(Region::Compressed(entry.seed.clone(), entry.header));
                            gloss_matches += 1;
                            if let Some(ref mut cov) = coverage {
                                cov[idx] = true;
                            }
                            *arity_counts.entry(arity).or_insert(0) += 1;
                            i += arity as usize;
                            matched = true;
                            break;
                        }
                    }
                }
            }
            if !matched {
                output.push(chain[i].clone());
                i += 1;
            }
        }
        chain = output;
    } else {
        loop {
            let mut matched = false;

            'outer: for start_i in 0..chain.len() {
                for arity in (2..=4u8).rev() {
                    if start_i + arity as usize > chain.len() {
                        continue;
                    }

                    let slice = &chain[start_i..start_i + arity as usize];
                    let target = decompress_regions(slice);

                    if let Some(table) = gloss {
                        if let Some((idx, entry)) = table.find_with_index(&target) {
                            if verbosity >= 2 {
                                eprintln!(
                                    "gloss match: seed={} arity={} nest={} index={}",
                                    hex::encode(&entry.seed),
                                    arity,
                                    entry.header.nest_len,
                                    start_i
                                );
                            }
                            chain.splice(
                                start_i..start_i + arity as usize,
                                [Region::Compressed(entry.seed.clone(), entry.header)],
                            );
                            gloss_matches += 1;
                            if let Some(ref mut cov) = coverage {
                                cov[idx] = true;
                            }
                            *arity_counts.entry(arity).or_insert(0) += 1;
                            matched = true;
                            break 'outer;
                        }
                    }

                    for seed_len in seed_len_range.clone() {
                        let max = 1u64 << (8 * seed_len as u64);
                        let limit = seed_limit.unwrap_or(max).min(max);

                        for seed in 0..limit {
                            *hash_counter += 1;
                            if *hash_counter % status_interval == 0 {
                                print_stats(
                                    &chain,
                                    original_bytes,
                                    original_regions,
                                    *hash_counter,
                                    brute_matches,
                                    gloss_matches,
                                    chain.iter().filter(|r| matches!(r, Region::Raw(_))).count() as u64,
                                    &arity_counts,
                                    json_out,
                                    verbosity,
                                    start,
                                    false,
                                );
                            }

                            let seed_bytes = &seed.to_be_bytes()[8 - seed_len as usize..];
                            let digest: [u8; 32] = if seed_len <= 2 {
                                *sha_cache.entry(seed_bytes.to_vec())
                                    .or_insert_with(|| Sha256::digest(seed_bytes).into())
                            } else {
                                Sha256::digest(seed_bytes).into()
                            };

                            if digest.starts_with(&target) {
                                let nest = encoded_len_of_regions(slice) as u32;
                                let header = Header {
                                    seed_len: seed_len - 1,
                                    nest_len: nest,
                                    arity: arity - 1,
                                };
                                if verbosity >= 2 {
                                    eprintln!(
                                        "match: seed={} len={} arity={} nest={} index={}",
                                        hex::encode(seed_bytes),
                                        seed_len,
                                        arity,
                                        nest,
                                        start_i
                                    );
                                }
                                chain.splice(
                                    start_i..start_i + arity as usize,
                                    [Region::Compressed(seed_bytes.to_vec(), header)],
                                );
                                matched = true;
                                brute_matches += 1;
                                *arity_counts.entry(arity).or_insert(0) += 1;
                                break 'outer;
                            } else if let Some(storage) = partials.as_mut() {
                                let mut prefix = BLOCK_SIZE;
                                let mut matched_len = 0;
                                while prefix <= target.len() {
                                    if digest.starts_with(&target[..prefix]) {
                                        matched_len = prefix;
                                        prefix += BLOCK_SIZE;
                                    } else {
                                        break;
                                    }
                                }
                                if matched_len >= BLOCK_SIZE && matched_len < target.len() {
                                    let nest = encoded_len_of_regions(slice) as u32;
                                    let header = Header {
                                        seed_len: seed_len - 1,
                                        nest_len: nest,
                                        arity: arity - 1,
                                    };
                                    if storage.len() >= 10_000 {
                                        storage.remove(0);
                                    }
                                    storage.push((seed_bytes.to_vec(), header));
                                }
                            }
                        }
                    }
                }
            }

            if !matched {
                break;
            }
        }
    }

    let mut encoded = Vec::new();
    let mut fallback_count = 0u64;
    for r in &chain {
        if matches!(r, Region::Raw(_)) {
            fallback_count += 1;
        }
        encoded.extend_from_slice(&encode_region(r));
    }

    print_stats(
        &chain,
        original_bytes,
        original_regions,
        *hash_counter,
        brute_matches,
        gloss_matches,
        fallback_count,
        &arity_counts,
        json_out,
        verbosity,
        start,
        true,
    );

    encoded
}
