#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! Telomere operator console — Tauri host.

use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};
use std::time::Instant;

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

use telomere::{
    build_seed_index_to_dir, compress_indexed_v2_with_telemetry, compress_multi_pass_with_config,
    compress_streaming_v2_with_telemetry, decode_tlmr_header, decode_tlmr_v2_header,
    decode_tlmr_v2_layer_descriptors, decompress_with_limit, read_index_manifest, Config,
    HasherKind, IndexConfig, MmapSeedExpansionIndex, SelectedSpanTelemetry, TelomereError,
    TLMR_V2_FORMAT_VERSION,
};

#[derive(Debug, Clone, Deserialize)]
pub struct UiConfig {
    pub block_size: usize,
    pub max_seed_len: usize,
    pub passes: usize,
    pub hash_bits: usize,
    pub max_arity: u8,
    pub hasher: String,
    pub engine: Option<String>,
    pub format: Option<String>,
    pub index_path: Option<String>,
    pub max_span_len: Option<usize>,
}

impl UiConfig {
    fn hasher_kind(&self) -> Result<HasherKind, String> {
        parse_hasher(&self.hasher)
    }

    fn into_engine(&self) -> Result<Config, String> {
        Ok(Config {
            block_size: self.block_size,
            max_seed_len: self.max_seed_len,
            max_arity: self.max_arity,
            hash_bits: self.hash_bits,
            hasher: self.hasher_kind()?,
            ..Default::default()
        })
    }
}

#[derive(Debug, Serialize)]
pub struct FileStat {
    pub name: String,
    pub size: u64,
}

#[derive(Debug, Serialize)]
pub struct PassStatsDto {
    pub pass: usize,
    pub bytes_out: usize,
    pub delta_pct: f64,
    pub hits: u64,
}

#[derive(Debug, Serialize)]
pub struct SeedDistDto {
    pub l0: u64,
    pub l1: u64,
    pub l2: u64,
    pub l3: u64,
}

#[derive(Debug, Serialize)]
pub struct CompressResult {
    pub kind: &'static str,
    pub run_id: u64,
    pub source_name: String,
    pub bytes_in: usize,
    pub bytes_out: usize,
    pub passes: Vec<PassStatsDto>,
    pub duration_ms: u64,
    pub candidate_count: u64,
    pub hits_total: u64,
    pub literal_bytes: usize,
    pub blocks: usize,
    pub seed_dist: SeedDistDto,
    pub bundles: u64,
    pub tier_hits: u64,
    pub lattice: Vec<LatticeCellDto>,
    pub verified: Option<bool>,
    pub hasher: String,
    pub engine: String,
    pub format: String,
    pub config: ConfigEcho,
    pub engine_telemetry: serde_json::Value,
}

#[derive(Debug, Serialize)]
pub struct ConfigEcho {
    pub block_size: usize,
    pub max_seed_len: usize,
    pub passes: usize,
    pub hash_bits: usize,
    pub max_arity: u8,
    pub hasher: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct LatticeCellDto {
    pub bin: String,
    pub pass: usize,
    pub depth: f64,
    #[serde(rename = "seedIdx")]
    pub seed_idx: Option<usize>,
    pub bundle: Option<String>,
    #[serde(rename = "seedHex")]
    pub seed_hex: Option<String>,
    #[serde(rename = "hashPrefix")]
    pub hash_prefix: String,
    #[serde(rename = "spanLen")]
    pub span_len: Option<usize>,
    pub savings: Option<usize>,
}

#[derive(Debug, Serialize)]
pub struct HeaderDto {
    pub version: u8,
    pub hasher: String,
    pub block_size: usize,
    pub max_seed_len: usize,
    pub hash_bits: usize,
    pub max_arity: u8,
}

#[derive(Debug, Serialize)]
pub struct DecompressResult {
    pub kind: &'static str,
    pub run_id: u64,
    pub source_name: String,
    pub bytes_in: usize,
    pub bytes_out: usize,
    pub duration_ms: u64,
    pub header: HeaderDto,
}

#[derive(Debug, Serialize)]
pub struct IndexResult {
    pub kind: &'static str,
    pub path: String,
    pub manifest: serde_json::Value,
}

#[derive(Debug, Serialize)]
pub struct ResearchArtifactCard {
    pub id: &'static str,
    pub title: &'static str,
    pub status: String,
    pub headline: String,
    pub metric: String,
    pub source: &'static str,
}

#[derive(Debug, Serialize)]
pub struct ResearchEvidenceSummary {
    pub top_ready_lane: String,
    pub ready_count: u64,
    pub gated_count: u64,
    pub blocked_by_evidence_count: u64,
    pub frontier_status: String,
    pub frontier_unresolved_count: u64,
    pub frontier_ungated_compute_allowed: bool,
    pub frontier_allowed_maintenance_only: bool,
    pub frontier_broad_depth_search_allowed: bool,
    pub frontier_best_non_planted_gib: f64,
    pub frontier_long_span_gate_met_count: u64,
    pub frontier_long_span_gate_count: u64,
    pub frontier_count: u64,
    pub research_team_protocol_status: String,
    pub research_team_ready_dispatch_count: u64,
    pub research_team_brief_count: u64,
    pub research_team_work_package_count: u64,
    pub research_team_forbidden_action_count: u64,
    pub research_team_maintenance_only: bool,
    pub goal_completion_objective_status: String,
    pub goal_completion_recommendation: String,
    pub goal_completion_production_proven: bool,
    pub goal_completion_unresolved_evidence_gates: u64,
    pub goal_completion_requirements_total: u64,
    pub goal_completion_requirements_blocked_by_evidence: u64,
    pub blocked_dispatch_status: String,
    pub blocked_dispatch_requirement_count: u64,
    pub blocked_dispatch_brief_count: u64,
    pub blocked_dispatch_parallel_group_count: u64,
    pub blocked_dispatch_ready_dispatch_count: u64,
    pub blocked_dispatch_forbidden_action_count: u64,
    pub blocked_dispatch_ungated_compute_allowed: bool,
    pub blocked_dispatch_research_decision: String,
    pub natural_corpus_status: String,
    pub natural_corpus_proven: bool,
    pub natural_corpus_gate_count: u64,
    pub natural_corpus_qualified_count: u64,
    pub natural_corpus_blocked_gate_count: u64,
    pub natural_corpus_heldout_corpus_count: u64,
    pub natural_corpus_heldout_prefix5_rows: u64,
    pub natural_corpus_heldout_exact_hit_rows: u64,
    pub natural_corpus_heldout_selected_span_rows: u64,
    pub natural_corpus_match_target_spans: u64,
    pub natural_corpus_match_selected_span_rows: u64,
    pub natural_corpus_best_non_planted_gib: f64,
    pub production_status: String,
    pub production_proven: bool,
    pub production_gate_count: u64,
    pub production_qualified_count: u64,
    pub production_blocked_gate_count: u64,
    pub production_runtime_required_count: u64,
    pub production_real_gpu_kernel_detected: bool,
    pub production_scale_next_double_peak_mib: f64,
    pub current_scale_mib: String,
    pub heldout_prefix4_win_corpora: u64,
    pub heldout_exact_hits: u64,
    pub heldout_expansion_corpora: u64,
    pub heldout_expansion_missing_matrix: u64,
    pub heldout_expansion_prefix5_rows: u64,
    pub heldout_expansion_exact_hit_rows: u64,
    pub heldout_expansion_selected_span_rows: u64,
    pub shadow_prefix4_win_corpora: u64,
    pub binary_exact_hits: u64,
    pub match_target_spans: u64,
    pub match_selected_spans: u64,
    pub lead_exact_target_spans: u64,
    pub lead_exact_hits: u64,
    pub lead_selected_spans: u64,
    pub exact_short_verified_hits: u64,
    pub exact_short_best_delta_bytes: i64,
    pub exact_short_full_stream_negative_groups: u64,
    pub exact_short_control_negative_groups: u64,
    pub exact_short_promotion_met: bool,
    pub whole_stream_honest_rows: u64,
    pub whole_stream_honest_negative_rows: u64,
    pub whole_stream_ordinary_negative_groups: u64,
    pub whole_stream_control_negative_groups: u64,
    pub whole_stream_best_honest_delta_bytes: i64,
    pub whole_stream_promotion_met: bool,
    pub expander_salt_exact_hits: u64,
    pub expander_salt_expected_exact_hits: f64,
    pub expander_salt_selected_span_rows: u64,
    pub expander_salt_full_stream_negative_rows: u64,
    pub expander_salt_random_multiplier_exceeded: bool,
    pub expander_salt_promotion_met: bool,
    pub schema_native_family_selected_spans: u64,
    pub schema_native_ordinary_negative_groups: u64,
    pub schema_native_control_negative_groups: u64,
    pub schema_native_wrong_schema_negative_groups: u64,
    pub schema_native_random_negative_groups: u64,
    pub schema_native_shadow_negative_groups: u64,
    pub schema_native_promotion_met: bool,
    pub schema_replication_selected_spans: u64,
    pub schema_replication_ordinary_negative_groups: u64,
    pub schema_replication_control_negative_groups: u64,
    pub schema_replication_generic_negative_groups: u64,
    pub schema_replication_claim_level: String,
    pub schema_replication_promotion_met: bool,
    pub superposition_retained_alternatives: u64,
    pub superposition_weighted_extra_savings: i64,
    pub superposition_unexplained_discards: u64,
    pub superposition_promotion_met: bool,
    pub recursive_structured_ordinary_later_win_families: u64,
    pub recursive_structured_planted_offset_later_win_families: u64,
    pub recursive_structured_claim_level: String,
    pub recursive_structured_promotion_met: bool,
    pub scale_performance_largest_peak_memory_mib: f64,
    pub scale_performance_peak_table_ratio: f64,
    pub scale_performance_next_double_peak_mib: f64,
    pub scale_performance_promotion_met: bool,
    pub depth4_enumerated_seeds: u64,
    pub depth4_exact_hits: u64,
    pub depth4_selected_spans: u64,
    pub gpu_status: String,
    pub gpu_real_kernel_detected: bool,
}

#[derive(Debug, Serialize)]
pub struct ResearchArtifactsResult {
    pub kind: &'static str,
    pub verdict: String,
    pub overall_status: String,
    pub open_gates: Vec<String>,
    pub evidence: ResearchEvidenceSummary,
    pub cards: Vec<ResearchArtifactCard>,
}

struct EngineRun {
    bytes: Vec<u8>,
    candidate_count: usize,
    selected_hits: usize,
    literal_bytes: usize,
    bundles: usize,
    tier_hits: usize,
    selected_spans: Vec<SelectedSpanTelemetry>,
    seed_counts: Vec<u64>,
    telemetry: serde_json::Value,
}

static RUN_COUNTER: AtomicU64 = AtomicU64::new(41);

fn into_string<E: std::fmt::Display>(e: E) -> String {
    e.to_string()
}

fn engine_err(e: TelomereError) -> String {
    format!("engine: {e}")
}

fn name_of(path: &str) -> String {
    Path::new(path)
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| path.to_string())
}

