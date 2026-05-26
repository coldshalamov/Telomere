#![cfg_attr(not(feature = "gpu"), deny(unsafe_code))]

use clap::{Parser, Subcommand, ValueEnum};
use serde::Serialize;
use std::time::Instant;
use std::{fs, path::PathBuf};
use telomere::{
    build_seed_index_to_dir, decompress_with_limit, estimate_streaming_target_chunk_upper_bound,
    estimate_streaming_target_table_upper_bound, estimate_target_table_chunk_upper_bound_for_tiers,
    estimate_target_table_upper_bound_for_tiers, read_index_manifest, Config, HasherKind,
    IndexConfig, MmapSeedExpansionIndex, PassStats, RunSummary, TelomereError,
};
use tracing::{error, info, warn};

#[derive(Parser)]
#[command(name = "telomere", author, version, about)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Compress a file
    #[command(alias = "c")]
    Compress(CompressArgs),
    /// Decompress a file
    #[command(alias = "d")]
    Decompress(DecompressArgs),
    /// Build and inspect experimental seed expansion indexes
    Index(IndexArgs),
}

#[derive(clap::Args)]
struct IndexArgs {
    #[command(subcommand)]
    command: IndexCommand,
}

#[derive(Subcommand)]
enum IndexCommand {
    /// Build an exact generated-prefix seed index
    Build(IndexBuildArgs),
    /// Print index manifest JSON
    Info(IndexPathArgs),
    /// Verify index manifest and sorted tier files
    Verify(IndexPathArgs),
}

#[derive(clap::Args)]
struct IndexBuildArgs {
    /// Output directory for manifest.json and tier files
    #[arg(long)]
    output: PathBuf,

    /// Hash function
    #[arg(long, value_enum, default_value_t = ArgHasher::Blake3)]
    hasher: ArgHasher,

    /// Max seed length in bytes
    #[arg(long, default_value_t = 1)]
    max_seed_len: usize,

    /// Maximum generated prefix/span length in bytes
    #[arg(long)]
    max_span_len: usize,

    /// Span tier step in bytes
    #[arg(long, default_value_t = 4)]
    block_size: usize,
}

#[derive(clap::Args)]
struct IndexPathArgs {
    /// Index directory
    path: PathBuf,
}

#[derive(clap::Args)]
struct CompressArgs {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,

    /// Max seed length in bytes (1-3 for MVP; larger values are exponentially slower)
    #[arg(long, default_value_t = 1)]
    seed_depth: usize,

    /// Experimental streaming/v2 seed budget as the first 2^N canonical seeds
    #[arg(long)]
    seed_bits: Option<usize>,

    /// Max compression passes
    #[arg(long, default_value_t = 1)]
    passes: u32,

    /// Save checkpoint every N minutes
    #[arg(long, default_value_t = 10)]
    checkpoint_every: u32,

    /// Max RAM usage (e.g. "4GB", "80%")
    #[arg(long, default_value = "80%")]
    memory_limit: String,

    /// Hash function
    #[arg(long, value_enum, default_value_t = ArgHasher::Blake3)]
    hasher: ArgHasher,

    /// Resume from checkpoint file
    #[arg(long)]
    resume: Option<PathBuf>,

    /// Verify output after compression
    #[arg(long)]
    verify: bool,

    /// Overwrite existing output
    #[arg(long)]
    force: bool,

    /// Print JSON summary of per-pass statistics to stdout
    #[arg(long)]
    json: bool,

    /// Block size in bytes
    #[arg(long, default_value_t = 4)]
    block_size: usize,

    /// Compression engine
    #[arg(long, value_enum, default_value_t = EngineKind::Brute)]
    engine: EngineKind,

    /// Container format
    #[arg(long, value_enum, default_value_t = FormatKind::V1)]
    format: FormatKind,

    /// Existing seed expansion index directory for indexed/v2 compression
    #[arg(long)]
    index: Option<PathBuf>,

    /// Maximum indexed/streaming span length in bytes
    #[arg(long)]
    max_span_len: Option<usize>,

    /// Byte step between candidate span starts for indexed/streaming v2
    #[arg(long)]
    span_step: Option<usize>,

    /// Limit selected span records emitted in --json engine telemetry
    #[arg(long)]
    telemetry_limit: Option<usize>,

    /// Experimental streaming/v2 target-table byte budget per chunk
    #[arg(long)]
    target_chunk_bytes: Option<String>,

