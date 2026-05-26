use crate::config::HasherKind;
use crate::header::{LOTUS_J_BITS, LOTUS_TIERS};
use crate::public_preset::{
    public_preset_selective_decode_framed, PUBLIC_PRESET_SELECTIVE_VERSION,
};
use crate::seed_index::{index_to_seed, seed_to_index};
use crate::tlmr::{truncated_hash_bits, MAX_BLOCK_SIZE, MAX_HASH_BITS, TLMR_MAGIC};
use crate::TelomereError;
use lotus::{
    lotus_decode_from_reader, lotus_encode_into_writer, lotus_encoded_bit_len, BitReader, BitWriter,
};

pub const TLMR_V2_FORMAT_VERSION: u8 = 3;
pub const LOTUS_PRESET_V2: u8 = 2;
/// Length of the raw "TLMR" magic + version byte prefix at the start of a v2
/// file. Everything after these 5 bytes is Lotus-encoded.
pub const V2_MAGIC_VERSION_LEN: usize = 5;
pub const V2_SEED_ORDER_VERSION: u8 = 1;
pub const V2_TIER_POLICY_SEED_SPAN: u8 = 1;
pub const V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE: u8 = 2;
pub const V2_TIER_POLICY_FIXED_SEED_SPAN: u8 = 3;
pub const MAX_V2_SEED_LEN: usize = 6;

/// Lotus-encoded tag values for v2 record framing. Encoded with the shared
/// `LOTUS_J_BITS`/`LOTUS_TIERS` preset. Tag 0 = seed-span record, tag 1 =
/// literal record. In the current preset (J3D2) both occupy 6 bits.
pub const V2_RECORD_TAG_SEED_SPAN: u64 = 0;
pub const V2_RECORD_TAG_LITERAL: u64 = 1;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlmrV2Header {
    pub version: u8,
    pub lotus_preset: u8,
    pub hasher: HasherKind,
    pub seed_order_version: u8,
    pub layer_count: u8,
    pub hash_bits: usize,
    pub original_len: u64,
    /// Number of meaningful bits in the outer payload section. The byte
    /// slice on disk is `ceil(outer_payload_bit_len / 8)` bytes long; the
    /// trailing 0-7 bits of the last byte must be zero pad.
    pub outer_payload_bit_len: u64,
    pub output_hash: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlmrV2LayerDescriptor {
    pub decoded_len: u64,
    pub decoded_hash: u64,
    pub max_seed_len: usize,
    pub max_span_len: usize,
    pub block_size: usize,
    pub tier_policy: u8,
    pub span_step: usize,
}

impl TlmrV2LayerDescriptor {
    pub fn for_decoded_bytes(
        decoded: &[u8],
        hasher: HasherKind,
        max_seed_len: usize,
        max_span_len: usize,
        block_size: usize,
        hash_bits: usize,
    ) -> Self {
        let expander = hasher.get_expander();
        Self {
            decoded_len: decoded.len() as u64,
            decoded_hash: truncated_hash_bits(decoded, expander.as_ref(), hash_bits),
            max_seed_len,
            max_span_len,
            block_size,
            tier_policy: V2_TIER_POLICY_SEED_SPAN,
            span_step: block_size,
        }
    }

    pub fn for_decoded_bytes_with_span_step(
        decoded: &[u8],
        hasher: HasherKind,
        max_seed_len: usize,
        max_span_len: usize,
        block_size: usize,
        span_step: usize,
        hash_bits: usize,
    ) -> Self {
        let expander = hasher.get_expander();
        Self {
            decoded_len: decoded.len() as u64,
            decoded_hash: truncated_hash_bits(decoded, expander.as_ref(), hash_bits),
            max_seed_len,
            max_span_len,
            block_size,
            tier_policy: V2_TIER_POLICY_SEED_SPAN,
            span_step,
        }
    }

    pub fn for_public_preset_selective_decoded_bytes(
        decoded: &[u8],
        hasher: HasherKind,
        min_token_len: usize,
        codeword_len: usize,
        hash_bits: usize,
    ) -> Self {
        let expander = hasher.get_expander();
        Self {
            decoded_len: decoded.len() as u64,
            decoded_hash: truncated_hash_bits(decoded, expander.as_ref(), hash_bits),
            max_seed_len: 1,
            max_span_len: codeword_len,
            block_size: min_token_len,
            tier_policy: V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE,
            span_step: PUBLIC_PRESET_SELECTIVE_VERSION,
        }
    }

    pub fn for_fixed_seed_span_decoded_bytes(
        decoded: &[u8],
        hasher: HasherKind,
        max_seed_len: usize,
        fixed_span_len: usize,
        span_step: usize,
        hash_bits: usize,
    ) -> Self {
        let expander = hasher.get_expander();
        Self {
            decoded_len: decoded.len() as u64,
            decoded_hash: truncated_hash_bits(decoded, expander.as_ref(), hash_bits),
            max_seed_len,
            max_span_len: fixed_span_len,
            block_size: fixed_span_len,
            tier_policy: V2_TIER_POLICY_FIXED_SEED_SPAN,
            span_step,
        }
    }
}

/// Standalone Lotus-encoded v2 record. `bytes` holds the byte-aligned tail
/// (any trailing partial byte is zero-padded); `bit_len` is the number of
/// significant bits that should be appended to a shared `BitWriter` when
/// concatenating records. `bytes.len() == (bit_len + 7) / 8`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EncodedV2Record {
    pub bytes: Vec<u8>,
    pub bit_len: usize,
}

fn lotus_err(e: lotus::LotusError) -> TelomereError {
    TelomereError::Header(format!("lotus: {e}"))
}