fn emit_progress(app: &AppHandle, stage: &str, message: &str, pct: f64) {
    let _ = app.emit(
        "telomere://progress",
        serde_json::json!({ "stage": stage, "message": message, "pct": pct }),
    );
}

fn parse_hasher(value: &str) -> Result<HasherKind, String> {
    match value {
        "blake3" => Ok(HasherKind::Blake3),
        "sha256" => Ok(HasherKind::Sha256),
        other => Err(format!("unknown hasher '{other}'")),
    }
}

fn tier_lengths(block_size: usize, max_span_len: usize) -> Result<Vec<usize>, String> {
    if block_size == 0 || max_span_len == 0 {
        return Err("block_size and max_span_len must be greater than zero".into());
    }
    if block_size > max_span_len {
        return Err("block_size must not exceed max_span_len".into());
    }
    Ok((block_size..=max_span_len).step_by(block_size).collect())
}

fn manifest_json<T: Serialize>(value: &T) -> Result<serde_json::Value, String> {
    serde_json::to_value(value).map_err(into_string)
}

fn repo_docs_dir() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap_or_else(|| Path::new("."))
        .join("docs")
}

fn read_json_value(path: &Path) -> Result<serde_json::Value, String> {
    let text =
        std::fs::read_to_string(path).map_err(|e| format!("reading {}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("parsing {}: {e}", path.display()))
}

fn value_str(value: &serde_json::Value, key: &str, default: &str) -> String {
    value
        .get(key)
        .and_then(serde_json::Value::as_str)
        .unwrap_or(default)
        .to_string()
}

fn summary<'a>(value: &'a serde_json::Value, key: &str) -> Option<&'a serde_json::Value> {
    value.get("summary").and_then(|summary| summary.get(key))
}

fn summary_u64(value: &serde_json::Value, key: &str) -> u64 {
    summary(value, key)
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0)
}

fn summary_i64(value: &serde_json::Value, key: &str) -> i64 {
    summary(value, key)
        .and_then(serde_json::Value::as_i64)
        .unwrap_or(0)
}

fn summary_bool(value: &serde_json::Value, key: &str) -> bool {
    summary(value, key)
        .and_then(serde_json::Value::as_bool)
        .unwrap_or(false)
}

fn summary_f64(value: &serde_json::Value, key: &str) -> f64 {
    summary(value, key)
        .and_then(serde_json::Value::as_f64)
        .unwrap_or(0.0)
}

fn summary_str(value: &serde_json::Value, key: &str, default: &str) -> String {
    summary(value, key)
        .and_then(serde_json::Value::as_str)
        .unwrap_or(default)
        .to_string()
}

fn array_len(value: &serde_json::Value, key: &str) -> u64 {
    value
        .get(key)
        .and_then(serde_json::Value::as_array)
        .map(|items| items.len() as u64)
        .unwrap_or(0)
}

