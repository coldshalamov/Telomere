use crate::config::HasherKind;
use crate::seed_index::{index_to_seed, seed_to_index};
use crate::tlmr::MAX_SEED_LEN;
use crate::TelomereError;
use memmap2::Mmap;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufReader, ErrorKind, Read, Write};
use std::path::{Path, PathBuf};

pub const INDEX_MAGIC: &[u8; 4] = b"TIDX";
pub const INDEX_VERSION: u8 = 1;
pub const SEED_ORDER_VERSION: u8 = 1;
const INDEX_BUILD_CHUNK_SEEDS: usize = 65_536;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexConfig {
    pub hasher: HasherKind,
    pub max_seed_len: usize,
    pub max_span_len: usize,
    pub tier_lengths: Vec<usize>,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TierSpec {
    pub span_len: usize,
    pub record_count: usize,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexManifest {
    pub magic: String,
    pub version: u8,
    pub hasher: HasherKind,
    pub seed_order_version: u8,
    pub max_seed_len: usize,
    pub max_span_len: usize,
    pub tiers: Vec<TierSpec>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SeedHit {
    pub span_len: usize,
    pub seed_index: usize,
    pub seed: Vec<u8>,
}

pub trait SeedLookup: Send + Sync {
    fn manifest(&self) -> &IndexManifest;
    fn lookup_exact(
        &self,
        span_len: usize,
        target: &[u8],
    ) -> Result<Option<SeedHit>, TelomereError>;
}

#[derive(Debug, Clone)]
pub struct SeedExpansionIndex {
    manifest: IndexManifest,
    tiers: HashMap<usize, HashMap<Vec<u8>, SeedHit>>,
}

impl SeedExpansionIndex {
    pub fn build_in_memory(config: &IndexConfig) -> Result<Self, TelomereError> {
        validate_index_config(config)?;
        let expander = config.hasher.get_expander();
        let mut tier_lengths = normalized_tiers(&config.tier_lengths)?;
        tier_lengths.retain(|len| *len <= config.max_span_len);

        let mut tiers: HashMap<usize, HashMap<Vec<u8>, SeedHit>> = tier_lengths
            .iter()
            .map(|len| (*len, HashMap::new()))
            .collect();

        let mut global_offset = 0usize;
        for seed_len in 1..=config.max_seed_len {
            let count = 1usize << (8 * seed_len);
            for local_idx in 0..count {
                let seed_index = global_offset + local_idx;
                let seed = index_to_seed(seed_index, config.max_seed_len)?;
                let mut expanded = vec![0u8; config.max_span_len];
                expander.expand_into(&seed, &mut expanded);
                for span_len in &tier_lengths {
                    let key = expanded[..*span_len].to_vec();
                    tiers
                        .get_mut(span_len)
                        .unwrap()
                        .entry(key)
                        .or_insert_with(|| SeedHit {
                            span_len: *span_len,
                            seed_index,
                            seed: seed.clone(),
                        });
                }
            }
            global_offset += count;
        }

        let manifest = IndexManifest {
            magic: String::from_utf8_lossy(INDEX_MAGIC).to_string(),
            version: INDEX_VERSION,
            hasher: config.hasher,
            seed_order_version: SEED_ORDER_VERSION,
            max_seed_len: config.max_seed_len,
            max_span_len: config.max_span_len,
            tiers: tier_lengths
                .iter()
                .map(|span_len| TierSpec {
                    span_len: *span_len,
                    record_count: tiers.get(span_len).map_or(0, HashMap::len),
                })
                .collect(),
        };

        Ok(Self { manifest, tiers })
    }

    pub fn from_exact_map_for_tests(
        config: IndexConfig,
        exact_map: HashMap<Vec<u8>, Vec<u8>>,
    ) -> Result<Self, TelomereError> {
        validate_index_config(&config)?;
        let mut tiers: HashMap<usize, HashMap<Vec<u8>, SeedHit>> = HashMap::new();
        for (target, seed) in exact_map {
            let span_len = target.len();
            if !config.tier_lengths.contains(&span_len) {
                return Err(TelomereError::Config(format!(
                    "test target length {span_len} is not configured as a tier"
                )));
            }
            let seed_index = seed_to_index(&seed, config.max_seed_len);
            tiers.entry(span_len).or_default().insert(
                target,
                SeedHit {
                    span_len,
                    seed_index,
                    seed,
                },
            );
        }
        for span_len in &config.tier_lengths {
            tiers.entry(*span_len).or_default();
        }

        let manifest = IndexManifest {
            magic: String::from_utf8_lossy(INDEX_MAGIC).to_string(),
            version: INDEX_VERSION,
            hasher: config.hasher,
            seed_order_version: SEED_ORDER_VERSION,
            max_seed_len: config.max_seed_len,
            max_span_len: config.max_span_len,
            tiers: normalized_tiers(&config.tier_lengths)?
                .into_iter()
                .map(|span_len| TierSpec {
                    span_len,
                    record_count: tiers.get(&span_len).map_or(0, HashMap::len),
                })
                .collect(),
        };

        Ok(Self { manifest, tiers })
    }

    pub fn manifest(&self) -> &IndexManifest {
        &self.manifest
    }

    pub fn lookup_exact(
        &self,
        span_len: usize,
        target: &[u8],
    ) -> Result<Option<SeedHit>, TelomereError> {
        <Self as SeedLookup>::lookup_exact(self, span_len, target)
    }

    pub fn write_to_dir(&self, path: &Path) -> Result<(), TelomereError> {
        if path.exists() && !path.is_dir() {
            return Err(TelomereError::Config(format!(
                "index output {:?} exists and is not a directory",
                path
            )));
        }
        fs::create_dir_all(path)?;
        let manifest_path = path.join("manifest.json");
        let manifest_json = serde_json::to_vec_pretty(&self.manifest)
            .map_err(|e| TelomereError::Internal(format!("serializing index manifest: {e}")))?;
        fs::write(manifest_path, manifest_json)?;

        for spec in &self.manifest.tiers {
            let tier_path = tier_path(path, spec.span_len);
            let mut records: Vec<_> = self
                .tiers
                .get(&spec.span_len)
                .into_iter()
                .flat_map(|tier| tier.iter())
                .collect();
            records.sort_by(|a, b| a.0.cmp(b.0));

            let mut file = File::create(tier_path)?;
            for (key, hit) in records {
                file.write_all(key)?;
                file.write_all(&[hit.seed.len() as u8])?;
                let mut padded = vec![0u8; self.manifest.max_seed_len];
                padded[..hit.seed.len()].copy_from_slice(&hit.seed);
                file.write_all(&padded)?;
            }
        }

        Ok(())
    }
}

impl SeedLookup for SeedExpansionIndex {
    fn manifest(&self) -> &IndexManifest {
        &self.manifest
    }

    fn lookup_exact(
        &self,
        span_len: usize,
        target: &[u8],
    ) -> Result<Option<SeedHit>, TelomereError> {
        if target.len() != span_len {
            return Err(TelomereError::Config(
                "lookup target length mismatch".into(),
            ));
        }
        Ok(self
            .tiers
            .get(&span_len)
            .and_then(|tier| tier.get(target).cloned()))
    }
}

pub struct MmapSeedExpansionIndex {
    manifest: IndexManifest,
    tiers: HashMap<usize, MmapTier>,
}

struct MmapTier {
    mmap: Mmap,
    record_size: usize,
    record_count: usize,
    max_seed_len: usize,
}

impl MmapSeedExpansionIndex {
    pub fn open_dir(path: &Path) -> Result<Self, TelomereError> {
        let manifest = read_manifest(path)?;
        validate_manifest(&manifest)?;
        let mut tiers = HashMap::new();

        for spec in &manifest.tiers {
            let file = File::open(tier_path(path, spec.span_len))?;
            let metadata_len = file.metadata()?.len() as usize;
            let record_size = spec.span_len + 1 + manifest.max_seed_len;
            if record_size == 0 || metadata_len != record_size * spec.record_count {
                return Err(TelomereError::Config(format!(
                    "tier {} has invalid byte length",
                    spec.span_len
                )));
            }
            let mmap = unsafe { Mmap::map(&file)? };
            tiers.insert(
                spec.span_len,
                MmapTier {
                    mmap,
                    record_size,
                    record_count: spec.record_count,
                    max_seed_len: manifest.max_seed_len,
                },
            );
        }

        Ok(Self { manifest, tiers })
    }

    pub fn verify_dir(path: &Path) -> Result<IndexManifest, TelomereError> {
        let index = Self::open_dir(path)?;
        for spec in &index.manifest.tiers {
            let tier = index.tiers.get(&spec.span_len).unwrap();
            let mut previous: Option<&[u8]> = None;
            for record_idx in 0..tier.record_count {
                let key = tier.key_at(record_idx, spec.span_len);
                if let Some(prev) = previous {
                    if prev >= key {
                        return Err(TelomereError::Config(format!(
                            "tier {} is not strictly sorted",
                            spec.span_len
                        )));
                    }
                }
                previous = Some(key);
            }
        }
        Ok(index.manifest)
    }

    pub fn manifest(&self) -> &IndexManifest {
        &self.manifest
    }
}

impl MmapTier {
    fn key_at(&self, record_idx: usize, span_len: usize) -> &[u8] {
        let start = record_idx * self.record_size;
        &self.mmap[start..start + span_len]
    }

    fn hit_at(&self, record_idx: usize, span_len: usize) -> Result<SeedHit, TelomereError> {
        let start = record_idx * self.record_size;
        let seed_len = self.mmap[start + span_len] as usize;
        if seed_len == 0 || seed_len > self.max_seed_len {
            return Err(TelomereError::Config("invalid seed length in index".into()));
        }
        let seed_start = start + span_len + 1;
        let seed = self.mmap[seed_start..seed_start + seed_len].to_vec();
        Ok(SeedHit {
            span_len,
            seed_index: seed_to_index(&seed, self.max_seed_len),
            seed,
        })
    }
}

impl SeedLookup for MmapSeedExpansionIndex {
    fn manifest(&self) -> &IndexManifest {
        &self.manifest
    }

    fn lookup_exact(
        &self,
        span_len: usize,
        target: &[u8],
    ) -> Result<Option<SeedHit>, TelomereError> {
        if target.len() != span_len {
            return Err(TelomereError::Config(
                "lookup target length mismatch".into(),
            ));
        }
        let Some(tier) = self.tiers.get(&span_len) else {
            return Ok(None);
        };

        let mut left = 0usize;
        let mut right = tier.record_count;
        while left < right {
            let mid = (left + right) / 2;
            match tier.key_at(mid, span_len).cmp(target) {
                std::cmp::Ordering::Less => left = mid + 1,
                std::cmp::Ordering::Greater => right = mid,
                std::cmp::Ordering::Equal => return Ok(Some(tier.hit_at(mid, span_len)?)),
            }
        }
        Ok(None)
    }
}

pub fn build_seed_index_to_dir(
    config: &IndexConfig,
    path: &Path,
) -> Result<IndexManifest, TelomereError> {
    let manifest = build_seed_index_to_dir_chunked(config, path)?;
    Ok(manifest)
}

pub fn read_index_manifest(path: &Path) -> Result<IndexManifest, TelomereError> {
    read_manifest(path)
}

fn read_manifest(path: &Path) -> Result<IndexManifest, TelomereError> {
    let mut bytes = Vec::new();
    File::open(path.join("manifest.json"))?.read_to_end(&mut bytes)?;
    let manifest: IndexManifest = serde_json::from_slice(&bytes)
        .map_err(|e| TelomereError::Config(format!("invalid index manifest: {e}")))?;
    validate_manifest(&manifest)?;
    Ok(manifest)
}

fn tier_path(root: &Path, span_len: usize) -> PathBuf {
    root.join(format!("tier-{span_len}.bin"))
}

fn chunk_path(root: &Path, span_len: usize, chunk_idx: usize) -> PathBuf {
    root.join(format!("tier-{span_len}.chunk-{chunk_idx}.tmp"))
}

#[derive(Debug, Clone, PartialEq, Eq)]
struct IndexBuildRecord {
    key: Vec<u8>,
    seed: Vec<u8>,
}

impl IndexBuildRecord {
    fn seed_index(&self, max_seed_len: usize) -> usize {
        seed_to_index(&self.seed, max_seed_len)
    }

    fn write_to(
        &self,
        out: &mut File,
        span_len: usize,
        max_seed_len: usize,
    ) -> Result<(), TelomereError> {
        debug_assert_eq!(self.key.len(), span_len);
        out.write_all(&self.key)?;
        out.write_all(&[self.seed.len() as u8])?;
        let mut padded = vec![0u8; max_seed_len];
        padded[..self.seed.len()].copy_from_slice(&self.seed);
        out.write_all(&padded)?;
        Ok(())
    }
}

struct ChunkReader {
    reader: BufReader<File>,
    current: Option<IndexBuildRecord>,
}

impl ChunkReader {
    fn open(path: &Path, span_len: usize, max_seed_len: usize) -> Result<Self, TelomereError> {
        let mut reader = Self {
            reader: BufReader::new(File::open(path)?),
            current: None,
        };
        reader.advance(span_len, max_seed_len)?;
        Ok(reader)
    }

    fn advance(&mut self, span_len: usize, max_seed_len: usize) -> Result<(), TelomereError> {
        let mut key = vec![0u8; span_len];
        match self.reader.read_exact(&mut key) {
            Ok(()) => {}
            Err(err) if err.kind() == ErrorKind::UnexpectedEof => {
                self.current = None;
                return Ok(());
            }
            Err(err) => return Err(err.into()),
        }

        let mut seed_len = [0u8; 1];
        self.reader.read_exact(&mut seed_len)?;
        let seed_len = seed_len[0] as usize;
        if seed_len == 0 || seed_len > max_seed_len {
            return Err(TelomereError::Config("invalid seed length in chunk".into()));
        }

        let mut padded = vec![0u8; max_seed_len];
        self.reader.read_exact(&mut padded)?;
        padded.truncate(seed_len);
        self.current = Some(IndexBuildRecord { key, seed: padded });
        Ok(())
    }
}

fn total_seed_count(max_seed_len: usize) -> usize {
    (1..=max_seed_len)
        .map(|seed_len| 1usize << (8 * seed_len))
        .sum()
}

fn sort_and_dedup_chunk(records: &mut Vec<IndexBuildRecord>, max_seed_len: usize) {
    records.sort_by(|left, right| {
        left.key.cmp(&right.key).then_with(|| {
            left.seed_index(max_seed_len)
                .cmp(&right.seed_index(max_seed_len))
        })
    });

    let mut deduped = Vec::with_capacity(records.len());
    for record in records.drain(..) {
        if deduped
            .last()
            .map(|last: &IndexBuildRecord| last.key != record.key)
            .unwrap_or(true)
        {
            deduped.push(record);
        }
    }
    *records = deduped;
}

fn write_chunk(
    path: &Path,
    records: &[IndexBuildRecord],
    span_len: usize,
    max_seed_len: usize,
) -> Result<(), TelomereError> {
    let mut out = File::create(path)?;
    for record in records {
        record.write_to(&mut out, span_len, max_seed_len)?;
    }
    Ok(())
}

fn merge_tier_chunks(
    root: &Path,
    span_len: usize,
    max_seed_len: usize,
    chunks: &[PathBuf],
) -> Result<usize, TelomereError> {
    let mut readers = chunks
        .iter()
        .map(|path| ChunkReader::open(path, span_len, max_seed_len))
        .collect::<Result<Vec<_>, _>>()?;
    let mut out = File::create(tier_path(root, span_len))?;
    let mut record_count = 0usize;

    loop {
        let Some(min_key) = readers
            .iter()
            .filter_map(|reader| reader.current.as_ref().map(|record| record.key.as_slice()))
            .min()
            .map(|key| key.to_vec())
        else {
            break;
        };

        let mut best: Option<IndexBuildRecord> = None;
        for reader in &mut readers {
            let is_current_key = reader
                .current
                .as_ref()
                .map(|record| record.key == min_key)
                .unwrap_or(false);
            if !is_current_key {
                continue;
            }

            let candidate = reader.current.take().unwrap();
            let replace = best
                .as_ref()
                .map(|record| candidate.seed_index(max_seed_len) < record.seed_index(max_seed_len))
                .unwrap_or(true);
            if replace {
                best = Some(candidate);
            }
            reader.advance(span_len, max_seed_len)?;
        }

        let best = best.expect("minimum key must have at least one record");
        best.write_to(&mut out, span_len, max_seed_len)?;
        record_count += 1;
    }

    for chunk in chunks {
        let _ = fs::remove_file(chunk);
    }

    Ok(record_count)
}

fn build_seed_index_to_dir_chunked(
    config: &IndexConfig,
    path: &Path,
) -> Result<IndexManifest, TelomereError> {
    validate_index_config(config)?;
    if path.exists() && !path.is_dir() {
        return Err(TelomereError::Config(format!(
            "index output {:?} exists and is not a directory",
            path
        )));
    }
    fs::create_dir_all(path)?;

    let expander = config.hasher.get_expander();
    let mut tier_lengths = normalized_tiers(&config.tier_lengths)?;
    tier_lengths.retain(|len| *len <= config.max_span_len);
    let mut chunk_paths: HashMap<usize, Vec<PathBuf>> = tier_lengths
        .iter()
        .map(|span_len| (*span_len, Vec::new()))
        .collect();

    let total_seeds = total_seed_count(config.max_seed_len);
    let mut seed_start = 0usize;
    let mut chunk_idx = 0usize;
    while seed_start < total_seeds {
        let seed_end = (seed_start + INDEX_BUILD_CHUNK_SEEDS).min(total_seeds);
        let mut by_tier: HashMap<usize, Vec<IndexBuildRecord>> = tier_lengths
            .iter()
            .map(|span_len| {
                (
                    *span_len,
                    Vec::with_capacity(seed_end.saturating_sub(seed_start)),
                )
            })
            .collect();

        for seed_index in seed_start..seed_end {
            let seed = index_to_seed(seed_index, config.max_seed_len)?;
            let mut expanded = vec![0u8; config.max_span_len];
            expander.expand_into(&seed, &mut expanded);
            for span_len in &tier_lengths {
                by_tier.get_mut(span_len).unwrap().push(IndexBuildRecord {
                    key: expanded[..*span_len].to_vec(),
                    seed: seed.clone(),
                });
            }
        }

        for span_len in &tier_lengths {
            let records = by_tier.get_mut(span_len).unwrap();
            sort_and_dedup_chunk(records, config.max_seed_len);
            if records.is_empty() {
                continue;
            }
            let path = chunk_path(path, *span_len, chunk_idx);
            write_chunk(&path, records, *span_len, config.max_seed_len)?;
            chunk_paths.get_mut(span_len).unwrap().push(path);
        }

        seed_start = seed_end;
        chunk_idx += 1;
    }

    let mut tiers = Vec::new();
    for span_len in tier_lengths {
        let chunks = chunk_paths.remove(&span_len).unwrap_or_default();
        let record_count = merge_tier_chunks(path, span_len, config.max_seed_len, &chunks)?;
        tiers.push(TierSpec {
            span_len,
            record_count,
        });
    }

    let manifest = IndexManifest {
        magic: String::from_utf8_lossy(INDEX_MAGIC).to_string(),
        version: INDEX_VERSION,
        hasher: config.hasher,
        seed_order_version: SEED_ORDER_VERSION,
        max_seed_len: config.max_seed_len,
        max_span_len: config.max_span_len,
        tiers,
    };

    let manifest_json = serde_json::to_vec_pretty(&manifest)
        .map_err(|e| TelomereError::Internal(format!("serializing index manifest: {e}")))?;
    fs::write(path.join("manifest.json"), manifest_json)?;
    Ok(manifest)
}

fn normalized_tiers(tiers: &[usize]) -> Result<Vec<usize>, TelomereError> {
    let mut out = tiers.to_vec();
    out.sort_unstable();
    out.dedup();
    if out.is_empty() || out.iter().any(|len| *len == 0 || *len > u16::MAX as usize) {
        return Err(TelomereError::Config(
            "tier lengths must be non-empty and fit u16".into(),
        ));
    }
    Ok(out)
}

fn validate_index_config(config: &IndexConfig) -> Result<(), TelomereError> {
    if !(1..=MAX_SEED_LEN).contains(&config.max_seed_len) {
        return Err(TelomereError::Config(format!(
            "max_seed_len must be in 1..={MAX_SEED_LEN}"
        )));
    }
    if config.max_span_len == 0 || config.max_span_len > u16::MAX as usize {
        return Err(TelomereError::Config(
            "max_span_len must be in 1..=65535".into(),
        ));
    }
    let tiers = normalized_tiers(&config.tier_lengths)?;
    if tiers.iter().any(|len| *len > config.max_span_len) {
        return Err(TelomereError::Config(
            "tier length exceeds max_span_len".into(),
        ));
    }
    Ok(())
}

fn validate_manifest(manifest: &IndexManifest) -> Result<(), TelomereError> {
    if manifest.magic.as_bytes() != INDEX_MAGIC
        || manifest.version != INDEX_VERSION
        || manifest.seed_order_version != SEED_ORDER_VERSION
        || !(1..=MAX_SEED_LEN).contains(&manifest.max_seed_len)
        || manifest.max_span_len == 0
        || manifest.max_span_len > u16::MAX as usize
        || manifest.tiers.is_empty()
    {
        return Err(TelomereError::Config("invalid index manifest".into()));
    }
    let tiers = normalized_tiers(
        &manifest
            .tiers
            .iter()
            .map(|tier| tier.span_len)
            .collect::<Vec<_>>(),
    )?;
    if tiers.len() != manifest.tiers.len()
        || tiers
            .iter()
            .any(|span_len| *span_len > manifest.max_span_len)
    {
        return Err(TelomereError::Config("invalid index manifest".into()));
    }
    Ok(())
}