    /// Experimental reversible preconditioner for streaming/v2 research
    #[arg(long, value_enum, default_value_t = TransformKind::None)]
    transform: TransformKind,
}

#[derive(clap::Args)]
struct DecompressArgs {
    /// Input file path
    input: PathBuf,
    /// Output file path
    output: PathBuf,

    /// Overwrite existing output
    #[arg(long)]
    force: bool,

    /// Hash function override for legacy files; v1/v2 files select the hasher from the header
    #[arg(long, value_enum, default_value_t = ArgHasher::Blake3)]
    hasher: ArgHasher,

    /// Max decompressed output / intermediate layer allocation (e.g. "4GB", "80%")
    #[arg(long, default_value = "80%")]
    memory_limit: String,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum ArgHasher {
    Blake3,
    Sha256,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum EngineKind {
    #[value(alias = "brute-force")]
    Brute,
    Indexed,
    Streaming,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum FormatKind {
    V1,
    V2,
}

#[derive(ValueEnum, Clone, Copy, Debug, PartialEq, Eq)]
enum TransformKind {
    None,
    PublicPresetSelective,
}

#[derive(Serialize)]
struct EngineJsonSummary<'a, T: Serialize> {
    #[serde(flatten)]
    summary: &'a RunSummary,
    engine_telemetry: &'a T,
}

impl From<ArgHasher> for HasherKind {
    fn from(val: ArgHasher) -> Self {
        match val {
            ArgHasher::Blake3 => HasherKind::Blake3,
            ArgHasher::Sha256 => HasherKind::Sha256,
        }
    }
}

fn main() {
    tracing_subscriber::fmt()
        .with_writer(std::io::stderr)
        .init();

    if let Err(e) = run() {
        error!("Fatal error: {}", e);
        eprintln!("Fatal error: {}", e);
        std::process::exit(1);
    }
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Compress(args) => compress_command(args),
        Commands::Decompress(args) => decompress_command(args),
        Commands::Index(args) => index_command(args),
    }
}

fn compress_command(args: CompressArgs) -> Result<(), Box<dyn std::error::Error>> {
    if args.resume.is_some() {
        warn!("Resume functionality not yet implemented");
    }

    if args.span_step.is_some()
        && !matches!(
            (args.engine, args.format),
            (EngineKind::Indexed | EngineKind::Streaming, FormatKind::V2)
        )
    {
        return Err("--span-step is supported only by indexed/streaming v2 compression".into());
    }
    if args.target_chunk_bytes.is_some()
        && !matches!(
            (args.engine, args.format),
            (EngineKind::Indexed | EngineKind::Streaming, FormatKind::V2)
        )
    {
        return Err(
            "--target-chunk-bytes is supported only by indexed/streaming v2 compression".into(),
        );
    }
    if args.transform != TransformKind::None
        && !matches!(
            (args.engine, args.format),
            (EngineKind::Streaming, FormatKind::V2)
        )
    {
        return Err("--transform is supported only by streaming v2 compression".into());
    }
    if args.seed_bits.is_some()
        && !matches!(
            (args.engine, args.format),
            (EngineKind::Streaming, FormatKind::V2)
        )
    {
        return Err("--seed-bits is supported only by streaming v2 compression".into());
    }

    if args.output.exists() && !args.force {
        return Err(format!(
            "Output file {:?} exists (use --force to overwrite)",
            args.output
        )
        .into());
    }

    let memory_limit_bytes = parse_memory_limit(&args.memory_limit)?;
    let hasher: HasherKind = args.hasher.into();
    let config = Config {
        block_size: args.block_size,
        max_seed_len: args.seed_depth,
        max_arity: 5,
        hash_bits: 13,
        hasher,
        seed_expansions: std::collections::HashMap::new(),
        enable_superposition: false,
        memory_limit: memory_limit_bytes,
    };
    config.validate()?;
    let seed_limit = args
        .seed_bits
        .map(telomere::seed_limit_from_bits)
        .transpose()?;

    let input_data = fs::read(&args.input)?;
    info!(
        "Compressing {} bytes with engine={:?} format={:?} seed_depth={} passes={}...",
        input_data.len(),
        args.engine,
        args.format,
        args.seed_depth,
        args.passes
    );

    let started = Instant::now();
    let out = match (args.engine, args.format) {
        (EngineKind::Brute, FormatKind::V1) => {
            let (out, summary) =
                telomere::compress_with_run_summary(&input_data, &config, args.passes as usize)?;
            emit_summary(&summary, args.json);
            out
        }
        (EngineKind::Indexed, FormatKind::V2) => {
            let index_path = args
                .index
                .as_ref()
                .ok_or("--index is required for --engine indexed --format v2")?;
            let index = MmapSeedExpansionIndex::open_dir(index_path)?;
            let max_span_len = args
                .max_span_len
                .unwrap_or_else(|| index.manifest().max_span_len);
            let span_step = args.span_step.unwrap_or(args.block_size);
            let tier_lengths: Vec<usize> = index
                .manifest()
                .tiers
                .iter()
                .map(|tier| tier.span_len)
                .filter(|span_len| *span_len <= max_span_len)
                .collect();
            let target_chunk_bytes = args
                .target_chunk_bytes
                .as_deref()
                .map(parse_memory_limit)
                .transpose()?;
            let (out, telemetry) = if let Some(target_chunk_bytes) = target_chunk_bytes {
                enforce_target_table_memory_limit(
                    "indexed chunk",
                    estimate_target_table_chunk_upper_bound_for_tiers(
                        input_data.len(),
                        &tier_lengths,
                        span_step,
                        target_chunk_bytes,
                    )?,
                    config.memory_limit,
                )?;
                telomere::compress_indexed_v2_with_chunked_span_step_and_telemetry(
                    &input_data,
                    &index,
                    hasher,
                    args.seed_depth,
                    max_span_len,
                    args.block_size,
                    span_step,
                    args.passes as usize,
                    config.hash_bits,
                    target_chunk_bytes,
                )?
            } else {
                enforce_target_table_memory_limit(
                    "indexed",
                    estimate_target_table_upper_bound_for_tiers(
                        input_data.len(),
                        &tier_lengths,
                        span_step,
                    ),
                    config.memory_limit,
                )?;
                telomere::compress_indexed_v2_with_span_step_and_telemetry(
                    &input_data,
                    &index,
                    hasher,
                    args.seed_depth,
                    max_span_len,
                    args.block_size,
                    span_step,
                    args.passes as usize,
                    config.hash_bits,
                )?
            };
            let summary = one_pass_summary(input_data.len(), out.len(), started);
            emit_summary_with_telemetry(&summary, &telemetry, args.json, args.telemetry_limit);
            out
        }
        (EngineKind::Streaming, FormatKind::V2) => {
            let max_span_len = args
                .max_span_len
                .unwrap_or(args.block_size * config.max_arity as usize);
            let span_step = args.span_step.unwrap_or(args.block_size);
            let target_chunk_bytes = args
                .target_chunk_bytes
                .as_deref()
                .map(parse_memory_limit)
                .transpose()?;
            if args.transform == TransformKind::PublicPresetSelective {
                let estimated_len = input_data.len().saturating_add(
                    input_data
                        .len()
                        .checked_div(u16::MAX as usize)
                        .unwrap_or(0)
                        .saturating_mul(3)
                        .saturating_add(3),
                );
                enforce_target_table_memory_limit(
                    "streaming public-preset-selective",
                    estimate_streaming_target_table_upper_bound(
                        estimated_len,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                    )?,
                    config.memory_limit,
                )?;
                let (out, telemetry) =
                    telomere::compress_streaming_v2_with_public_preset_selective_and_telemetry(
                        &input_data,
                        hasher,
                        args.seed_depth,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        args.passes as usize,
                        config.hash_bits,
                        target_chunk_bytes,
                        seed_limit,
                    )?;
                let summary = one_pass_summary(input_data.len(), out.len(), started);
                emit_summary_with_telemetry(&summary, &telemetry, args.json, args.telemetry_limit);
                out
            } else if let Some(target_chunk_bytes) = target_chunk_bytes {
                enforce_target_table_memory_limit(
                    "streaming chunk",
                    estimate_streaming_target_chunk_upper_bound(
                        input_data.len(),
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        target_chunk_bytes,
                    )?,
                    config.memory_limit,
                )?;
                let (out, telemetry) = if let Some(seed_limit) = seed_limit {
                    telomere::compress_streaming_v2_with_seed_limit_and_telemetry(
                        &input_data,
                        hasher,
                        seed_limit,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        args.passes as usize,
                        config.hash_bits,
                        Some(target_chunk_bytes),
                    )?
                } else {
                    telomere::compress_streaming_v2_with_chunked_span_step_and_telemetry(
                        &input_data,
                        hasher,
                        args.seed_depth,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        args.passes as usize,
                        config.hash_bits,
                        target_chunk_bytes,
                    )?
                };
                let summary = one_pass_summary(input_data.len(), out.len(), started);
                emit_summary_with_telemetry(&summary, &telemetry, args.json, args.telemetry_limit);
                out
            } else {
                enforce_target_table_memory_limit(
                    "streaming",
                    estimate_streaming_target_table_upper_bound(
                        input_data.len(),
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                    )?,
                    config.memory_limit,
                )?;
                let (out, telemetry) = if let Some(seed_limit) = seed_limit {
                    telomere::compress_streaming_v2_with_seed_limit_and_telemetry(
                        &input_data,
                        hasher,
                        seed_limit,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        args.passes as usize,
                        config.hash_bits,
                        None,
                    )?
                } else {
                    telomere::compress_streaming_v2_with_span_step_and_telemetry(
                        &input_data,
                        hasher,
                        args.seed_depth,
                        max_span_len,
                        args.block_size,
                        span_step,
                        config.max_arity,
                        args.passes as usize,
                        config.hash_bits,
                    )?
                };
                let summary = one_pass_summary(input_data.len(), out.len(), started);
                emit_summary_with_telemetry(&summary, &telemetry, args.json, args.telemetry_limit);
                out
            }
        }
        (EngineKind::Brute, FormatKind::V2) => {
            return Err("--format v2 requires --engine indexed or --engine streaming".into());
        }
        (_, FormatKind::V1) => {
            return Err("--format v1 is supported only by --engine brute".into());
        }
    };

    if args.verify {
        info!("Verifying...");
        let decompressed = decompress_with_limit(&out, &config, usize::MAX)?;
        if decompressed != input_data {
            return Err("Verification failed: data mismatch".into());
        }
        info!("Verification successful");
    }

    fs::write(&args.output, &out)?;
    info!("Wrote {} bytes to {:?}", out.len(), args.output);
    Ok(())
}

fn decompress_command(args: DecompressArgs) -> Result<(), Box<dyn std::error::Error>> {
    if args.output.exists() && !args.force {
        return Err(format!(
            "Output file {:?} exists (use --force to overwrite)",
            args.output
        )
        .into());
    }
    let ext = args
        .input
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("");
    if ext != "tlmr" {
        return Err(format!(
            "Invalid file extension '.{}' — input must be a .tlmr file",
            ext
        )
        .into());
    }

    let input_data = fs::read(&args.input)?;
    let _hasher_override: HasherKind = args.hasher.into();
    let memory_limit_bytes = parse_memory_limit(&args.memory_limit)?;
    let config = Config {
        memory_limit: memory_limit_bytes,
        ..Default::default()
    };

    info!("Decompressing...");
    let out = decompress_with_limit(&input_data, &config, usize::MAX).map_err(|err| {
        let detail = err.to_string();
        if detail.contains("limit") {
            format!("Decompression exceeded --memory-limit {memory_limit_bytes} bytes: {detail}")
        } else {
            "File appears corrupt or truncated. Verify the file is intact.".into()
        }
    })?;

    fs::write(&args.output, &out)?;
    info!("Wrote decompressed data to {:?}", args.output);
    Ok(())
}

fn index_command(args: IndexArgs) -> Result<(), Box<dyn std::error::Error>> {
    match args.command {
        IndexCommand::Build(args) => {
            let tier_lengths = tier_lengths(args.block_size, args.max_span_len)?;
            let config = IndexConfig {
                hasher: args.hasher.into(),
                max_seed_len: args.max_seed_len,
                max_span_len: args.max_span_len,
                tier_lengths,
            };
            let manifest = build_seed_index_to_dir(&config, &args.output)?;
            println!("{}", serde_json::to_string_pretty(&manifest)?);
        }
        IndexCommand::Info(args) => {
            let manifest = read_index_manifest(&args.path)?;
            println!("{}", serde_json::to_string_pretty(&manifest)?);
        }
        IndexCommand::Verify(args) => {
            let manifest = MmapSeedExpansionIndex::verify_dir(&args.path)?;
            println!("{}", serde_json::to_string_pretty(&manifest)?);
        }
    }
    Ok(())
}

fn emit_summary(summary: &RunSummary, json: bool) {
    if json {
        println!("{}", summary.to_json());
    } else {
        summary.print_summary();
    }
}

fn emit_summary_with_telemetry<T: Serialize>(
    summary: &RunSummary,
    telemetry: &T,
    json: bool,
    telemetry_limit: Option<usize>,
) {
    if json {
        let payload = EngineJsonSummary {
            summary,
            engine_telemetry: telemetry,
        };
        let mut value = match serde_json::to_value(&payload) {
            Ok(value) => value,
            Err(e) => {
                println!("{{\"error\":\"{}\"}}", e);
                return;
            }
        };
        if let Some(limit) = telemetry_limit {
            apply_telemetry_limit(&mut value, limit);
        }
        println!(
            "{}",
            serde_json::to_string_pretty(&value)
                .unwrap_or_else(|e| format!("{{\"error\":\"{}\"}}", e))
        );
    } else {
        summary.print_summary();
    }
}

fn apply_telemetry_limit(value: &mut serde_json::Value, limit: usize) {
    let Some(engine) = value.get_mut("engine_telemetry") else {
        return;
    };
    truncate_selected_spans(engine, limit);
    if let Some(layers) = engine
        .get_mut("layers")
        .and_then(serde_json::Value::as_array_mut)
    {
        for layer in layers {
            truncate_selected_spans(layer, limit);
        }
    }
}

fn truncate_selected_spans(value: &mut serde_json::Value, limit: usize) {
    let Some(object) = value.as_object_mut() else {
        return;
    };
    let Some(spans) = object
        .get_mut("selected_spans")
        .and_then(serde_json::Value::as_array_mut)
    else {
        return;
    };
    let total = spans.len();
    if total > limit {
        spans.truncate(limit);
    }
    object.insert("selected_spans_total".into(), serde_json::json!(total));
    object.insert(
        "selected_spans_omitted".into(),
        serde_json::json!(total.saturating_sub(limit)),
    );
}

fn one_pass_summary(original_bytes: usize, final_bytes: usize, started: Instant) -> RunSummary {
    RunSummary::new(
        original_bytes,
        vec![PassStats::new(
            1,
            original_bytes,
            final_bytes,
            started.elapsed(),
        )],
    )
}

fn tier_lengths(block_size: usize, max_span_len: usize) -> Result<Vec<usize>, TelomereError> {
    if block_size == 0 || max_span_len == 0 {
        return Err(TelomereError::Config(
            "block_size and max_span_len must be greater than zero".into(),
        ));
    }
    if block_size > max_span_len {
        return Err(TelomereError::Config(
            "block_size must not exceed max_span_len".into(),
        ));
    }
    Ok((block_size..=max_span_len).step_by(block_size).collect())
}

fn enforce_target_table_memory_limit(
    engine: &str,
    estimated_bytes: usize,
    memory_limit: usize,
) -> Result<(), Box<dyn std::error::Error>> {
    if estimated_bytes > memory_limit {
        return Err(format!(
            "estimated {engine} target table memory {estimated_bytes} bytes exceeds --memory-limit {memory_limit} bytes; lower --max-span-len, increase --span-step, split the input, or raise --memory-limit"
        )
        .into());
    }
    Ok(())
}

fn parse_memory_limit(s: &str) -> Result<usize, Box<dyn std::error::Error>> {
    use sysinfo::{System, SystemExt};

    let s = s.trim().to_uppercase();
    if s.ends_with('%') {
        let pct = s.trim_end_matches('%').parse::<f64>()?;
        if !(0.0..=100.0).contains(&pct) || pct == 0.0 {
            return Err("memory percentage must be in 0..=100".into());
        }
        let mut sys = System::new();
        sys.refresh_memory();
        Ok((sys.total_memory() as f64 * pct / 100.0) as usize)
    } else {
        let mut mul = 1.0;
        let num_str;
        if s.ends_with("GB") {
            mul = 1e9;
            num_str = s.trim_end_matches("GB");
        } else if s.ends_with("MB") {
            mul = 1e6;
            num_str = s.trim_end_matches("MB");
        } else if s.ends_with("KB") {
            mul = 1e3;
            num_str = s.trim_end_matches("KB");
        } else {
            num_str = &s;
        }
        let val = num_str.parse::<f64>()?;
        if val <= 0.0 {
            return Err("memory limit must be greater than zero".into());
        }
        Ok((val * mul) as usize)
    }
}