fn load_research_artifacts_from_docs(docs_dir: &Path) -> Result<ResearchArtifactsResult, String> {
    let goal = read_json_value(&docs_dir.join("goal_audit.json"))?;
    let queue = read_json_value(&docs_dir.join("experiment_queue.json"))?;
    let frontier = read_json_value(&docs_dir.join("research_frontier.json"))?;
    let research_team = read_json_value(&docs_dir.join("research_team_protocol.json"))?;
    let goal_completion = read_json_value(&docs_dir.join("goal_completion_audit.json"))?;
    let blocked_dispatch = read_json_value(&docs_dir.join("blocked_requirement_dispatch.json"))?;
    let natural_proof = read_json_value(&docs_dir.join("natural_corpus_proof_matrix.json"))?;
    let production_proof = read_json_value(&docs_dir.join("production_proof_matrix.json"))?;
    let scorecard = read_json_value(&docs_dir.join("research_scorecard.json"))?;
    let nearmiss = read_json_value(&docs_dir.join("nearmiss_forecast.json"))?;
    let validation = read_json_value(&docs_dir.join("transform_validation.json"))?;
    let heldout_expansion = read_json_value(&docs_dir.join("heldout_corpus_expansion.json"))?;
    let match_discovery = read_json_value(&docs_dir.join("match_discovery.json"))?;
    let lead_exact = read_json_value(&docs_dir.join("lead_exact_discovery.json"))?;
    let exact_short = read_json_value(&docs_dir.join("exact_short_hit_bundle_economics.json"))?;
    let whole_stream = read_json_value(&docs_dir.join("whole_stream_residual_vector_probe.json"))?;
    let expander_salt = read_json_value(&docs_dir.join("expander_salt_ensemble.json"))?;
    let schema_native = read_json_value(&docs_dir.join("schema_native_public_dictionaries.json"))?;
    let schema_replication =
        read_json_value(&docs_dir.join("schema_native_public_dictionary_replication.json"))?;
    let superposition = read_json_value(&docs_dir.join("superposition_telemetry.json"))?;
    let recursive_structured =
        read_json_value(&docs_dir.join("recursive_structured_fixtures.json"))?;
    let scale_performance = read_json_value(&docs_dir.join("scale_performance_report.json"))?;
    let depth4 = read_json_value(&docs_dir.join("depth4_pilot_shard.json"))?;
    let acceleration = read_json_value(&docs_dir.join("acceleration_report.json"))?;

    let open_gates = goal
        .get("unresolved_requirements")
        .or_else(|| goal.get("open_requirements"))
        .and_then(serde_json::Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(serde_json::Value::as_str)
                .map(str::to_string)
                .collect()
        })
        .unwrap_or_default();

    let goal_counts = goal
        .get("status_counts")
        .and_then(serde_json::Value::as_object)
        .cloned()
        .unwrap_or_default();
    let complete = goal_counts
        .get("complete")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0);
    let proved = goal_counts
        .get("proved")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0);
    let qualified = goal_counts
        .get("qualified")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0);
    let open = goal_counts
        .get("open")
        .and_then(serde_json::Value::as_u64)
        .unwrap_or(0);

    let accel_detected = acceleration
        .get("detected")
        .cloned()
        .unwrap_or(serde_json::Value::Null);
    let accel_status = value_str(&accel_detected, "status", "unknown");
    let real_kernel = accel_detected
        .get("real_kernel_detected")
        .and_then(serde_json::Value::as_bool)
        .unwrap_or(false);

    let evidence = ResearchEvidenceSummary {
        top_ready_lane: summary_str(&queue, "top_ready_lane", "none"),
        ready_count: summary_u64(&queue, "ready_count"),
        gated_count: summary_u64(&queue, "gated_count"),
        blocked_by_evidence_count: summary_u64(&queue, "blocked_by_evidence_count"),
        frontier_status: summary_str(&frontier, "frontier_status", "unknown"),
        frontier_unresolved_count: summary_u64(&frontier, "unresolved_count"),
        frontier_ungated_compute_allowed: summary_bool(&frontier, "ungated_compute_allowed"),
        frontier_allowed_maintenance_only: summary_bool(&frontier, "allowed_maintenance_only"),
        frontier_broad_depth_search_allowed: summary_bool(&frontier, "broad_depth_search_allowed"),
        frontier_best_non_planted_gib: summary_f64(
            &frontier,
            "best_non_planted_gib_for_one_expected_hit",
        ),
        frontier_long_span_gate_met_count: summary_u64(&frontier, "long_span_gate_met_count"),
        frontier_long_span_gate_count: summary_u64(&frontier, "long_span_gate_count"),
        frontier_count: array_len(&frontier, "frontiers"),
        research_team_protocol_status: summary_str(&research_team, "protocol_status", "unknown"),
        research_team_ready_dispatch_count: summary_u64(&research_team, "ready_dispatch_count"),
        research_team_brief_count: summary_u64(&research_team, "brief_count"),
        research_team_work_package_count: summary_u64(&research_team, "work_package_count"),
        research_team_forbidden_action_count: summary_u64(&research_team, "forbidden_action_count"),
        research_team_maintenance_only: summary_bool(&research_team, "maintenance_only"),
        goal_completion_objective_status: summary_str(
            &goal_completion,
            "objective_status",
            "unknown",
        ),
        goal_completion_recommendation: summary_str(
            &goal_completion,
            "completion_recommendation",
            "unknown",
        ),
        goal_completion_production_proven: summary_bool(&goal_completion, "production_proven"),
        goal_completion_unresolved_evidence_gates: summary_u64(
            &goal_completion,
            "unresolved_evidence_gates",
        ),
        goal_completion_requirements_total: summary_u64(&goal_completion, "requirements_total"),
        goal_completion_requirements_blocked_by_evidence: summary_u64(
            &goal_completion,
            "requirements_blocked_by_evidence",
        ),
        blocked_dispatch_status: summary_str(&blocked_dispatch, "dispatch_status", "unknown"),
        blocked_dispatch_requirement_count: summary_u64(
            &blocked_dispatch,
            "blocked_requirement_count",
        ),
        blocked_dispatch_brief_count: summary_u64(&blocked_dispatch, "brief_count"),
        blocked_dispatch_parallel_group_count: summary_u64(
            &blocked_dispatch,
            "parallel_group_count",
        ),
        blocked_dispatch_ready_dispatch_count: summary_u64(
            &blocked_dispatch,
            "ready_dispatch_count",
        ),
        blocked_dispatch_forbidden_action_count: summary_u64(
            &blocked_dispatch,
            "forbidden_action_count",
        ),
        blocked_dispatch_ungated_compute_allowed: summary_bool(
            &blocked_dispatch,
            "ungated_compute_allowed",
        ),
        blocked_dispatch_research_decision: summary_str(
            &blocked_dispatch,
            "research_decision",
            "unknown",
        ),
        natural_corpus_status: summary_str(&natural_proof, "natural_corpus_status", "unknown"),
        natural_corpus_proven: summary_bool(&natural_proof, "natural_corpus_proven"),
        natural_corpus_gate_count: summary_u64(&natural_proof, "gate_count"),
        natural_corpus_qualified_count: summary_u64(&natural_proof, "qualified_count"),
        natural_corpus_blocked_gate_count: summary_u64(&natural_proof, "blocked_by_evidence_count"),
        natural_corpus_heldout_corpus_count: summary_u64(&natural_proof, "heldout_corpus_count"),
        natural_corpus_heldout_prefix5_rows: summary_u64(&natural_proof, "heldout_prefix5_rows"),
        natural_corpus_heldout_exact_hit_rows: summary_u64(
            &natural_proof,
            "heldout_exact_hit_rows",
        ),
        natural_corpus_heldout_selected_span_rows: summary_u64(
            &natural_proof,
            "heldout_selected_span_rows",
        ),
        natural_corpus_match_target_spans: summary_u64(
            &natural_proof,
            "match_discovery_target_spans",
        ),
        natural_corpus_match_selected_span_rows: summary_u64(
            &natural_proof,
            "match_discovery_selected_span_rows",
        ),
        natural_corpus_best_non_planted_gib: summary_f64(
            &natural_proof,
            "best_non_planted_gib_for_one_expected_hit",
        ),
        production_status: summary_str(&production_proof, "production_status", "unknown"),
        production_proven: summary_bool(&production_proof, "production_proven"),
        production_gate_count: summary_u64(&production_proof, "gate_count"),
        production_qualified_count: summary_u64(&production_proof, "qualified_count"),
        production_blocked_gate_count: summary_u64(&production_proof, "blocked_by_evidence_count"),
        production_runtime_required_count: summary_u64(&production_proof, "runtime_required_count"),
        production_real_gpu_kernel_detected: summary_bool(
            &production_proof,
            "real_gpu_kernel_detected",
        ),
        production_scale_next_double_peak_mib: summary_f64(
            &production_proof,
            "scale_next_double_peak_memory_mib",
        ),
        current_scale_mib: summary_str(&queue, "current_scale_mib", "unknown"),
        heldout_prefix4_win_corpora: summary_u64(&validation, "heldout_prefix4_win_corpora"),
        heldout_exact_hits: summary_u64(&validation, "heldout_exact_hits"),
        heldout_expansion_corpora: summary_u64(&heldout_expansion, "corpus_count"),
        heldout_expansion_missing_matrix: summary_u64(
            &heldout_expansion,
            "missing_corpus_matrix_count",
        ),
        heldout_expansion_prefix5_rows: summary_u64(&heldout_expansion, "rows_with_prefix_ge_5"),
        heldout_expansion_exact_hit_rows: summary_u64(&heldout_expansion, "rows_with_exact_hits"),
        heldout_expansion_selected_span_rows: summary_u64(
            &heldout_expansion,
            "rows_with_selected_spans",
        ),
        shadow_prefix4_win_corpora: summary_u64(&validation, "shadow_prefix4_win_corpora"),
        binary_exact_hits: summary_u64(&validation, "binary_exact_hits"),
        match_target_spans: summary_u64(&match_discovery, "target_span_count"),
        match_selected_spans: summary_u64(&match_discovery, "total_selected_spans"),
        lead_exact_target_spans: summary_u64(&lead_exact, "target_span_count"),
        lead_exact_hits: summary_u64(&lead_exact, "total_exact_hits"),
        lead_selected_spans: summary_u64(&lead_exact, "total_selected_spans"),
        exact_short_verified_hits: summary_u64(&exact_short, "reconstructed_exact_hits"),
        exact_short_best_delta_bytes: summary_i64(&exact_short, "best_full_stream_delta_bytes"),
        exact_short_full_stream_negative_groups: summary_u64(
            &exact_short,
            "full_stream_ordinary_negative_groups",
        ),
        exact_short_control_negative_groups: summary_u64(
            &exact_short,
            "full_stream_control_negative_groups",
        ),
        exact_short_promotion_met: summary_bool(&exact_short, "promotion_met"),
        whole_stream_honest_rows: summary_u64(&whole_stream, "honest_encoded_rows"),
        whole_stream_honest_negative_rows: summary_u64(
            &whole_stream,
            "honest_full_stream_negative_rows",
        ),
        whole_stream_ordinary_negative_groups: summary_u64(
            &whole_stream,
            "ordinary_heldout_negative_groups",
        ),
        whole_stream_control_negative_groups: summary_u64(&whole_stream, "control_negative_groups"),
        whole_stream_best_honest_delta_bytes: summary_i64(&whole_stream, "best_honest_delta_bytes"),
        whole_stream_promotion_met: summary_bool(&whole_stream, "promotion_met"),
        expander_salt_exact_hits: summary_u64(&expander_salt, "salted_exact_hits"),
        expander_salt_expected_exact_hits: summary_f64(
            &expander_salt,
            "salted_expected_exact_hits",
        ),
        expander_salt_selected_span_rows: summary_u64(&expander_salt, "salted_selected_span_rows"),
        expander_salt_full_stream_negative_rows: summary_u64(
            &expander_salt,
            "full_stream_negative_rows",
        ),
        expander_salt_random_multiplier_exceeded: summary_bool(
            &expander_salt,
            "random_trial_multiplier_exceeded",
        ),
        expander_salt_promotion_met: summary_bool(&expander_salt, "promotion_met"),
        schema_native_family_selected_spans: summary_u64(&schema_native, "family_selected_spans"),
        schema_native_ordinary_negative_groups: summary_u64(
            &schema_native,
            "family_ordinary_heldout_negative_groups",
        ),
        schema_native_control_negative_groups: summary_u64(
            &schema_native,
            "family_control_negative_groups",
        ),
        schema_native_wrong_schema_negative_groups: summary_u64(
            &schema_native,
            "wrong_schema_ordinary_negative_groups",
        ),
        schema_native_random_negative_groups: summary_u64(
            &schema_native,
            "random_table_ordinary_negative_groups",
        ),
        schema_native_shadow_negative_groups: summary_u64(
            &schema_native,
            "shadow_ordinary_negative_groups",
        ),
        schema_native_promotion_met: summary_bool(&schema_native, "promotion_met"),
        schema_replication_selected_spans: summary_u64(
            &schema_replication,
            "standards_selected_spans",
        ),
        schema_replication_ordinary_negative_groups: summary_u64(
            &schema_replication,
            "standards_ordinary_negative_groups",
        ),
        schema_replication_control_negative_groups: summary_u64(
            &schema_replication,
            "standards_control_negative_groups",
        ),
        schema_replication_generic_negative_groups: summary_u64(
            &schema_replication,
            "generic_ordinary_negative_groups",
        ),
        schema_replication_claim_level: summary_str(&schema_replication, "claim_level", "unknown"),
        schema_replication_promotion_met: summary_bool(&schema_replication, "promotion_met"),
        superposition_retained_alternatives: summary_u64(
            &superposition,
            "retained_alternative_count",
        ),
        superposition_weighted_extra_savings: summary_i64(&superposition, "weighted_extra_savings"),
        superposition_unexplained_discards: summary_u64(
            &superposition,
            "unexplained_discard_count",
        ),
        superposition_promotion_met: summary_bool(&superposition, "promotion_met"),
        recursive_structured_ordinary_later_win_families: summary_u64(
            &recursive_structured,
            "ordinary_later_win_families",
        ),
        recursive_structured_planted_offset_later_win_families: summary_u64(
            &recursive_structured,
            "planted_offset_later_win_families",
        ),
        recursive_structured_claim_level: summary_str(
            &recursive_structured,
            "claim_level",
            "unknown",
        ),
        recursive_structured_promotion_met: summary_bool(&recursive_structured, "promotion_met"),
        scale_performance_largest_peak_memory_mib: summary_f64(
            &scale_performance,
            "largest_peak_memory_mib",
        ),
        scale_performance_peak_table_ratio: summary_f64(
            &scale_performance,
            "largest_peak_to_estimated_table_ratio",
        ),
        scale_performance_next_double_peak_mib: summary_f64(
            &scale_performance,
            "next_double_peak_memory_mib_at_current_ratio",
        ),
        scale_performance_promotion_met: summary_bool(&scale_performance, "promotion_met"),
        depth4_enumerated_seeds: summary_u64(&depth4, "enumerated_seed_count"),
        depth4_exact_hits: summary_u64(&depth4, "total_exact_hits"),
        depth4_selected_spans: summary_u64(&depth4, "total_selected_spans"),
        gpu_status: accel_status.clone(),
        gpu_real_kernel_detected: real_kernel,
    };

    Ok(ResearchArtifactsResult {
        kind: "research-artifacts",
        verdict: value_str(&goal, "verdict", "unknown"),
        overall_status: value_str(&goal, "overall_status", "unknown"),
        open_gates,
        evidence,
        cards: vec![
            ResearchArtifactCard {
                id: "goal-audit",
                title: "Goal Audit",
                status: value_str(&goal, "overall_status", "unknown"),
                headline: format!("{complete} complete, {proved} proved, {qualified} qualified, {open} open"),
                metric: format!("{} unresolved gates", goal.get("unresolved_count").and_then(serde_json::Value::as_u64).unwrap_or(0)),
                source: "docs/GOAL_AUDIT.md",
            },
            ResearchArtifactCard {
                id: "goal-completion-audit",
                title: "Completion Audit",
                status: summary_str(&goal_completion, "objective_status", "unknown"),
                headline:
                    "Active-goal completion remains blocked until natural-corpus or production proof exists."
                        .into(),
                metric: format!(
                    "{} recommendation, {} blocked of {} requirements",
                    summary_str(&goal_completion, "completion_recommendation", "unknown"),
                    summary_u64(&goal_completion, "requirements_blocked_by_evidence"),
                    summary_u64(&goal_completion, "requirements_total")
                ),
                source: "docs/GOAL_COMPLETION_AUDIT.md",
            },
            ResearchArtifactCard {
                id: "blocked-requirement-dispatch",
                title: "Blocked Dispatch",
                status: summary_str(&blocked_dispatch, "dispatch_status", "unknown"),
                headline:
                    "Blocked requirement briefs keep parallel agents in maintenance-only scopes."
                        .into(),
                metric: format!(
                    "{} briefs, {} blocked requirements, {} ready dispatches, ungated compute: {}",
                    summary_u64(&blocked_dispatch, "brief_count"),
                    summary_u64(&blocked_dispatch, "blocked_requirement_count"),
                    summary_u64(&blocked_dispatch, "ready_dispatch_count"),
                    summary_bool(&blocked_dispatch, "ungated_compute_allowed")
                ),
                source: "docs/BLOCKED_REQUIREMENT_DISPATCH.md",
            },
            ResearchArtifactCard {
                id: "natural-corpus-proof",
                title: "Natural Corpus Proof",
                status: summary_str(&natural_proof, "natural_corpus_status", "unknown"),
                headline:
                    "Non-planted viability remains blocked until held-out selected spans or negative delta survive controls."
                        .into(),
                metric: format!(
                    "{} blocked gates, {} held-out selected spans, {:.1} GiB forecast",
                    summary_u64(&natural_proof, "blocked_by_evidence_count"),
                    summary_u64(&natural_proof, "heldout_selected_span_rows"),
                    summary_f64(&natural_proof, "best_non_planted_gib_for_one_expected_hit")
                ),
                source: "docs/NATURAL_CORPUS_PROOF_MATRIX.md",
            },
            ResearchArtifactCard {
                id: "production-proof",
                title: "Production Proof",
                status: summary_str(&production_proof, "production_status", "unknown"),
                headline:
                    "Release-readiness remains blocked by v2 stability, acceleration value, natural workload evidence, and migration policy."
                        .into(),
                metric: format!(
                    "{} blocked gates, {} runtime-required gates, GPU kernel: {}",
                    summary_u64(&production_proof, "blocked_by_evidence_count"),
                    summary_u64(&production_proof, "runtime_required_count"),
                    summary_bool(&production_proof, "real_gpu_kernel_detected")
                ),
                source: "docs/PRODUCTION_PROOF_MATRIX.md",
            },
            ResearchArtifactCard {
                id: "scorecard",
                title: "Scorecard",
                status: value_str(&scorecard, "overall_status", "unknown"),
                headline: value_str(&scorecard, "verdict", "unknown"),
                metric: format!(
                    "{} open scorecard areas",
                    scorecard
                        .get("scorecard_status_counts")
                        .and_then(|counts| counts.get("open"))
                        .and_then(serde_json::Value::as_u64)
                        .unwrap_or(0)
                ),
                source: "docs/RESEARCH_SCORECARD.md",
            },
            ResearchArtifactCard {
                id: "queue",
                title: "Experiment Queue",
                status: summary_str(&queue, "top_ready_lane", "none"),
                headline: "Run ready experiments before gated compute or production GPU.".into(),
                metric: format!(
                    "{} ready, {} gated, {} blocked",
                    summary_u64(&queue, "ready_count"),
                    summary_u64(&queue, "gated_count"),
                    summary_u64(&queue, "blocked_by_evidence_count")
                ),
                source: "docs/EXPERIMENT_QUEUE.md",
            },
            ResearchArtifactCard {
                id: "research-frontier",
                title: "Research Frontier",
                status: summary_str(&frontier, "frontier_status", "unknown"),
                headline:
                    "Trigger board keeps gated compute closed until upstream evidence changes."
                        .into(),
                metric: format!(
                    "{} frontiers, ungated compute: {}, maintenance only: {}",
                    array_len(&frontier, "frontiers"),
                    summary_bool(&frontier, "ungated_compute_allowed"),
                    summary_bool(&frontier, "allowed_maintenance_only")
                ),
                source: "docs/RESEARCH_FRONTIER.md",
            },
            ResearchArtifactCard {
                id: "research-team-protocol",
                title: "Research Team",
                status: summary_str(&research_team, "protocol_status", "unknown"),
                headline:
                    "Dispatch briefs constrain parallel research work to safe, evidence-backed scopes."
                        .into(),
                metric: format!(
                    "{} briefs, {} ready dispatches, maintenance only: {}",
                    summary_u64(&research_team, "brief_count"),
                    summary_u64(&research_team, "ready_dispatch_count"),
                    summary_bool(&research_team, "maintenance_only")
                ),
                source: "docs/RESEARCH_TEAM_PROTOCOL.md",
            },
            ResearchArtifactCard {
                id: "near-miss",
                title: "Near-Miss Forecast",
                status: summary_str(&nearmiss, "best_non_planted_case", "none"),
                headline: "Current non-planted exact-hit scale remains too large for blind depth search.".into(),
                metric: format!(
                    "{:.3e} GiB per expected exact hit",
                    summary_f64(&nearmiss, "best_non_planted_gib_for_one_expected_hit")
                ),
                source: "docs/NEARMISS_FORECAST.md",
            },
            ResearchArtifactCard {
                id: "transform-validation",
                title: "Transform Validation",
                status: "held-out controls".into(),
                headline: "Shallow prefix motion exists, but exact seed-span wins have not survived held-out validation.".into(),
                metric: format!(
                    "{} prefix>=4 corpora, {} exact hits",
                    summary_u64(&validation, "heldout_prefix4_win_corpora"),
                    summary_u64(&validation, "heldout_exact_hits")
                ),
                source: "docs/TRANSFORM_VALIDATION.md",
            },
            ResearchArtifactCard {
                id: "heldout-expansion",
                title: "Held-Out Expansion",
                status: "frontier audit".into(),
                headline: "Frozen replication corpora stay separate until raw seed-frontier evidence changes.".into(),
                metric: format!(
                    "{} corpora missing, {} prefix>=5, {} selected",
                    summary_u64(&heldout_expansion, "missing_corpus_matrix_count"),
                    summary_u64(&heldout_expansion, "rows_with_prefix_ge_5"),
                    summary_u64(&heldout_expansion, "rows_with_selected_spans")
                ),
                source: "docs/HELDOUT_CORPUS_EXPANSION.md",
            },
            ResearchArtifactCard {
                id: "exact-discovery",
                title: "Exact Discovery",
                status: "selected-span gate".into(),
                headline: "Current natural-corpus discovery has not produced selected exact seed-span rows.".into(),
                metric: format!(
                    "{} match selected, {} lead exact, {} depth4 exact",
                    summary_u64(&match_discovery, "total_selected_spans"),
                    summary_u64(&lead_exact, "total_exact_hits"),
                    summary_u64(&depth4, "total_exact_hits")
                ),
                source: "docs/LEAD_EXACT_DISCOVERY.md",
            },
            ResearchArtifactCard {
                id: "exact-short-economics",
                title: "Short-Hit Economics",
                status: summary_str(&exact_short, "best_full_stream_layout", "none"),
                headline: "Span-3 short-hit bundling has negative rows, but controls block promotion.".into(),
                metric: format!(
                    "{} hits, best {} bytes, controls {}",
                    summary_u64(&exact_short, "reconstructed_exact_hits"),
                    summary_i64(&exact_short, "best_full_stream_delta_bytes"),
                    summary_u64(&exact_short, "full_stream_control_negative_groups")
                ),
                source: "docs/EXACT_SHORT_HIT_BUNDLE_ECONOMICS.md",
            },
            ResearchArtifactCard {
                id: "whole-stream-residual",
                title: "Residual Vector",
                status: summary_str(&whole_stream, "best_honest_case", "none"),
                headline: "Whole-stream residual vectors currently falsify residual-sidecar promotion.".into(),
                metric: format!(
                    "{} honest rows, {} negative, controls {}",
                    summary_u64(&whole_stream, "honest_encoded_rows"),
                    summary_u64(&whole_stream, "honest_full_stream_negative_rows"),
                    summary_u64(&whole_stream, "control_negative_groups")
                ),
                source: "docs/WHOLE_STREAM_RESIDUAL_VECTOR_PROBE.md",
            },
            ResearchArtifactCard {
                id: "expander-salt",
                title: "Expander Salts",
                status: summary_str(&expander_salt, "best_salted_case", "none"),
                headline: "Predeclared salted expanders currently behave like extra random trials.".into(),
                metric: format!(
                    "{} exact, {:.3} expected, {} selected rows",
                    summary_u64(&expander_salt, "salted_exact_hits"),
                    summary_f64(&expander_salt, "salted_expected_exact_hits"),
                    summary_u64(&expander_salt, "salted_selected_span_rows")
                ),
                source: "docs/EXPANDER_SALT_ENSEMBLE.md",
            },
            ResearchArtifactCard {
                id: "schema-native-dictionaries",
                title: "Schema Dictionaries",
                status: summary_str(&schema_native, "best_family_case", "none"),
                headline: "Frozen public schema dictionaries show a narrow dictionary-preset positive, not format support.".into(),
                metric: format!(
                    "{} selected, {} groups, controls {}/{}/{}",
                    summary_u64(&schema_native, "family_selected_spans"),
                    summary_u64(&schema_native, "family_ordinary_heldout_negative_groups"),
                    summary_u64(&schema_native, "family_control_negative_groups"),
                    summary_u64(&schema_native, "wrong_schema_ordinary_negative_groups"),
                    summary_u64(&schema_native, "random_table_ordinary_negative_groups")
                ),
                source: "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARIES.md",
            },
            ResearchArtifactCard {
                id: "schema-replication",
                title: "Schema Replication",
                status: summary_str(&schema_replication, "claim_level", "unknown"),
                headline: "Frozen replication blocks schema dictionary promotion because paired shadow controls also shrink.".into(),
                metric: format!(
                    "{} selected, {} groups, controls {}, generic {}",
                    summary_u64(&schema_replication, "standards_selected_spans"),
                    summary_u64(&schema_replication, "standards_ordinary_negative_groups"),
                    summary_u64(&schema_replication, "standards_control_negative_groups"),
                    summary_u64(&schema_replication, "generic_ordinary_negative_groups")
                ),
                source: "docs/SCHEMA_NATIVE_PUBLIC_DICTIONARY_REPLICATION.md",
            },
            ResearchArtifactCard {
                id: "superposition-telemetry",
                title: "Superposition",
                status: summary_str(&superposition, "claim_level", "unknown"),
                headline: "Candidate-lattice telemetry explains discarded alternatives without adding decoder-visible branching.".into(),
                metric: format!(
                    "{} retained, extra {}, unexplained {}",
                    summary_u64(&superposition, "retained_alternative_count"),
                    summary_i64(&superposition, "weighted_extra_savings"),
                    summary_u64(&superposition, "unexplained_discard_count")
                ),
                source: "docs/SUPERPOSITION_TELEMETRY.md",
            },
            ResearchArtifactCard {
                id: "recursive-structured-fixtures",
                title: "Recursive Fixtures",
                status: summary_str(&recursive_structured, "claim_level", "unknown"),
                headline: "Recursive v2 remains unpromoted outside planted offset controls.".into(),
                metric: format!(
                    "{} ordinary wins, {} planted-offset wins",
                    summary_u64(&recursive_structured, "ordinary_later_win_families"),
                    summary_u64(&recursive_structured, "planted_offset_later_win_families")
                ),
                source: "docs/RECURSIVE_STRUCTURED_FIXTURES.md",
            },
            ResearchArtifactCard {
                id: "scale-performance",
                title: "Scale Performance",
                status: summary_str(
                    &scale_performance,
                    "recommendation",
                    "unknown scale status",
                ),
                headline: "Planted-density scaling is interpretable but memory-heavy.".into(),
                metric: format!(
                    "peak {} MiB, ratio {}",
                    summary_f64(&scale_performance, "largest_peak_memory_mib"),
                    summary_f64(&scale_performance, "largest_peak_to_estimated_table_ratio")
                ),
                source: "docs/SCALE_PERFORMANCE.md",
            },
            ResearchArtifactCard {
                id: "acceleration",
                title: "Acceleration",
                status: accel_status,
                headline: "GPU remains research-only until real kernel parity and benchmark gates pass.".into(),
                metric: format!("real kernel detected: {real_kernel}"),
                source: "docs/ACCELERATION.md",
            },
        ],
    })
}

