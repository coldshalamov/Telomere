use crate::config::HasherKind;
use crate::hasher::SeedExpander;
use crate::header::{LOTUS_J_BITS, LOTUS_TIERS};
use crate::TelomereError;
use lotus::{
    lotus_decode_from_reader, lotus_encode_into_writer, BitReader as LotusBitReader,
    BitWriter as LotusBitWriter, LotusError,
};

pub const TLMR_MAGIC: [u8; 4] = *b"TLMR";
/// V1 format version. Bumped to 2 with the variable-length Lotus-encoded
/// header that replaces the legacy 40-byte fixed layout.
pub const TLMR_FORMAT_VERSION: u8 = 2;
pub const LOTUS_PRESET_VERSION: u8 = 2;
pub const MAX_BLOCK_SIZE: usize = 16;
pub const MAX_SEED_LEN: usize = 3;
pub const MAX_ARITY: u8 = 5;
pub const MAX_HASH_BITS: usize = 64;
/// Length of the raw "TLMR" magic + version byte prefix. Everything after
/// these 5 bytes is a Lotus bit stream followed by zero-pad to a byte boundary.
pub const V1_MAGIC_VERSION_LEN: usize = 5;

/// Rich Telomere file header used by the active `.tlmr` v1 format.
///
/// Version 2 replaces the old 40-byte fixed layout with a variable-length
/// Lotus-encoded bit stream. The 5-byte prefix (magic + version) stays raw so
/// detectors can identify the format without parsing Lotus; everything else is
/// routed through the real lotus crate. `payload_bit_len` is the meaningful
/// bit count in the records payload that follows the header — the header is
/// byte-aligned via zero pad so the payload begins at a byte offset.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TlmrHeader {
    pub version: u8,
    pub lotus_preset: u8,
    pub hasher: HasherKind,
    pub block_size: usize,
    pub last_block_size: usize,
    pub max_seed_len: usize,
    pub max_arity: u8,
    pub hash_bits: usize,
    pub layer_count: u8,
    pub original_len: u64,
    /// Number of meaningful bits in the records payload section. The payload
    /// byte slice on disk is `ceil(payload_bit_len / 8)` bytes; trailing 0-7
    /// bits in the final byte must be zero pad.
    pub payload_bit_len: u64,
    pub output_hash: u64,
}

fn hasher_to_id(hasher: HasherKind) -> u8 {
    match hasher {
        HasherKind::Blake3 => 1,
        HasherKind::Sha256 | HasherKind::Sha256Ni => 2,
    }
}

fn invalid_field(context: &str) -> TelomereError {
    TelomereError::Header(format!("v1 header invalid field: {context}"))
}

fn id_to_hasher(id: u8) -> Result<HasherKind, TelomereError> {
    match id {
        1 => Ok(HasherKind::Blake3),
        2 => Ok(HasherKind::Sha256),
        _ => Err(invalid_field("hasher id")),
    }
}

fn hash_mask(bits: usize) -> u64 {
    if bits >= 64 {
        u64::MAX
    } else {
        (1u64 << bits) - 1
    }
}

fn lotus_err(e: LotusError) -> TelomereError {
    TelomereError::Header(format!("v1 lotus: {e}"))
}

fn validate_header(header: &TlmrHeader) {
    assert_eq!(
        header.version, TLMR_FORMAT_VERSION,
        "unsupported format version"
    );
    assert_eq!(
        header.lotus_preset, LOTUS_PRESET_VERSION,
        "unsupported Lotus preset"
    );
    assert!(
        (1..=MAX_BLOCK_SIZE).contains(&header.block_size),
        "block size out of range"
    );
    assert!(
        (1..=header.block_size).contains(&header.last_block_size),
        "last block size out of range"
    );
    assert!(
        (1..=MAX_SEED_LEN).contains(&header.max_seed_len),
        "max seed length out of range"
    );
    assert!(
        (1..=MAX_ARITY).contains(&header.max_arity),
        "max arity out of range"
    );
    assert!(
        (1..=MAX_HASH_BITS).contains(&header.hash_bits),
        "hash bits out of range"
    );
    assert_eq!(
        header.layer_count, 1,
        "only one-layer files are supported in v1"
    );
    assert!(
        header.output_hash & !hash_mask(header.hash_bits) == 0,
        "output hash exceeds hash_bits"
    );
}