/// Streaming encoder for a seed-span record. Writes
///   [Lotus tag=0][Lotus (span_len - 1)][Lotus seed_index]
/// into the shared writer. Returns the number of bits written.
pub fn v2_seed_span_record_into_writer(
    writer: &mut BitWriter,
    span_len: usize,
    seed: &[u8],
    max_seed_len: usize,
) -> Result<usize, TelomereError> {
    if span_len == 0 || span_len > u16::MAX as usize {
        return Err(TelomereError::Header(
            "v2 seed span length must fit u16".into(),
        ));
    }
    if seed.is_empty() || seed.len() > max_seed_len {
        return Err(TelomereError::Header(
            "v2 seed length out of range for max_seed_len".into(),
        ));
    }
    let seed_index = seed_to_index(seed, max_seed_len);
    let start = writer.bits_written();
    lotus_encode_into_writer(V2_RECORD_TAG_SEED_SPAN, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    // Encode span_len - 1 so the common case (span_len=1 -> value 0) sits in
    // Lotus's smallest tier.
    lotus_encode_into_writer((span_len - 1) as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(seed_index as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    Ok(writer.bits_written() - start)
}

/// Streaming encoder for a fixed-span seed record. The span length is not
/// stored per record; decoders recover it from the layer descriptor's
/// `max_span_len` when `tier_policy == V2_TIER_POLICY_FIXED_SEED_SPAN`.
pub fn v2_fixed_seed_span_record_into_writer(
    writer: &mut BitWriter,
    seed: &[u8],
    max_seed_len: usize,
) -> Result<usize, TelomereError> {
    if seed.is_empty() || seed.len() > max_seed_len {
        return Err(TelomereError::Header(
            "v2 seed length out of range for max_seed_len".into(),
        ));
    }
    let seed_index = seed_to_index(seed, max_seed_len);
    let start = writer.bits_written();
    lotus_encode_into_writer(V2_RECORD_TAG_SEED_SPAN, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(seed_index as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    Ok(writer.bits_written() - start)
}

/// Streaming encoder for a literal record. Writes
///   [Lotus tag=1][Lotus (len - 1)][0..7 pad bits][len raw bytes]
/// into the shared writer. The 0-7 pad bits before the raw payload exist so
/// the literal payload starts on a byte boundary inside the layer stream and
/// decoders can `memcpy` it directly. The padding count depends on the shared
/// writer's bit position when the literal begins, NOT on the record's internal
/// layout, so concatenated records MUST use this streaming form.
pub fn v2_literal_record_into_writer(
    writer: &mut BitWriter,
    bytes: &[u8],
) -> Result<usize, TelomereError> {
    if bytes.is_empty() || bytes.len() > u16::MAX as usize {
        return Err(TelomereError::Header(
            "v2 literal record length must be in 1..=65535".into(),
        ));
    }
    let start = writer.bits_written();
    lotus_encode_into_writer(V2_RECORD_TAG_LITERAL, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer((bytes.len() - 1) as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    // Byte-align so the raw payload that follows can be read via memcpy. This
    // is the only raw-binary surface in the v2 record format, and only for
    // alignment of bytes that compression has already chosen to skip.
    while writer.bits_written() % 8 != 0 {
        writer.write_bits(0, 1).map_err(lotus_err)?;
    }
    for byte in bytes {
        writer.write_bits(*byte as u64, 8).map_err(lotus_err)?;
    }
    Ok(writer.bits_written() - start)
}

/// Convenience constructor for a standalone seed-span record. Layer encoders
/// that concatenate multiple records MUST use
/// [`v2_seed_span_record_into_writer`] so bit-alignment stays consistent.
pub fn v2_seed_span_record(
    span_len: usize,
    seed: &[u8],
    max_seed_len: usize,
) -> Result<EncodedV2Record, TelomereError> {
    let mut writer = BitWriter::new();
    let bit_len = v2_seed_span_record_into_writer(&mut writer, span_len, seed, max_seed_len)?;
    Ok(EncodedV2Record {
        bytes: writer.into_bytes(),
        bit_len,
    })
}

/// Convenience constructor for a standalone literal record. The byte-alignment
/// padding inside the returned bytes is relative to position 0, so blindly
/// concatenating two `EncodedV2Record::bytes` values would put the second
/// record's raw payload at the wrong offset. Layer encoders MUST use
/// [`v2_literal_record_into_writer`] instead.
pub fn v2_literal_record(bytes: &[u8]) -> Result<EncodedV2Record, TelomereError> {
    let mut writer = BitWriter::new();
    let bit_len = v2_literal_record_into_writer(&mut writer, bytes)?;
    Ok(EncodedV2Record {
        bytes: writer.into_bytes(),
        bit_len,
    })
}

/// Returns the number of bits a seed-span record would consume on the wire,
/// without actually encoding it. Used by candidate scoring.
pub fn v2_seed_span_record_bit_len(
    span_len: usize,
    seed: &[u8],
    max_seed_len: usize,
) -> Result<usize, TelomereError> {
    if span_len == 0 || span_len > u16::MAX as usize {
        return Err(TelomereError::Header(
            "v2 seed span length must fit u16".into(),
        ));
    }
    if seed.is_empty() || seed.len() > max_seed_len {
        return Err(TelomereError::Header(
            "v2 seed length out of range for max_seed_len".into(),
        ));
    }
    let seed_index = seed_to_index(seed, max_seed_len);
    let tag_bits = lotus_encoded_bit_len(V2_RECORD_TAG_SEED_SPAN, LOTUS_J_BITS, LOTUS_TIERS)
        .map_err(lotus_err)?;
    let span_bits = lotus_encoded_bit_len((span_len - 1) as u64, LOTUS_J_BITS, LOTUS_TIERS)
        .map_err(lotus_err)?;
    let seed_bits =
        lotus_encoded_bit_len(seed_index as u64, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    Ok(tag_bits + span_bits + seed_bits)
}

/// Returns the bit length of a fixed-span seed record. This omits the
/// per-record span length because the layer descriptor fixes it for the
/// whole payload.
pub fn v2_fixed_seed_span_record_bit_len(
    seed: &[u8],
    max_seed_len: usize,
) -> Result<usize, TelomereError> {
    if seed.is_empty() || seed.len() > max_seed_len {
        return Err(TelomereError::Header(
            "v2 seed length out of range for max_seed_len".into(),
        ));
    }
    let seed_index = seed_to_index(seed, max_seed_len);
    let tag_bits = lotus_encoded_bit_len(V2_RECORD_TAG_SEED_SPAN, LOTUS_J_BITS, LOTUS_TIERS)
        .map_err(lotus_err)?;
    let seed_bits =
        lotus_encoded_bit_len(seed_index as u64, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    Ok(tag_bits + seed_bits)
}

/// Ceil-divided byte count for a seed-span record, for candidate scoring
/// against `span_len` (also in bytes). Rounds up so we never report
/// profitability we won't actually realize once the bits are packed.
pub fn v2_seed_span_record_byte_len(
    span_len: usize,
    seed: &[u8],
    max_seed_len: usize,
) -> Result<usize, TelomereError> {
    let bits = v2_seed_span_record_bit_len(span_len, seed, max_seed_len)?;
    Ok((bits + 7) / 8)
}

/// Encode a complete v2 file. The outer payload must already be a
/// byte-aligned bit-packed stream of v2 records; this function records its
/// meaningful bit length as `outer_payload.len() * 8`. Use
/// [`encode_v2_file_with_bit_len`] when the payload's last byte contains
/// trailing pad bits whose count must be tracked precisely.
pub fn encode_v2_file(
    hasher: HasherKind,
    hash_bits: usize,
    original_len: u64,
    layers: &[TlmrV2LayerDescriptor],
    outer_payload: &[u8],
) -> Result<Vec<u8>, TelomereError> {
    let bit_len = (outer_payload.len() as u64)
        .checked_mul(8)
        .ok_or_else(|| TelomereError::Header("v2 outer payload too large".into()))?;
    encode_v2_file_with_bit_len(
        hasher,
        hash_bits,
        original_len,
        layers,
        outer_payload,
        bit_len,
    )
}

/// Encode a complete v2 file with an explicit outer payload bit length. The
/// outer payload byte slice must contain at least `ceil(bit_len/8)` bytes;
/// only the first `ceil(bit_len/8)` bytes are written to the output.
pub fn encode_v2_file_with_bit_len(
    hasher: HasherKind,
    hash_bits: usize,
    original_len: u64,
    layers: &[TlmrV2LayerDescriptor],
    outer_payload: &[u8],
    outer_payload_bit_len: u64,
) -> Result<Vec<u8>, TelomereError> {
    if layers.is_empty() || layers.len() > u8::MAX as usize {
        return Err(TelomereError::Header(
            "v2 files must contain 1..=255 layers".into(),
        ));
    }
    if !(1..=64).contains(&hash_bits) {
        return Err(TelomereError::Header("hash_bits must be in 1..=64".into()));
    }
    let expected_bytes = (outer_payload_bit_len as usize).div_ceil(8);
    if outer_payload.len() < expected_bytes {
        return Err(TelomereError::Header(
            "v2 outer payload shorter than declared bit length".into(),
        ));
    }
    let output_hash = layers
        .last()
        .ok_or_else(|| TelomereError::Header("missing v2 layer".into()))?
        .decoded_hash;

    let header = TlmrV2Header {
        version: TLMR_V2_FORMAT_VERSION,
        lotus_preset: LOTUS_PRESET_V2,
        hasher,
        seed_order_version: V2_SEED_ORDER_VERSION,
        layer_count: layers.len() as u8,
        hash_bits,
        original_len,
        outer_payload_bit_len,
        output_hash,
    };

    // Build a single bit-stream containing the header followed by all layer
    // descriptors. Pad to a byte boundary so the outer payload (also
    // byte-aligned) can be appended as raw bytes.
    let mut writer = BitWriter::new();
    encode_header_into_writer(&header, &mut writer)?;
    for layer in layers {
        encode_layer_descriptor_into(layer, header.hash_bits, &mut writer)?;
    }
    let bits = writer.bits_written();
    let pad = (8 - (bits % 8)) % 8;
    if pad > 0 {
        writer.write_bits(0, pad).map_err(lotus_err)?;
    }
    let header_section = writer.into_bytes();

    let mut out = Vec::with_capacity(V2_MAGIC_VERSION_LEN + header_section.len() + expected_bytes);
    out.extend_from_slice(&TLMR_MAGIC);
    out.push(header.version);
    out.extend_from_slice(&header_section);
    if expected_bytes > 0 {
        out.extend_from_slice(&outer_payload[..expected_bytes]);
    }
    Ok(out)
}

pub(crate) fn validate_v2_search_config(
    max_seed_len: usize,
    max_span_len: usize,
    block_size: usize,
    passes: usize,
    hash_bits: usize,
) -> Result<(), TelomereError> {
    if !(1..=MAX_V2_SEED_LEN).contains(&max_seed_len) {
        return Err(TelomereError::Config(format!(
            "max_seed_len must be in 1..={MAX_V2_SEED_LEN}"
        )));
    }
    if max_span_len == 0 || max_span_len > u16::MAX as usize {
        return Err(TelomereError::Config(
            "max_span_len must be in 1..=65535".into(),
        ));
    }
    if !(1..=MAX_BLOCK_SIZE).contains(&block_size) {
        return Err(TelomereError::Config(format!(
            "block_size must be in 1..={MAX_BLOCK_SIZE}"
        )));
    }
    if block_size > max_span_len {
        return Err(TelomereError::Config(
            "block_size must not exceed max_span_len".into(),
        ));
    }
    if passes == 0 || passes > u8::MAX as usize {
        return Err(TelomereError::Config(
            "passes must be in 1..=255 for v2".into(),
        ));
    }
    if !(1..=MAX_HASH_BITS).contains(&hash_bits) {
        return Err(TelomereError::Config(format!(
            "hash_bits must be in 1..={MAX_HASH_BITS}"
        )));
    }
    Ok(())
}

pub(crate) fn validate_v2_span_step(
    span_step: usize,
    block_size: usize,
    max_span_len: usize,
) -> Result<(), TelomereError> {
    if span_step == 0 || span_step > u16::MAX as usize {
        return Err(TelomereError::Config(
            "span_step must be in 1..=65535".into(),
        ));
    }
    if span_step > block_size {
        return Err(TelomereError::Config(
            "span_step must not exceed block_size".into(),
        ));
    }
    if span_step > max_span_len {
        return Err(TelomereError::Config(
            "span_step must not exceed max_span_len".into(),
        ));
    }
    Ok(())
}

/// Decode just the v2 header (no descriptors, no payload offset). This
/// works on both standalone header byte buffers produced by
/// [`encode_tlmr_v2_header`] and on complete v2 files where descriptors and
/// payload follow.
pub fn decode_tlmr_v2_header(input: &[u8]) -> Result<TlmrV2Header, TelomereError> {
    let (_version, _tail, header) = decode_magic_and_header(input)?;
    Ok(header)
}

/// Decode the v2 header plus all layer descriptors. Returns the header,
/// the descriptors, and the byte offset where the outer payload starts.
/// The outer payload section is byte-aligned: the encoder pads the header +
/// descriptor bit stream to a byte boundary, so the returned offset can be
/// used to byte-slice the payload directly.
pub fn decode_v2_header_and_descriptors(
    input: &[u8],
) -> Result<(TlmrV2Header, Vec<TlmrV2LayerDescriptor>, usize), TelomereError> {
    if input.len() < V2_MAGIC_VERSION_LEN {
        return Err(TelomereError::Header("v2 header too short".into()));
    }
    if input[0..4] != TLMR_MAGIC {
        return Err(TelomereError::Header("invalid v2 magic".into()));
    }
    let version = input[4];
    if version != TLMR_V2_FORMAT_VERSION {
        return Err(TelomereError::Header(format!(
            "unsupported v2 format version {version}; expected {TLMR_V2_FORMAT_VERSION}"
        )));
    }

    let tail = &input[V2_MAGIC_VERSION_LEN..];
    let mut reader = BitReader::new(tail);
    let header = decode_header_from_reader(version, &mut reader)?;

    let mut descriptors = Vec::with_capacity(header.layer_count as usize);
    for _ in 0..header.layer_count {
        descriptors.push(decode_layer_descriptor_from(&mut reader, header.hash_bits)?);
    }

    // Consume trailing pad bits to byte boundary.
    let consumed = reader.bits_consumed();
    let pad = (8 - (consumed % 8)) % 8;
    if pad > 0 {
        let pad_value = reader.read_bits(pad).map_err(lotus_err)?;
        if pad_value != 0 {
            return Err(TelomereError::Header(
                "nonzero v2 header alignment pad bit".into(),
            ));
        }
    }

    let consumed_bits = reader.bits_consumed();
    debug_assert!(consumed_bits.is_multiple_of(8));
    let payload_start = V2_MAGIC_VERSION_LEN + (consumed_bits / 8);

    Ok((header, descriptors, payload_start))
}

/// Helper: validate magic + version and decode the header portion only.
/// Returns the version byte, the bit-stream tail (after magic+version), and
/// the parsed header. Callers that also want descriptors must continue with
/// a `BitReader::new(tail)` from where the header reader left off — see
/// [`decode_v2_header_and_descriptors`].
fn decode_magic_and_header(input: &[u8]) -> Result<(u8, &[u8], TlmrV2Header), TelomereError> {
    if input.len() < V2_MAGIC_VERSION_LEN {
        return Err(TelomereError::Header("v2 header too short".into()));
    }
    if input[0..4] != TLMR_MAGIC {
        return Err(TelomereError::Header("invalid v2 magic".into()));
    }
    let version = input[4];
    if version != TLMR_V2_FORMAT_VERSION {
        return Err(TelomereError::Header(format!(
            "unsupported v2 format version {version}; expected {TLMR_V2_FORMAT_VERSION}"
        )));
    }
    let tail = &input[V2_MAGIC_VERSION_LEN..];
    let mut reader = BitReader::new(tail);
    let header = decode_header_from_reader(version, &mut reader)?;
    Ok((version, tail, header))
}

/// Decode the header's Lotus-encoded fields and raw output hash from a
/// `BitReader` positioned right after the magic+version bytes.
fn decode_header_from_reader(
    version: u8,
    reader: &mut BitReader<'_>,
) -> Result<TlmrV2Header, TelomereError> {
    let (lotus_preset_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let lotus_preset = u8::try_from(lotus_preset_u64)
        .map_err(|_| TelomereError::Header("invalid v2 lotus preset".into()))?;
    let (hasher_id_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let hasher_id = u8::try_from(hasher_id_u64)
        .map_err(|_| TelomereError::Header("invalid v2 hasher id".into()))?;
    let hasher = id_to_hasher(hasher_id)?;
    let (seed_order_version_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let seed_order_version = u8::try_from(seed_order_version_u64)
        .map_err(|_| TelomereError::Header("invalid v2 seed order version".into()))?;
    let (layer_count_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let layer_count = u8::try_from(layer_count_u64)
        .map_err(|_| TelomereError::Header("invalid v2 layer count".into()))?;
    let (hash_bits_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let hash_bits = usize::try_from(hash_bits_u64)
        .map_err(|_| TelomereError::Header("invalid v2 hash bits".into()))?;
    let (original_len, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let (outer_payload_bit_len, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;

    if lotus_preset != LOTUS_PRESET_V2
        || seed_order_version != V2_SEED_ORDER_VERSION
        || layer_count == 0
        || !(1..=64).contains(&hash_bits)
    {
        return Err(TelomereError::Header("invalid v2 header field".into()));
    }

    let output_hash = reader.read_bits(hash_bits).map_err(lotus_err)?;
    if output_hash & !hash_mask(hash_bits) != 0 {
        return Err(TelomereError::Header("invalid v2 output hash".into()));
    }

    Ok(TlmrV2Header {
        version,
        lotus_preset,
        hasher,
        seed_order_version,
        layer_count,
        hash_bits,
        original_len,
        outer_payload_bit_len,
        output_hash,
    })
}

pub fn decompress_v2_with_limit(
    input: &[u8],
    limit: usize,
    memory_limit: usize,
) -> Result<Vec<u8>, TelomereError> {
    let (header, descriptors, payload_start) = decode_v2_header_and_descriptors(input)?;
    let outer_payload_bit_len: usize = header
        .outer_payload_bit_len
        .try_into()
        .map_err(|_| TelomereError::Header("v2 payload length out of range".into()))?;
    let outer_payload_byte_len = outer_payload_bit_len.div_ceil(8);
    let total_len = payload_start
        .checked_add(outer_payload_byte_len)
        .ok_or_else(|| TelomereError::Header("v2 payload length out of range".into()))?;
    if input.len() != total_len {
        return Err(TelomereError::Header("v2 payload length mismatch".into()));
    }

    let original_len: usize = header
        .original_len
        .try_into()
        .map_err(|_| TelomereError::Header("v2 original length out of range".into()))?;
    if original_len > limit || original_len > memory_limit {
        return Err(TelomereError::Header("v2 output limit exceeded".into()));
    }

    for descriptor in &descriptors {
        let decoded_len: usize = descriptor
            .decoded_len
            .try_into()
            .map_err(|_| TelomereError::Header("v2 layer length out of range".into()))?;
        if decoded_len > limit || decoded_len > memory_limit {
            return Err(TelomereError::Header(
                "v2 layer output limit exceeded".into(),
            ));
        }
    }

    let expander = header.hasher.get_expander();
    let mut current = input[payload_start..].to_vec();
    for descriptor in descriptors {
        current = decode_v2_layer(&current, &descriptor, header.hasher)?;
        let hash = truncated_hash_bits(&current, expander.as_ref(), header.hash_bits);
        if hash != descriptor.decoded_hash {
            return Err(TelomereError::Header("layer hash mismatch".into()));
        }
    }

    if current.len() != original_len {
        return Err(TelomereError::Header("v2 output length mismatch".into()));
    }
    let hash = truncated_hash_bits(&current, expander.as_ref(), header.hash_bits);
    if hash != header.output_hash {
        return Err(TelomereError::Header("v2 output hash mismatch".into()));
    }
    Ok(current)
}

pub fn decode_tlmr_v2_layer_descriptors(
    input: &[u8],
) -> Result<Vec<TlmrV2LayerDescriptor>, TelomereError> {
    decode_v2_header_and_descriptors(input).map(|(_, descriptors, _)| descriptors)
}

pub fn decode_v2_payload(
    payload: &[u8],
    descriptor: &TlmrV2LayerDescriptor,
    hasher: HasherKind,
) -> Result<Vec<u8>, TelomereError> {
    if descriptor.tier_policy != V2_TIER_POLICY_SEED_SPAN
        && descriptor.tier_policy != V2_TIER_POLICY_FIXED_SEED_SPAN
    {
        return Err(TelomereError::Header(
            "v2 payload decoder requires seed-span tier policy".into(),
        ));
    }
    let fixed_span_len = if descriptor.tier_policy == V2_TIER_POLICY_FIXED_SEED_SPAN {
        Some(descriptor.max_span_len)
    } else {
        None
    };
    let decoded_len: usize = descriptor
        .decoded_len
        .try_into()
        .map_err(|_| TelomereError::Header("v2 decoded length out of range".into()))?;
    // Cap the pre-allocation so a malicious descriptor with `decoded_len`
    // close to `u64::MAX` cannot trip the allocator's "capacity overflow"
    // abort. Two bounds apply:
    //   1. `isize::MAX as usize` is Rust's documented upper limit for
    //      `Vec::with_capacity`.
    //   2. `payload.len() * max_span_len` is a tight input-derived bound:
    //      each record consumes at least one bit of payload (so at most
    //      `payload.len() * 8` records), and each record produces at most
    //      `max_span_len` output bytes. The multiplication uses
    //      `saturating_mul` so the bound itself can't overflow.
    // Per-record checks (`next_len > decoded_len`) still enforce the actual
    // payload bound; this only protects the initial allocation from a
    // hostile descriptor whose `memory_limit` guard was bypassed (e.g.
    // a library consumer using `Config::default()` with `memory_limit =
    // usize::MAX`).
    let payload_cap = payload
        .len()
        .saturating_mul(8)
        .saturating_mul(descriptor.max_span_len);
    let cap = decoded_len.min(payload_cap).min(isize::MAX as usize);
    let mut out = Vec::with_capacity(cap);
    let expander = hasher.get_expander();
    let mut reader = BitReader::new(payload);

    // Loop on output length, not on bit position: the last record may leave
    // up to 7 trailing pad bits in the final byte that have no semantic
    // meaning. The decoder stops when the layer is fully reconstructed.
    while out.len() < decoded_len {
        let (tag, _) =
            lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
        match tag {
            t if t == V2_RECORD_TAG_SEED_SPAN => {
                let span_len = if let Some(span_len) = fixed_span_len {
                    span_len
                } else {
                    let (span_minus_one, _) =
                        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS)
                            .map_err(lotus_err)?;
                    let span_minus_one = usize::try_from(span_minus_one)
                        .map_err(|_| TelomereError::Header("v2 seed span overflow".into()))?;
                    span_minus_one
                        .checked_add(1)
                        .ok_or_else(|| TelomereError::Header("v2 seed span overflow".into()))?
                };
                if span_len == 0 || span_len > descriptor.max_span_len {
                    return Err(TelomereError::Header("invalid v2 seed span".into()));
                }
                let (seed_index, _) =
                    lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS)
                        .map_err(lotus_err)?;
                let next_len = out
                    .len()
                    .checked_add(span_len)
                    .ok_or_else(|| TelomereError::Header("invalid v2 seed span".into()))?;
                if next_len > decoded_len {
                    return Err(TelomereError::Header("invalid v2 seed span".into()));
                }
                let seed_index = usize::try_from(seed_index)
                    .map_err(|_| TelomereError::Header("invalid v2 seed index".into()))?;
                let seed = index_to_seed(seed_index, descriptor.max_seed_len)
                    .map_err(|_| TelomereError::Header("invalid v2 seed index".into()))?;
                if seed.is_empty() || seed.len() > descriptor.max_seed_len {
                    return Err(TelomereError::Header("invalid v2 seed span".into()));
                }
                let start = out.len();
                out.resize(start + span_len, 0);
                expander.expand_into(&seed, &mut out[start..start + span_len]);
            }
            t if t == V2_RECORD_TAG_LITERAL => {
                let (len_minus_one, _) =
                    lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS)
                        .map_err(lotus_err)?;
                let len_minus_one = usize::try_from(len_minus_one)
                    .map_err(|_| TelomereError::Header("v2 literal overflow".into()))?;
                let len = len_minus_one
                    .checked_add(1)
                    .ok_or_else(|| TelomereError::Header("v2 literal overflow".into()))?;
                if len == 0 || len > u16::MAX as usize {
                    return Err(TelomereError::Header("invalid v2 literal length".into()));
                }
                let next_len = out
                    .len()
                    .checked_add(len)
                    .ok_or_else(|| TelomereError::Header("invalid v2 literal length".into()))?;
                if next_len > decoded_len {
                    return Err(TelomereError::Header("invalid v2 literal length".into()));
                }
                // Mirror encoder padding: skip 0-7 bits to byte boundary, then
                // read raw bytes 8 bits at a time.
                while reader.bits_consumed() % 8 != 0 {
                    let pad = reader.read_bits(1).map_err(lotus_err)?;
                    if pad != 0 {
                        return Err(TelomereError::Header("nonzero v2 literal pad bit".into()));
                    }
                }
                let start = out.len();
                out.resize(start + len, 0);
                for slot in &mut out[start..start + len] {
                    *slot = reader.read_bits(8).map_err(lotus_err)? as u8;
                }
            }
            other => {
                return Err(TelomereError::Header(format!(
                    "unknown v2 record tag {other}"
                )));
            }
        }
    }

    let remaining_bits = payload.len() * 8 - reader.bits_consumed();
    if remaining_bits > 7 {
        return Err(TelomereError::Header("excess v2 trailing pad bits".into()));
    }
    while reader.bits_consumed() < payload.len() * 8 {
        let pad = reader.read_bits(1).map_err(lotus_err)?;
        if pad != 0 {
            return Err(TelomereError::Header("nonzero v2 trailing pad bit".into()));
        }
    }

    if out.len() != decoded_len {
        return Err(TelomereError::Header("v2 layer length mismatch".into()));
    }
    Ok(out)
}

fn decode_v2_layer(
    payload: &[u8],
    descriptor: &TlmrV2LayerDescriptor,
    hasher: HasherKind,
) -> Result<Vec<u8>, TelomereError> {
    match descriptor.tier_policy {
        V2_TIER_POLICY_SEED_SPAN | V2_TIER_POLICY_FIXED_SEED_SPAN => {
            decode_v2_payload(payload, descriptor, hasher)
        }
        V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE => {
            let decoded_len: usize = descriptor.decoded_len.try_into().map_err(|_| {
                TelomereError::Header("v2 transform layer length out of range".into())
            })?;
            public_preset_selective_decode_framed(
                payload,
                hasher,
                descriptor.block_size,
                descriptor.max_span_len,
                decoded_len,
            )
        }
        _ => Err(TelomereError::Header("unknown v2 layer policy".into())),
    }
}

/// Encode the v2 file header into a standalone byte buffer. The header
/// begins with the raw "TLMR" magic and version byte, followed by a
/// bit-stream of Lotus-encoded fields (preset, hasher id, seed order
/// version, layer count, hash bits, original length, outer payload bit
/// length) and a raw `hash_bits`-wide output hash. Trailing pad bits in the
/// final byte are zero.
///
/// This standalone form is intended for tests and tools that want only the
/// header. The full-file encoder (`encode_v2_file`) writes the header and
/// descriptors back-to-back into a shared bit writer to avoid wasted
/// alignment padding between them.
pub fn encode_tlmr_v2_header(header: &TlmrV2Header) -> Result<Vec<u8>, TelomereError> {
    if !(1..=64).contains(&header.hash_bits) {
        return Err(TelomereError::Header("hash_bits must be in 1..=64".into()));
    }
    let mut writer = BitWriter::new();
    encode_header_into_writer(header, &mut writer)?;
    let mut out = Vec::with_capacity(V2_MAGIC_VERSION_LEN + writer.bits_written().div_ceil(8));
    out.extend_from_slice(&TLMR_MAGIC);
    out.push(header.version);
    out.extend_from_slice(&writer.into_bytes());
    Ok(out)
}

/// Write the v2 header's Lotus-encoded fields and raw hash bits into a
/// shared `BitWriter`. This does NOT emit the "TLMR" magic or version byte
/// (those stay raw and live outside the bit stream).
pub fn encode_header_into_writer(
    header: &TlmrV2Header,
    writer: &mut BitWriter,
) -> Result<(), TelomereError> {
    if !(1..=64).contains(&header.hash_bits) {
        return Err(TelomereError::Header("hash_bits must be in 1..=64".into()));
    }
    lotus_encode_into_writer(
        header.lotus_preset as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        writer,
    )
    .map_err(lotus_err)?;
    lotus_encode_into_writer(
        hasher_to_id(header.hasher) as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        writer,
    )
    .map_err(lotus_err)?;
    lotus_encode_into_writer(
        header.seed_order_version as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        writer,
    )
    .map_err(lotus_err)?;
    lotus_encode_into_writer(header.layer_count as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(header.hash_bits as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(header.original_len, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(
        header.outer_payload_bit_len,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        writer,
    )
    .map_err(lotus_err)?;
    let masked = header.output_hash & hash_mask(header.hash_bits);
    writer
        .write_bits(masked, header.hash_bits)
        .map_err(lotus_err)?;
    Ok(())
}

/// Encode a layer descriptor into a shared `BitWriter`. The hash field is
/// emitted as a raw `hash_bits`-wide chunk; everything else is
/// Lotus-encoded.
pub fn encode_layer_descriptor_into(
    layer: &TlmrV2LayerDescriptor,
    hash_bits: usize,
    writer: &mut BitWriter,
) -> Result<(), TelomereError> {
    if layer.max_seed_len == 0
        || layer.max_seed_len > u8::MAX as usize
        || layer.max_span_len == 0
        || layer.max_span_len > u16::MAX as usize
        || layer.block_size == 0
        || layer.block_size > u16::MAX as usize
        || layer.span_step == 0
        || layer.span_step > u16::MAX as usize
    {
        return Err(TelomereError::Header("invalid v2 layer descriptor".into()));
    }
    if !(1..=64).contains(&hash_bits) {
        return Err(TelomereError::Header("hash_bits must be in 1..=64".into()));
    }
    lotus_encode_into_writer(layer.decoded_len, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    let masked_hash = layer.decoded_hash & hash_mask(hash_bits);
    writer
        .write_bits(masked_hash, hash_bits)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(layer.max_seed_len as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(layer.max_span_len as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(layer.block_size as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(layer.tier_policy as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    lotus_encode_into_writer(layer.span_step as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
        .map_err(lotus_err)?;
    Ok(())
}

/// Decode a layer descriptor from a shared `BitReader`. Mirrors
/// [`encode_layer_descriptor_into`].
pub fn decode_layer_descriptor_from(
    reader: &mut BitReader<'_>,
    hash_bits: usize,
) -> Result<TlmrV2LayerDescriptor, TelomereError> {
    if !(1..=64).contains(&hash_bits) {
        return Err(TelomereError::Header("hash_bits must be in 1..=64".into()));
    }
    let (decoded_len, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let decoded_hash = reader.read_bits(hash_bits).map_err(lotus_err)?;
    let (max_seed_len_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let max_seed_len = usize::try_from(max_seed_len_u64)
        .map_err(|_| TelomereError::Header("invalid v2 max_seed_len".into()))?;
    let (max_span_len_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let max_span_len = usize::try_from(max_span_len_u64)
        .map_err(|_| TelomereError::Header("invalid v2 max_span_len".into()))?;
    let (block_size_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let block_size = usize::try_from(block_size_u64)
        .map_err(|_| TelomereError::Header("invalid v2 block_size".into()))?;
    let (tier_policy_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let tier_policy = u8::try_from(tier_policy_u64)
        .map_err(|_| TelomereError::Header("invalid v2 tier policy".into()))?;
    let (span_step_u64, _) =
        lotus_decode_from_reader(reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let span_step = usize::try_from(span_step_u64)
        .map_err(|_| TelomereError::Header("invalid v2 span_step".into()))?;

    let valid_policy = match tier_policy {
        V2_TIER_POLICY_SEED_SPAN => {
            max_seed_len != 0
                && max_seed_len <= MAX_V2_SEED_LEN
                && max_span_len != 0
                && (1..=MAX_BLOCK_SIZE).contains(&block_size)
                && block_size <= max_span_len
                && span_step != 0
                && span_step <= block_size
                && span_step <= max_span_len
        }
        V2_TIER_POLICY_PUBLIC_PRESET_SELECTIVE => {
            // Pin the layer descriptor's span_step (which carries the
            // public-preset wire-format version) to exactly the current
            // version. Older raw-byte framings are intentionally not
            // backwards-compatible — the decoder cannot parse them.
            max_seed_len == 1
                && max_span_len != 0
                && (1..=u16::MAX as usize).contains(&block_size)
                && span_step == PUBLIC_PRESET_SELECTIVE_VERSION
        }
        V2_TIER_POLICY_FIXED_SEED_SPAN => {
            max_seed_len != 0
                && max_seed_len <= MAX_V2_SEED_LEN
                && max_span_len != 0
                && max_span_len <= u16::MAX as usize
                && block_size == max_span_len
                && span_step != 0
                && span_step <= max_span_len
        }
        _ => false,
    };
    if !valid_policy || decoded_hash & !hash_mask(hash_bits) != 0 {
        return Err(TelomereError::Header("invalid v2 layer descriptor".into()));
    }
    Ok(TlmrV2LayerDescriptor {
        decoded_len,
        decoded_hash,
        max_seed_len,
        max_span_len,
        block_size,
        tier_policy,
        span_step,
    })
}

fn hasher_to_id(hasher: HasherKind) -> u8 {
    match hasher {
        HasherKind::Blake3 => 1,
        HasherKind::Sha256 | HasherKind::Sha256Ni => 2,
    }
}

fn id_to_hasher(id: u8) -> Result<HasherKind, TelomereError> {
    match id {
        1 => Ok(HasherKind::Blake3),
        2 => Ok(HasherKind::Sha256),
        _ => Err(TelomereError::Header("invalid v2 hasher id".into())),
    }
}

fn hash_mask(bits: usize) -> u64 {
    if bits >= 64 {
        u64::MAX
    } else {
        (1u64 << bits) - 1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn v2_seed_span_record_short_is_under_three_bytes() {
        // Old encoding: 1 tag + 2 span + 1 lotus_len + 1 lotus_payload = 5 bytes (40 bits).
        // New encoding: 3 Lotus values in J3D2 packed back-to-back.
        // For (span_len=8, seed=[0], max_seed_len=1) the new wire format
        // produces 22 bits (3 bytes) — a 45% reduction from the old 40 bits.
        let encoded = v2_seed_span_record(8, &[0x00], 1).unwrap();
        assert_eq!(encoded.bit_len, 22);
        assert_eq!(encoded.bytes.len(), 3);
    }

    #[test]
    fn v2_seed_span_record_roundtrip_via_layer_payload() {
        let max_seed_len = 1;
        let seed = vec![0x00u8];
        let span_len = 4usize;
        let expander = HasherKind::Sha256.get_expander();
        let mut expanded = vec![0u8; span_len];
        expander.expand_into(&seed, &mut expanded);

        let mut writer = BitWriter::new();
        v2_seed_span_record_into_writer(&mut writer, span_len, &seed, max_seed_len).unwrap();
        let payload = writer.into_bytes();
        let descriptor = TlmrV2LayerDescriptor::for_decoded_bytes(
            &expanded,
            HasherKind::Sha256,
            max_seed_len,
            span_len,
            span_len,
            13,
        );
        let decoded = decode_v2_payload(&payload, &descriptor, HasherKind::Sha256).unwrap();
        assert_eq!(decoded, expanded);
    }

    #[test]
    fn v2_fixed_seed_span_record_omits_span_len() {
        let seed = [0x00u8];
        let normal_bits = v2_seed_span_record_bit_len(16, &seed, 1).unwrap();
        let fixed_bits = v2_fixed_seed_span_record_bit_len(&seed, 1).unwrap();
        assert_eq!(fixed_bits, 12);
        assert_eq!(normal_bits - fixed_bits, 11);
    }

    #[test]
    fn v2_fixed_seed_span_record_roundtrip_via_layer_payload() {
        let max_seed_len = 1;
        let seed = vec![0x00u8];
        let span_len = 16usize;
        let expander = HasherKind::Sha256.get_expander();
        let mut expanded = vec![0u8; span_len];
        expander.expand_into(&seed, &mut expanded);

        let mut writer = BitWriter::new();
        v2_fixed_seed_span_record_into_writer(&mut writer, &seed, max_seed_len).unwrap();
        let payload = writer.into_bytes();
        let descriptor = TlmrV2LayerDescriptor::for_fixed_seed_span_decoded_bytes(
            &expanded,
            HasherKind::Sha256,
            max_seed_len,
            span_len,
            1,
            13,
        );
        let decoded = decode_v2_payload(&payload, &descriptor, HasherKind::Sha256).unwrap();
        assert_eq!(decoded, expanded);
    }

    #[test]
    fn v2_literal_record_roundtrip_via_layer_payload() {
        let bytes = b"hello".to_vec();
        let mut writer = BitWriter::new();
        v2_literal_record_into_writer(&mut writer, &bytes).unwrap();
        let payload = writer.into_bytes();
        let descriptor = TlmrV2LayerDescriptor::for_decoded_bytes(
            &bytes,
            HasherKind::Sha256,
            1,
            bytes.len(),
            bytes.len(),
            13,
        );
        let decoded = decode_v2_payload(&payload, &descriptor, HasherKind::Sha256).unwrap();
        assert_eq!(decoded, bytes);
    }

    #[test]
    fn v2_records_pack_back_to_back() {
        let max_seed_len = 1;
        let seed = vec![0x00u8];
        let expander = HasherKind::Sha256.get_expander();
        let mut expanded = vec![0u8; 8];
        expander.expand_into(&seed, &mut expanded);

        let literal = b"!!literal!!".to_vec();
        let mut decoded_expected = expanded.clone();
        decoded_expected.extend_from_slice(&literal);

        let mut writer = BitWriter::new();
        v2_seed_span_record_into_writer(&mut writer, 8, &seed, max_seed_len).unwrap();
        v2_literal_record_into_writer(&mut writer, &literal).unwrap();
        let payload = writer.into_bytes();

        let descriptor = TlmrV2LayerDescriptor::for_decoded_bytes(
            &decoded_expected,
            HasherKind::Sha256,
            max_seed_len,
            8,
            8,
            13,
        );
        let decoded = decode_v2_payload(&payload, &descriptor, HasherKind::Sha256).unwrap();
        assert_eq!(decoded, decoded_expected);
    }

    #[test]
    fn v2_seed_span_record_byte_len_matches_writer() {
        let max_seed_len = 1;
        for span_len in [1usize, 4, 8, 16, 64, 1024, 65535] {
            for seed_byte in [0u8, 1, 255] {
                let bits =
                    v2_seed_span_record_bit_len(span_len, &[seed_byte], max_seed_len).unwrap();
                let encoded = v2_seed_span_record(span_len, &[seed_byte], max_seed_len).unwrap();
                assert_eq!(encoded.bit_len, bits);
            }
        }
    }

    #[test]
    fn v2_literal_record_pads_within_a_record() {
        // For a standalone literal of length 1, the first lotus encodings sum
        // to some bit count; the standalone form pads to the next byte before
        // the raw payload. Ensure bytes length equals ceil(bit_len/8).
        let r = v2_literal_record(b"x").unwrap();
        assert_eq!(r.bytes.len(), r.bit_len.div_ceil(8));
        // The raw payload byte ("x") sits on a byte boundary within the
        // standalone bytes — assert by parsing.
        let descriptor =
            TlmrV2LayerDescriptor::for_decoded_bytes(b"x", HasherKind::Sha256, 1, 1, 1, 13);
        let decoded = decode_v2_payload(&r.bytes, &descriptor, HasherKind::Sha256).unwrap();
        assert_eq!(decoded, b"x");
    }

    #[test]
    fn v2_header_lotus_roundtrip() {
        // Build a header, encode it standalone, decode it, and check fields.
        // The standalone form must include exactly the magic + version + a
        // bit-stream of all configured fields.
        let header = TlmrV2Header {
            version: TLMR_V2_FORMAT_VERSION,
            lotus_preset: LOTUS_PRESET_V2,
            hasher: HasherKind::Sha256,
            seed_order_version: V2_SEED_ORDER_VERSION,
            layer_count: 2,
            hash_bits: 13,
            original_len: 1024,
            outer_payload_bit_len: 800,
            output_hash: 0x1abc,
        };
        let bytes = encode_tlmr_v2_header(&header).unwrap();
        // Header should be much smaller than the old 48-byte fixed layout.
        assert!(bytes.len() < 20, "expected <20 bytes, got {}", bytes.len());
        let decoded = decode_tlmr_v2_header(&bytes).unwrap();
        assert_eq!(decoded.version, header.version);
        assert_eq!(decoded.lotus_preset, header.lotus_preset);
        assert_eq!(decoded.hasher, header.hasher);
        assert_eq!(decoded.seed_order_version, header.seed_order_version);
        assert_eq!(decoded.layer_count, header.layer_count);
        assert_eq!(decoded.hash_bits, header.hash_bits);
        assert_eq!(decoded.original_len, header.original_len);
        assert_eq!(decoded.outer_payload_bit_len, header.outer_payload_bit_len);
        assert_eq!(decoded.output_hash, header.output_hash);
    }

    #[test]
    fn v2_layer_descriptor_lotus_roundtrip() {
        let descriptor = TlmrV2LayerDescriptor {
            decoded_len: 1024,
            decoded_hash: 0x1234,
            max_seed_len: 1,
            max_span_len: 8,
            block_size: 4,
            tier_policy: V2_TIER_POLICY_SEED_SPAN,
            span_step: 4,
        };
        let mut writer = BitWriter::new();
        encode_layer_descriptor_into(&descriptor, 13, &mut writer).unwrap();
        let bytes = writer.into_bytes();
        // The fixed layout used to be 32 bytes; the Lotus form should be
        // substantially smaller for this representative descriptor.
        assert!(bytes.len() < 16, "expected <16 bytes, got {}", bytes.len());
        let mut reader = BitReader::new(&bytes);
        let decoded = decode_layer_descriptor_from(&mut reader, 13).unwrap();
        assert_eq!(decoded.decoded_len, descriptor.decoded_len);
        assert_eq!(decoded.decoded_hash, descriptor.decoded_hash);
        assert_eq!(decoded.max_seed_len, descriptor.max_seed_len);
        assert_eq!(decoded.max_span_len, descriptor.max_span_len);
        assert_eq!(decoded.block_size, descriptor.block_size);
        assert_eq!(decoded.tier_policy, descriptor.tier_policy);
        assert_eq!(decoded.span_step, descriptor.span_step);
    }

    #[test]
    fn full_v2_file_with_records_roundtrips() {
        // Build a v2 file with header, one descriptor, and a small record
        // payload. Encode, decode, verify roundtrip works through the new
        // bit-stream framing.
        let max_seed_len = 1;
        let seed = vec![0x00u8];
        let span_len = 4usize;
        let expander = HasherKind::Sha256.get_expander();
        let mut expanded = vec![0u8; span_len];
        expander.expand_into(&seed, &mut expanded);

        let mut writer = BitWriter::new();
        v2_seed_span_record_into_writer(&mut writer, span_len, &seed, max_seed_len).unwrap();
        let payload = writer.into_bytes();
        let layer = TlmrV2LayerDescriptor::for_decoded_bytes(
            &expanded,
            HasherKind::Sha256,
            max_seed_len,
            span_len,
            span_len,
            13,
        );
        let encoded = encode_v2_file(
            HasherKind::Sha256,
            13,
            expanded.len() as u64,
            std::slice::from_ref(&layer),
            &payload,
        )
        .unwrap();

        let (header, descriptors, payload_start) =
            decode_v2_header_and_descriptors(&encoded).unwrap();
        assert_eq!(header.version, TLMR_V2_FORMAT_VERSION);
        assert_eq!(header.layer_count, 1);
        assert_eq!(descriptors.len(), 1);
        assert_eq!(descriptors[0].decoded_len, layer.decoded_len);
        assert_eq!(payload_start + payload.len(), encoded.len());

        let recovered = decompress_v2_with_limit(&encoded, usize::MAX, usize::MAX).unwrap();
        assert_eq!(recovered, expanded);
    }

    #[test]
    fn v2_decoder_rejects_old_version() {
        // A version byte other than 3 must be rejected with a descriptive
        // error so callers know they're seeing an old/unknown format.
        let mut bytes = encode_tlmr_v2_header(&TlmrV2Header {
            version: TLMR_V2_FORMAT_VERSION,
            lotus_preset: LOTUS_PRESET_V2,
            hasher: HasherKind::Sha256,
            seed_order_version: V2_SEED_ORDER_VERSION,
            layer_count: 1,
            hash_bits: 13,
            original_len: 0,
            outer_payload_bit_len: 0,
            output_hash: 0,
        })
        .unwrap();
        bytes[4] = 2; // pretend this is a v2-format-version-2 file
        let err = decode_tlmr_v2_header(&bytes).unwrap_err();
        assert!(err.to_string().contains("unsupported v2 format version"));
    }
}