fn run_engine_for_ui(
    data: &[u8],
    cfg: &Config,
    engine: &str,
    format: &str,
    index_path: Option<&str>,
    max_span_len: usize,
    passes: usize,
) -> Result<EngineRun, TelomereError> {
    match (engine, format) {
        ("brute" | "brute-force", "v1") => {
            let (bytes, _) = compress_multi_pass_with_config(data, cfg, passes, false)?;
            Ok(EngineRun {
                bytes,
                candidate_count: 0,
                selected_hits: 0,
                literal_bytes: data.len(),
                bundles: 0,
                tier_hits: 0,
                selected_spans: Vec::new(),
                seed_counts: vec![0u64; 4],
                telemetry: serde_json::Value::Null,
            })
        }
        ("indexed", "v2") => {
            let path = index_path.ok_or_else(|| {
                TelomereError::Config("index_path is required for indexed/v2".into())
            })?;
            let index = MmapSeedExpansionIndex::open_dir(Path::new(path))?;
            let (bytes, telemetry) = compress_indexed_v2_with_telemetry(
                data,
                &index,
                cfg.hasher,
                cfg.max_seed_len,
                max_span_len,
                cfg.block_size,
                passes,
                cfg.hash_bits,
            )?;
            Ok(EngineRun {
                bytes,
                candidate_count: telemetry.candidate_count,
                selected_hits: telemetry.selected_count,
                literal_bytes: telemetry.literal_bytes,
                bundles: telemetry.bundle_count,
                tier_hits: telemetry.tiers.iter().map(|tier| tier.candidate_hits).sum(),
                selected_spans: telemetry.selected_spans.clone(),
                seed_counts: telemetry.seed_len_counts.clone(),
                telemetry: serde_json::to_value(&telemetry).unwrap_or(serde_json::Value::Null),
            })
        }
        ("streaming", "v2") => {
            let (bytes, telemetry) = compress_streaming_v2_with_telemetry(
                data,
                cfg.hasher,
                cfg.max_seed_len,
                max_span_len,
                cfg.block_size,
                cfg.max_arity,
                passes,
                cfg.hash_bits,
            )?;
            Ok(EngineRun {
                bytes,
                candidate_count: telemetry.candidate_count,
                selected_hits: telemetry.selected_count,
                literal_bytes: telemetry.literal_bytes,
                bundles: telemetry.bundle_count,
                tier_hits: telemetry.tiers.iter().map(|tier| tier.candidate_hits).sum(),
                selected_spans: telemetry.selected_spans.clone(),
                seed_counts: telemetry.seed_len_counts.clone(),
                telemetry: serde_json::to_value(&telemetry).unwrap_or(serde_json::Value::Null),
            })
        }
        ("brute" | "brute-force", "v2") => Err(TelomereError::Config(
            "v2 requires indexed or streaming engine".into(),
        )),
        (_, "v1") => Err(TelomereError::Config(
            "v1 is supported only by brute engine".into(),
        )),
        _ => Err(TelomereError::Config("unknown engine/format".into())),
    }
}