/// Encode the active `.tlmr` v1 header. The result is the raw 5-byte prefix
/// (magic + version) followed by a Lotus bit stream padded to a byte boundary
/// with zero bits.
pub fn encode_tlmr_header(header: &TlmrHeader) -> Vec<u8> {
    validate_header(header);

    let mut writer = LotusBitWriter::new();
    // SAFETY: `validate_header` (assertion-checked above) enforces all field
    // ranges. The Lotus encoder cannot fail for these in-range values, but we
    // unwrap defensively because validation also guarantees no preset
    // misconfiguration.
    lotus_encode_into_writer(
        header.lotus_preset as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode preset");
    lotus_encode_into_writer(
        hasher_to_id(header.hasher) as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode hasher");
    lotus_encode_into_writer(
        header.block_size as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode block_size");
    lotus_encode_into_writer(
        header.last_block_size as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode last_block_size");
    lotus_encode_into_writer(
        header.max_seed_len as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode max_seed_len");
    lotus_encode_into_writer(
        header.max_arity as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode max_arity");
    lotus_encode_into_writer(
        header.hash_bits as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode hash_bits");
    lotus_encode_into_writer(
        header.layer_count as u64,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode layer_count");
    lotus_encode_into_writer(header.original_len, LOTUS_J_BITS, LOTUS_TIERS, &mut writer)
        .expect("lotus encode original_len");
    lotus_encode_into_writer(
        header.payload_bit_len,
        LOTUS_J_BITS,
        LOTUS_TIERS,
        &mut writer,
    )
    .expect("lotus encode payload_bit_len");
    // Truncated output hash: raw `hash_bits`-wide bit chunk.
    let masked = header.output_hash & hash_mask(header.hash_bits);
    writer
        .write_bits(masked, header.hash_bits)
        .expect("write output hash");
    // Pad to byte boundary so the records payload starts on a byte offset.
    let bits = writer.bits_written();
    let pad = (8 - (bits % 8)) % 8;
    if pad > 0 {
        writer.write_bits(0, pad).expect("write header pad");
    }
    let body = writer.into_bytes();

    let mut out = Vec::with_capacity(V1_MAGIC_VERSION_LEN + body.len());
    out.extend_from_slice(&TLMR_MAGIC);
    out.push(header.version);
    out.extend_from_slice(&body);
    out
}

/// Decode the active `.tlmr` v1 header from the start of `data`. Returns the
/// header on success. The number of bytes consumed (including the 5-byte
/// magic+version prefix) can be obtained via [`tlmr_header_byte_len`].
pub fn decode_tlmr_header(data: &[u8]) -> Result<TlmrHeader, TelomereError> {
    let (header, _) = decode_tlmr_header_with_len(data)?;
    Ok(header)
}

/// Decode the v1 header and return both the parsed fields and the byte
/// offset where the records payload begins. The header section is padded to
/// a byte boundary so the offset is exact.
pub fn decode_tlmr_header_with_len(data: &[u8]) -> Result<(TlmrHeader, usize), TelomereError> {
    if data.len() < V1_MAGIC_VERSION_LEN {
        return Err(TelomereError::Header("v1 header too short".into()));
    }
    if data[0..4] != TLMR_MAGIC {
        return Err(invalid_field("magic"));
    }
    let version = data[4];
    if version != TLMR_FORMAT_VERSION {
        return Err(invalid_field("version"));
    }
    let tail = &data[V1_MAGIC_VERSION_LEN..];
    let mut reader = LotusBitReader::new(tail);

    let (lotus_preset_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let lotus_preset = u8::try_from(lotus_preset_u64).map_err(|_| invalid_field("lotus_preset"))?;
    let (hasher_id_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let hasher_id = u8::try_from(hasher_id_u64).map_err(|_| invalid_field("hasher_id"))?;
    let hasher = id_to_hasher(hasher_id)?;
    let (block_size_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let block_size = usize::try_from(block_size_u64).map_err(|_| invalid_field("block_size"))?;
    let (last_block_size_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let last_block_size =
        usize::try_from(last_block_size_u64).map_err(|_| invalid_field("last_block_size"))?;
    let (max_seed_len_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let max_seed_len =
        usize::try_from(max_seed_len_u64).map_err(|_| invalid_field("max_seed_len"))?;
    let (max_arity_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let max_arity = u8::try_from(max_arity_u64).map_err(|_| invalid_field("max_arity"))?;
    let (hash_bits_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let hash_bits = usize::try_from(hash_bits_u64).map_err(|_| invalid_field("hash_bits"))?;
    let (layer_count_u64, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let layer_count = u8::try_from(layer_count_u64).map_err(|_| invalid_field("layer_count"))?;
    let (original_len, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;
    let (payload_bit_len, _) =
        lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(lotus_err)?;

    if !(1..=MAX_HASH_BITS).contains(&hash_bits) {
        return Err(invalid_field("hash_bits range"));
    }
    let output_hash = reader.read_bits(hash_bits).map_err(lotus_err)?;

    // Consume trailing pad bits to byte boundary; pad bits must all be zero.
    let consumed = reader.bits_consumed();
    let pad = (8 - (consumed % 8)) % 8;
    if pad > 0 {
        let pad_value = reader.read_bits(pad).map_err(lotus_err)?;
        if pad_value != 0 {
            return Err(invalid_field("nonzero header pad bit"));
        }
    }
    let consumed_bits = reader.bits_consumed();
    debug_assert!(consumed_bits.is_multiple_of(8));
    let header_end = V1_MAGIC_VERSION_LEN + (consumed_bits / 8);

    let header = TlmrHeader {
        version,
        lotus_preset,
        hasher,
        block_size,
        last_block_size,
        max_seed_len,
        max_arity,
        hash_bits,
        layer_count,
        original_len,
        payload_bit_len,
        output_hash,
    };

    if lotus_preset != LOTUS_PRESET_VERSION {
        return Err(invalid_field("lotus_preset value"));
    }
    if !(1..=MAX_BLOCK_SIZE).contains(&block_size) {
        return Err(invalid_field("block_size range"));
    }
    if !(1..=block_size).contains(&last_block_size) {
        return Err(invalid_field("last_block_size range"));
    }
    if !(1..=MAX_SEED_LEN).contains(&max_seed_len) {
        return Err(invalid_field("max_seed_len range"));
    }
    if !(1..=MAX_ARITY).contains(&max_arity) {
        return Err(invalid_field("max_arity range"));
    }
    if !(1..=MAX_HASH_BITS).contains(&hash_bits) {
        return Err(invalid_field("hash_bits range"));
    }
    if layer_count != 1 {
        return Err(invalid_field("layer_count must be 1"));
    }
    if output_hash & !hash_mask(hash_bits) != 0 {
        return Err(invalid_field("output_hash exceeds hash_bits"));
    }

    Ok((header, header_end))
}

/// Return the on-disk byte length of the encoded v1 header for `data` (the
/// offset where the records payload begins). This is a thin wrapper for
/// callers that don't need the parsed header.
pub fn tlmr_header_byte_len(data: &[u8]) -> Result<usize, TelomereError> {
    let (_, end) = decode_tlmr_header_with_len(data)?;
    Ok(end)
}

/// Compute a low-bit truncated digest of the provided bytes using the given expander.
pub fn truncated_hash_bits(data: &[u8], expander: &dyn SeedExpander, bits: usize) -> u64 {
    assert!(
        (1..=MAX_HASH_BITS).contains(&bits),
        "hash bits out of range"
    );
    let digest = expander.digest(data);
    let low = u64::from_be_bytes(digest[24..32].try_into().unwrap());
    low & hash_mask(bits)
}

/// Compute the legacy/default 13-bit truncated digest.
pub fn truncated_hash(data: &[u8], expander: &dyn SeedExpander) -> u16 {
    truncated_hash_bits(data, expander, 13) as u16
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_header() -> TlmrHeader {
        TlmrHeader {
            version: TLMR_FORMAT_VERSION,
            lotus_preset: LOTUS_PRESET_VERSION,
            hasher: HasherKind::Blake3,
            block_size: 4,
            last_block_size: 2,
            max_seed_len: 1,
            max_arity: 5,
            hash_bits: 13,
            layer_count: 1,
            original_len: 10,
            payload_bit_len: 80,
            output_hash: 0x0123,
        }
    }

    #[test]
    fn lotus_header_roundtrip() {
        let header = sample_header();
        let bytes = encode_tlmr_header(&header);
        let decoded = decode_tlmr_header(&bytes).unwrap();
        assert_eq!(decoded, header);
    }

    #[test]
    fn typical_header_is_smaller_than_legacy_40_bytes() {
        let header = sample_header();
        let bytes = encode_tlmr_header(&header);
        assert!(
            bytes.len() < 40,
            "expected v1 header < 40 bytes (was {} bytes)",
            bytes.len()
        );
        // For the sample config (hash_bits=13, max_seed_len=1, max_arity=5,
        // block_size=4) the Lotus-encoded header is well under half the
        // legacy 40-byte layout.
        assert!(
            bytes.len() <= 20,
            "expected v1 header <= 20 bytes, got {}",
            bytes.len()
        );
    }

    #[test]
    fn header_starts_with_tlmr_magic_and_version() {
        let header = sample_header();
        let bytes = encode_tlmr_header(&header);
        assert_eq!(&bytes[0..4], b"TLMR");
        assert_eq!(bytes[4], TLMR_FORMAT_VERSION);
    }

    #[test]
    fn decode_rejects_old_version_byte() {
        let header = sample_header();
        let mut bytes = encode_tlmr_header(&header);
        bytes[4] = 1; // pre-Wave-D version
        assert!(decode_tlmr_header(&bytes).is_err());
    }
}