#[tauri::command]
fn stat_file(path: String) -> Result<FileStat, String> {
    let p = Path::new(&path);
    let meta = std::fs::metadata(p).map_err(into_string)?;
    Ok(FileStat {
        name: name_of(&path),
        size: meta.len(),
    })
}

#[derive(Debug, Serialize)]
pub struct PeekResult {
    pub bytes: Vec<u8>,
}

/// First `n` bytes of a file — backs the F8 source hex preview.
#[tauri::command]
fn peek_file(path: String, n: usize) -> Result<PeekResult, String> {
    use std::io::Read;
    let cap = n.min(4096);
    let mut f = std::fs::File::open(&path).map_err(into_string)?;
    let mut buf = vec![0u8; cap];
    let read = f.read(&mut buf).map_err(into_string)?;
    buf.truncate(read);
    Ok(PeekResult { bytes: buf })
}

#[tauri::command]
async fn index_build(
    app: AppHandle,
    output: String,
    hasher: String,
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
) -> Result<IndexResult, String> {
    emit_progress(&app, "running", "building index…", 5.0);
    let path = output.clone();
    let config = IndexConfig {
        hasher: parse_hasher(&hasher)?,
        max_seed_len,
        max_span_len,
        tier_lengths: tier_lengths(block_size, max_span_len)?,
    };
    let manifest =
        tokio::task::spawn_blocking(move || build_seed_index_to_dir(&config, Path::new(&path)))
            .await
            .map_err(into_string)?
            .map_err(engine_err)?;
    emit_progress(&app, "done", "index complete", 100.0);
    Ok(IndexResult {
        kind: "index-build",
        path: output,
        manifest: manifest_json(&manifest)?,
    })
}

#[tauri::command]
fn index_info(path: String) -> Result<IndexResult, String> {
    let manifest = read_index_manifest(Path::new(&path)).map_err(engine_err)?;
    Ok(IndexResult {
        kind: "index-info",
        path,
        manifest: manifest_json(&manifest)?,
    })
}

#[tauri::command]
fn index_verify(path: String) -> Result<IndexResult, String> {
    let manifest = MmapSeedExpansionIndex::verify_dir(Path::new(&path)).map_err(engine_err)?;
    Ok(IndexResult {
        kind: "index-verify",
        path,
        manifest: manifest_json(&manifest)?,
    })
}

#[tauri::command]
fn research_artifacts() -> Result<ResearchArtifactsResult, String> {
    load_research_artifacts_from_docs(&repo_docs_dir())
}

#[tauri::command]
async fn compress_file(
    app: AppHandle,
    path: String,
    config: UiConfig,
    verify: bool,
) -> Result<CompressResult, String> {
    let source_name = name_of(&path);
    let hasher_label = config.hasher.clone();
    let engine = config.engine.clone().unwrap_or_else(|| "brute".into());
    let format = config.format.clone().unwrap_or_else(|| "v1".into());
    let engine_cfg = config.into_engine()?;
    engine_cfg.validate().map_err(engine_err)?;

    emit_progress(&app, "running", "reading source…", 2.0);
    let data = std::fs::read(&path).map_err(into_string)?;
    let source_for_verify = if verify { Some(data.clone()) } else { None };
    let bytes_in = data.len();
    let blocks = bytes_in.div_ceil(engine_cfg.block_size.max(1));
    let t0 = Instant::now();

    emit_progress(&app, "running", "compressing…", 12.0);
    let cfg_for_thread = engine_cfg.clone();
    let engine_for_thread = engine.clone();
    let format_for_thread = format.clone();
    let index_path = config.index_path.clone();
    let max_span_len = config
        .max_span_len
        .unwrap_or(config.block_size * config.max_arity as usize);
    let passes_requested = config.passes.max(1);

    let result = tokio::task::spawn_blocking(move || {
        run_engine_for_ui(
            &data,
            &cfg_for_thread,
            &engine_for_thread,
            &format_for_thread,
            index_path.as_deref(),
            max_span_len,
            passes_requested,
        )
    })
    .await
    .map_err(into_string)?
    .map_err(engine_err)?;
    let compressed_bytes = result.bytes;
    let bytes_out = compressed_bytes.len();
    let duration_ms = t0.elapsed().as_millis() as u64;

    let mut verified = None;
    if let Some(source) = source_for_verify {
        emit_progress(&app, "running", "verifying roundtrip…", 96.0);
        let bytes = compressed_bytes.clone();
        let verify_cfg = engine_cfg.clone();
        let recovered = tokio::task::spawn_blocking(move || {
            decompress_with_limit(&bytes, &verify_cfg, usize::MAX)
        })
        .await
        .map_err(into_string)?
        .map_err(engine_err)?;
        verified = Some(recovered == source);
    }

    let want_persist = !verify || verified == Some(true);
    if want_persist {
        let out_path = format!("{path}.tlmr");
        std::fs::write(&out_path, &compressed_bytes)
            .map_err(|e| format!("writing {out_path}: {e}"))?;
    }

    let delta_pct = if bytes_in > 0 {
        (bytes_out as f64 - bytes_in as f64) / bytes_in as f64 * 100.0
    } else {
        0.0
    };
    let seed_dist = SeedDistDto {
        l0: blocks.saturating_sub(result.selected_hits) as u64,
        l1: *result.seed_counts.get(1).unwrap_or(&0),
        l2: *result.seed_counts.get(2).unwrap_or(&0),
        l3: *result.seed_counts.get(3).unwrap_or(&0),
    };
    let lattice = build_lattice(
        blocks,
        engine_cfg.block_size,
        engine_cfg.max_seed_len,
        &result.selected_spans,
    );

    emit_progress(&app, "done", "complete", 100.0);
    Ok(CompressResult {
        kind: "compress",
        run_id: RUN_COUNTER.fetch_add(1, Ordering::Relaxed) + 1,
        source_name,
        bytes_in,
        bytes_out,
        passes: vec![
            PassStatsDto {
                pass: 0,
                bytes_out: bytes_in,
                delta_pct: 0.0,
                hits: 0,
            },
            PassStatsDto {
                pass: 1,
                bytes_out,
                delta_pct,
                hits: result.selected_hits as u64,
            },
        ],
        duration_ms,
        candidate_count: result.candidate_count as u64,
        hits_total: result.selected_hits as u64,
        literal_bytes: result.literal_bytes,
        blocks,
        seed_dist,
        bundles: result.bundles as u64,
        tier_hits: result.tier_hits as u64,
        lattice,
        verified,
        hasher: hasher_label,
        engine,
        format,
        config: ConfigEcho {
            block_size: config.block_size,
            max_seed_len: config.max_seed_len,
            passes: config.passes,
            hash_bits: config.hash_bits,
            max_arity: config.max_arity,
            hasher: config.hasher,
        },
        engine_telemetry: result.telemetry,
    })
}

fn build_lattice(
    blocks: usize,
    block_size: usize,
    max_seed_len: usize,
    selected_spans: &[SelectedSpanTelemetry],
) -> Vec<LatticeCellDto> {
    let sample_blocks = blocks.min(4096);
    let mut cells: Vec<LatticeCellDto> = (0..sample_blocks)
        .map(|_| LatticeCellDto {
            bin: "l0".into(),
            pass: 0,
            depth: 0.0,
            seed_idx: None,
            bundle: None,
            seed_hex: None,
            hash_prefix: String::new(),
            span_len: None,
            savings: None,
        })
        .collect();

    if block_size == 0 || sample_blocks == 0 {
        return cells;
    }

    for span in selected_spans {
        let first = span.start / block_size;
        let span_blocks = span.span_len.div_ceil(block_size).max(1);
        let bundle_id = if span_blocks > 1 {
            Some(format!("p{}-{}", span.pass, span.start))
        } else {
            None
        };
        for idx in first..first.saturating_add(span_blocks) {
            let Some(cell) = cells.get_mut(idx) else {
                continue;
            };
            cell.bin = if span_blocks > 1 {
                "l4".into()
            } else {
                format!("l{}", span.seed_len.min(3))
            };
            cell.pass = span.pass;
            cell.depth = (span.seed_len as f64 / max_seed_len.max(1) as f64).min(1.0);
            cell.seed_idx = Some(span.seed_index);
            cell.bundle = bundle_id.clone();
            cell.seed_hex = Some(span.seed_hex.clone());
            cell.span_len = Some(span.span_len);
            cell.savings = Some(span.savings);
        }
    }

    cells
}

#[tauri::command]
async fn decompress_file(app: AppHandle, path: String) -> Result<DecompressResult, String> {
    let source_name = name_of(&path);

    emit_progress(&app, "running", "reading container…", 4.0);
    let bytes = std::fs::read(&path).map_err(into_string)?;
    let bytes_in = bytes.len();
    let header = header_dto(&bytes)?;

    emit_progress(&app, "running", "expanding seeds…", 25.0);
    let t0 = Instant::now();
    let bytes_clone = bytes.clone();
    let recovered = tokio::task::spawn_blocking(move || {
        decompress_with_limit(&bytes_clone, &Default::default(), usize::MAX)
    })
    .await
    .map_err(into_string)?
    .map_err(engine_err)?;
    let duration_ms = t0.elapsed().as_millis() as u64;

    let out_path = path
        .strip_suffix(".tlmr")
        .map(|p| format!("{p}.out"))
        .unwrap_or_else(|| format!("{path}.out"));
    std::fs::write(&out_path, &recovered).map_err(into_string)?;

    emit_progress(&app, "done", "complete", 100.0);
    Ok(DecompressResult {
        kind: "decompress",
        run_id: RUN_COUNTER.fetch_add(1, Ordering::Relaxed) + 1,
        source_name,
        bytes_in,
        bytes_out: recovered.len(),
        duration_ms,
        header,
    })
}

fn header_dto(bytes: &[u8]) -> Result<HeaderDto, String> {
    if bytes.len() >= 5 && bytes[4] == TLMR_V2_FORMAT_VERSION {
        let header = decode_tlmr_v2_header(bytes).map_err(engine_err)?;
        let first_layer = decode_tlmr_v2_layer_descriptors(bytes)
            .map_err(engine_err)?
            .into_iter()
            .next();
        return Ok(HeaderDto {
            version: header.version,
            hasher: header.hasher.as_str().to_string(),
            block_size: first_layer.as_ref().map_or(0, |layer| layer.block_size),
            max_seed_len: first_layer.as_ref().map_or(0, |layer| layer.max_seed_len),
            hash_bits: header.hash_bits,
            max_arity: 0,
        });
    }

    let header = decode_tlmr_header(bytes).map_err(|e| format!("engine: {e}"))?;
    Ok(HeaderDto {
        version: header.version,
        hasher: header.hasher.as_str().to_string(),
        block_size: header.block_size,
        max_seed_len: header.max_seed_len,
        hash_bits: header.hash_bits,
        max_arity: header.max_arity,
    })
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            stat_file,
            peek_file,
            compress_file,
            decompress_file,
            index_build,
            index_info,
            index_verify,
            research_artifacts
        ])
        .setup(|app| {
            let h = app.handle().clone();
            let _ = h.emit(
                "telomere://bridge",
                serde_json::json!({ "version": env!("CARGO_PKG_VERSION") }),
            );
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("failed to start Tauri runtime");
}

#[cfg(test)]
mod tests {
    use super::*;
    use telomere::hasher::{SeedExpander, Sha256Expander};

    fn sha_expand(seed: &[u8], len: usize) -> Vec<u8> {
        let mut out = vec![0; len];
        Sha256Expander.expand_into(seed, &mut out);
        out
    }

    fn sha256_ui_config() -> Config {
        Config {
            block_size: 4,
            max_seed_len: 1,
            max_arity: 2,
            hash_bits: 13,
            hasher: HasherKind::Sha256,
            ..Config::default()
        }
    }

    #[test]
    fn streaming_v2_engine_smoke_serializes_real_telemetry() {
        let span = sha_expand(&[0x00], 8);
        let mut data = vec![0xAA];
        for _ in 0..128 {
            data.extend_from_slice(&span);
        }
        let cfg = sha256_ui_config();

        let run = run_engine_for_ui(&data, &cfg, "streaming", "v2", None, 8, 2).unwrap();
        let decoded = decompress_with_limit(&run.bytes, &cfg, usize::MAX).unwrap();
        assert_eq!(decoded, data);
        assert!(run.bytes.len() < data.len());
        assert_eq!(run.telemetry["layers"].as_array().unwrap().len(), 2);
        assert_eq!(run.telemetry["layers"][0]["selected_count"], 0);
        assert!(
            run.telemetry["layers"][1]["selected_count"]
                .as_u64()
                .unwrap()
                > 0
        );

        let lattice = build_lattice(
            data.len().div_ceil(cfg.block_size),
            cfg.block_size,
            cfg.max_seed_len,
            &run.selected_spans,
        );
        let result = CompressResult {
            kind: "compress",
            run_id: 1,
            source_name: "fixture.bin".into(),
            bytes_in: data.len(),
            bytes_out: run.bytes.len(),
            passes: vec![PassStatsDto {
                pass: 1,
                bytes_out: run.bytes.len(),
                delta_pct: -1.0,
                hits: run.selected_hits as u64,
            }],
            duration_ms: 0,
            candidate_count: run.candidate_count as u64,
            hits_total: run.selected_hits as u64,
            literal_bytes: run.literal_bytes,
            blocks: data.len().div_ceil(cfg.block_size),
            seed_dist: SeedDistDto {
                l0: 0,
                l1: *run.seed_counts.get(1).unwrap_or(&0),
                l2: 0,
                l3: 0,
            },
            bundles: run.bundles as u64,
            tier_hits: run.tier_hits as u64,
            lattice,
            verified: Some(true),
            hasher: "sha256".into(),
            engine: "streaming".into(),
            format: "v2".into(),
            config: ConfigEcho {
                block_size: cfg.block_size,
                max_seed_len: cfg.max_seed_len,
                passes: 2,
                hash_bits: cfg.hash_bits,
                max_arity: cfg.max_arity,
                hasher: "sha256".into(),
            },
            engine_telemetry: run.telemetry,
        };
        let value = serde_json::to_value(&result).unwrap();
        assert_eq!(value["kind"], "compress");
        assert!(value["engine_telemetry"]["layers"].is_array());
        assert!(value["lattice"]
            .as_array()
            .unwrap()
            .iter()
            .any(|cell| { cell["seedIdx"].as_u64().is_some() && cell["seedHex"] == "00" }));
    }

    #[test]
    fn indexed_v2_engine_smoke_uses_real_index() {
        let temp = tempfile::tempdir().unwrap();
        let index_config = IndexConfig {
            hasher: HasherKind::Sha256,
            max_seed_len: 1,
            max_span_len: 8,
            tier_lengths: vec![4, 8],
        };
        build_seed_index_to_dir(&index_config, temp.path()).unwrap();
        let span = sha_expand(&[0x00], 8);
        let data = span.repeat(16);
        let cfg = sha256_ui_config();

        let run = run_engine_for_ui(
            &data,
            &cfg,
            "indexed",
            "v2",
            Some(temp.path().to_str().unwrap()),
            8,
            1,
        )
        .unwrap();

        let decoded = decompress_with_limit(&run.bytes, &cfg, usize::MAX).unwrap();
        assert_eq!(decoded, data);
        assert!(run.candidate_count > 0);
        assert!(run.telemetry["candidate_count"].as_u64().unwrap() > 0);
    }

    #[test]
    fn research_artifacts_summary_serializes_generated_ledgers() {
        let result = load_research_artifacts_from_docs(&repo_docs_dir()).unwrap();
        let queue = read_json_value(&repo_docs_dir().join("experiment_queue.json")).unwrap();
        let frontier = read_json_value(&repo_docs_dir().join("research_frontier.json")).unwrap();
        let research_team =
            read_json_value(&repo_docs_dir().join("research_team_protocol.json")).unwrap();
        let goal_completion =
            read_json_value(&repo_docs_dir().join("goal_completion_audit.json")).unwrap();
        let blocked_dispatch =
            read_json_value(&repo_docs_dir().join("blocked_requirement_dispatch.json")).unwrap();
        let natural_proof =
            read_json_value(&repo_docs_dir().join("natural_corpus_proof_matrix.json")).unwrap();
        let production_proof =
            read_json_value(&repo_docs_dir().join("production_proof_matrix.json")).unwrap();
        assert_eq!(result.kind, "research-artifacts");
        assert!(result.verdict.contains("not production-proven"));
        assert!(result
            .open_gates
            .iter()
            .any(|gate| gate.contains("structured-corpus seed-span wins")));
        assert!(result.cards.iter().any(|card| card.id == "goal-audit"));
        assert!(result.cards.iter().any(|card| card.id == "queue"));
        assert_eq!(
            result.evidence.ready_count,
            summary_u64(&queue, "ready_count")
        );
        assert_eq!(
            result.evidence.gated_count,
            summary_u64(&queue, "gated_count")
        );
        assert_eq!(
            result.evidence.blocked_by_evidence_count,
            summary_u64(&queue, "blocked_by_evidence_count")
        );
        assert_eq!(
            result.evidence.top_ready_lane,
            summary_str(&queue, "top_ready_lane", "none")
        );
        assert_eq!(
            result.evidence.frontier_status,
            summary_str(&frontier, "frontier_status", "unknown")
        );
        assert_eq!(
            result.evidence.frontier_unresolved_count,
            summary_u64(&frontier, "unresolved_count")
        );
        assert!(!result.evidence.frontier_ungated_compute_allowed);
        assert!(result.evidence.frontier_allowed_maintenance_only);
        assert!(!result.evidence.frontier_broad_depth_search_allowed);
        assert_eq!(result.evidence.frontier_best_non_planted_gib, 828.0);
        assert_eq!(result.evidence.frontier_long_span_gate_met_count, 0);
        assert_eq!(result.evidence.frontier_long_span_gate_count, 8);
        assert_eq!(result.evidence.frontier_count, 5);
        assert_eq!(
            result.evidence.research_team_protocol_status,
            summary_str(&research_team, "protocol_status", "unknown")
        );
        assert_eq!(result.evidence.research_team_ready_dispatch_count, 0);
        assert_eq!(result.evidence.research_team_brief_count, 6);
        assert_eq!(result.evidence.research_team_work_package_count, 6);
        assert_eq!(result.evidence.research_team_forbidden_action_count, 16);
        assert!(result.evidence.research_team_maintenance_only);
        assert_eq!(
            result.evidence.goal_completion_objective_status,
            summary_str(&goal_completion, "objective_status", "unknown")
        );
        assert_eq!(
            result.evidence.goal_completion_recommendation,
            "keep_goal_active"
        );
        assert!(!result.evidence.goal_completion_production_proven);
        assert_eq!(
            result.evidence.goal_completion_unresolved_evidence_gates,
            27
        );
        assert_eq!(result.evidence.goal_completion_requirements_total, 10);
        assert_eq!(
            result
                .evidence
                .goal_completion_requirements_blocked_by_evidence,
            3
        );
        assert_eq!(
            result.evidence.blocked_dispatch_status,
            summary_str(&blocked_dispatch, "dispatch_status", "unknown")
        );
        assert_eq!(result.evidence.blocked_dispatch_requirement_count, 3);
        assert_eq!(result.evidence.blocked_dispatch_brief_count, 3);
        assert_eq!(result.evidence.blocked_dispatch_parallel_group_count, 6);
        assert_eq!(result.evidence.blocked_dispatch_ready_dispatch_count, 0);
        assert_eq!(result.evidence.blocked_dispatch_forbidden_action_count, 14);
        assert!(!result.evidence.blocked_dispatch_ungated_compute_allowed);
        assert_eq!(
            result.evidence.blocked_dispatch_research_decision,
            "hold_gated_compute_and_continue_evidence_maintenance"
        );
        assert_eq!(
            result.evidence.natural_corpus_status,
            summary_str(&natural_proof, "natural_corpus_status", "unknown")
        );
        assert!(!result.evidence.natural_corpus_proven);
        assert_eq!(result.evidence.natural_corpus_gate_count, 11);
        assert_eq!(result.evidence.natural_corpus_qualified_count, 3);
        assert_eq!(result.evidence.natural_corpus_blocked_gate_count, 8);
        assert_eq!(result.evidence.natural_corpus_heldout_corpus_count, 20);
        assert_eq!(result.evidence.natural_corpus_heldout_prefix5_rows, 0);
        assert_eq!(result.evidence.natural_corpus_heldout_exact_hit_rows, 0);
        assert_eq!(result.evidence.natural_corpus_heldout_selected_span_rows, 0);
        assert_eq!(result.evidence.natural_corpus_match_target_spans, 11154720);
        assert_eq!(result.evidence.natural_corpus_match_selected_span_rows, 0);
        assert_eq!(result.evidence.natural_corpus_best_non_planted_gib, 828.0);
        assert_eq!(
            result.evidence.production_status,
            summary_str(&production_proof, "production_status", "unknown")
        );
        assert!(!result.evidence.production_proven);
        assert_eq!(result.evidence.production_gate_count, 9);
        assert_eq!(result.evidence.production_qualified_count, 5);
        assert_eq!(result.evidence.production_blocked_gate_count, 3);
        assert_eq!(result.evidence.production_runtime_required_count, 1);
        assert!(!result.evidence.production_real_gpu_kernel_detected);
        assert_eq!(
            result.evidence.production_scale_next_double_peak_mib,
            3869.204
        );
        assert_eq!(result.evidence.heldout_prefix4_win_corpora, 11);
        assert_eq!(result.evidence.heldout_exact_hits, 0);
        assert_eq!(result.evidence.heldout_expansion_corpora, 20);
        assert_eq!(result.evidence.heldout_expansion_missing_matrix, 20);
        assert_eq!(result.evidence.heldout_expansion_prefix5_rows, 0);
        assert_eq!(result.evidence.heldout_expansion_exact_hit_rows, 0);
        assert_eq!(result.evidence.heldout_expansion_selected_span_rows, 0);
        assert_eq!(result.evidence.match_selected_spans, 0);
        assert_eq!(result.evidence.lead_exact_hits, 0);
        assert_eq!(result.evidence.exact_short_verified_hits, 3480);
        assert_eq!(result.evidence.exact_short_best_delta_bytes, -631);
        assert_eq!(result.evidence.exact_short_full_stream_negative_groups, 3);
        assert_eq!(result.evidence.exact_short_control_negative_groups, 1);
        assert!(!result.evidence.exact_short_promotion_met);
        assert_eq!(result.evidence.whole_stream_honest_rows, 2358);
        assert_eq!(result.evidence.whole_stream_honest_negative_rows, 0);
        assert_eq!(result.evidence.whole_stream_ordinary_negative_groups, 0);
        assert_eq!(result.evidence.whole_stream_control_negative_groups, 0);
        assert_eq!(result.evidence.whole_stream_best_honest_delta_bytes, 25);
        assert!(!result.evidence.whole_stream_promotion_met);
        assert_eq!(result.evidence.expander_salt_exact_hits, 0);
        assert_eq!(result.evidence.expander_salt_selected_span_rows, 0);
        assert_eq!(result.evidence.expander_salt_full_stream_negative_rows, 0);
        assert!(!result.evidence.expander_salt_random_multiplier_exceeded);
        assert!(!result.evidence.expander_salt_promotion_met);
        assert_eq!(result.evidence.schema_native_family_selected_spans, 11302);
        assert_eq!(result.evidence.schema_native_ordinary_negative_groups, 14);
        assert_eq!(result.evidence.schema_native_control_negative_groups, 0);
        assert_eq!(
            result.evidence.schema_native_wrong_schema_negative_groups,
            0
        );
        assert_eq!(result.evidence.schema_native_random_negative_groups, 0);
        assert_eq!(result.evidence.schema_native_shadow_negative_groups, 0);
        assert!(result.evidence.schema_native_promotion_met);
        assert_eq!(result.evidence.schema_replication_selected_spans, 20239);
        assert_eq!(
            result.evidence.schema_replication_ordinary_negative_groups,
            9
        );
        assert_eq!(
            result.evidence.schema_replication_control_negative_groups,
            2
        );
        assert_eq!(
            result.evidence.schema_replication_generic_negative_groups,
            2
        );
        assert_eq!(
            result.evidence.schema_replication_claim_level,
            "control_failed_on_frozen_expansion_corpora"
        );
        assert!(!result.evidence.schema_replication_promotion_met);
        assert_eq!(result.evidence.superposition_retained_alternatives, 2);
        assert_eq!(result.evidence.superposition_weighted_extra_savings, 4);
        assert_eq!(result.evidence.superposition_unexplained_discards, 0);
        assert!(result.evidence.superposition_promotion_met);
        assert_eq!(
            result
                .evidence
                .recursive_structured_ordinary_later_win_families,
            0
        );
        assert_eq!(
            result
                .evidence
                .recursive_structured_planted_offset_later_win_families,
            1
        );
        assert_eq!(
            result.evidence.recursive_structured_claim_level,
            "recursive_gain_only_in_planted_offset_controls"
        );
        assert!(!result.evidence.recursive_structured_promotion_met);
        assert_eq!(
            result.evidence.scale_performance_largest_peak_memory_mib,
            1934.602
        );
        assert_eq!(result.evidence.scale_performance_peak_table_ratio, 21.985);
        assert_eq!(
            result.evidence.scale_performance_next_double_peak_mib,
            3869.204
        );
        assert!(result.evidence.scale_performance_promotion_met);
        assert_eq!(result.evidence.depth4_exact_hits, 0);
        assert!(!result.evidence.gpu_real_kernel_detected);
        assert!(result
            .cards
            .iter()
            .any(|card| { card.id == "research-frontier" && card.metric.contains("5 frontiers") }));
        assert!(result.cards.iter().any(|card| {
            card.id == "goal-completion-audit" && card.metric.contains("keep_goal_active")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "blocked-requirement-dispatch" && card.metric.contains("3 briefs")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "natural-corpus-proof" && card.metric.contains("8 blocked gates")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "production-proof" && card.metric.contains("3 blocked gates")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "research-team-protocol" && card.metric.contains("6 briefs")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "transform-validation" && card.metric.contains("11 prefix>=4 corpora")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "heldout-expansion" && card.metric.contains("20 corpora missing")
        }));
        assert!(result
            .cards
            .iter()
            .any(|card| { card.id == "exact-discovery" && card.metric.contains("0 lead exact") }));
        assert!(result.cards.iter().any(|card| {
            card.id == "exact-short-economics" && card.metric.contains("3480 hits")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "whole-stream-residual" && card.metric.contains("2358 honest rows")
        }));
        assert!(result
            .cards
            .iter()
            .any(|card| { card.id == "expander-salt" && card.metric.contains("0 exact") }));
        assert!(result.cards.iter().any(|card| {
            card.id == "schema-native-dictionaries" && card.metric.contains("11302 selected")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "schema-replication" && card.metric.contains("20239 selected")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "superposition-telemetry" && card.metric.contains("2 retained")
        }));
        assert!(result.cards.iter().any(|card| {
            card.id == "recursive-structured-fixtures" && card.metric.contains("0 ordinary wins")
        }));
        assert!(result
            .cards
            .iter()
            .any(|card| { card.id == "scale-performance" && card.metric.contains("1934.602") }));
        assert!(result.cards.iter().any(|card| {
            card.id == "acceleration" && card.metric.contains("real kernel detected: false")
        }));

        let value = serde_json::to_value(&result).unwrap();
        assert_eq!(value["kind"], "research-artifacts");
        assert_eq!(value["evidence"]["lead_exact_hits"], 0);
        assert_eq!(value["evidence"]["exact_short_verified_hits"], 3480);
        assert_eq!(value["evidence"]["whole_stream_honest_negative_rows"], 0);
        assert_eq!(value["evidence"]["expander_salt_exact_hits"], 0);
        assert_eq!(
            value["evidence"]["schema_native_family_selected_spans"],
            11302
        );
        assert_eq!(
            value["evidence"]["schema_replication_control_negative_groups"],
            2
        );
        assert_eq!(value["evidence"]["superposition_weighted_extra_savings"], 4);
        assert_eq!(
            value["evidence"]["recursive_structured_ordinary_later_win_families"],
            0
        );
        assert_eq!(
            value["evidence"]["scale_performance_peak_table_ratio"],
            21.985
        );
        assert_eq!(value["evidence"]["depth4_exact_hits"], 0);
        assert_eq!(value["evidence"]["heldout_expansion_corpora"], 20);
        assert_eq!(value["evidence"]["gpu_real_kernel_detected"], false);
        assert_eq!(value["evidence"]["frontier_count"], 5);
        assert_eq!(value["evidence"]["frontier_ungated_compute_allowed"], false);
        assert_eq!(
            value["evidence"]["goal_completion_recommendation"],
            "keep_goal_active"
        );
        assert_eq!(value["evidence"]["blocked_dispatch_brief_count"], 3);
        assert_eq!(
            value["evidence"]["blocked_dispatch_ungated_compute_allowed"],
            false
        );
        assert_eq!(value["evidence"]["natural_corpus_gate_count"], 11);
        assert_eq!(value["evidence"]["natural_corpus_blocked_gate_count"], 8);
        assert_eq!(
            value["evidence"]["natural_corpus_heldout_selected_span_rows"],
            0
        );
        assert_eq!(value["evidence"]["production_gate_count"], 9);
        assert_eq!(value["evidence"]["production_blocked_gate_count"], 3);
        assert_eq!(value["evidence"]["production_runtime_required_count"], 1);
        assert_eq!(
            value["evidence"]["production_real_gpu_kernel_detected"],
            false
        );
        assert_eq!(value["evidence"]["research_team_brief_count"], 6);
        assert_eq!(value["evidence"]["research_team_maintenance_only"], true);
        assert!(value["cards"].as_array().unwrap().len() >= 8);
        assert!(value["overall_status"]
            .as_str()
            .unwrap()
            .contains("not production-proven"));
    }
}
