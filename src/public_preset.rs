use crate::config::HasherKind;
use crate::TelomereError;
use lotus::{
    lotus_decode_from_reader, lotus_encode_into_writer, BitReader as LotusBitReader,
    BitWriter as LotusBitWriter, LotusError,
};
use serde::Serialize;
use std::collections::HashMap;

/// Version 3 layout uses a Lotus bit-stream framing (see module docs below).
/// Older raw-byte framings (versions 1 and 2) are intentionally NOT supported
/// by the current decoder; the layer descriptor validator pins the wire format
/// to exactly this version.
pub const PUBLIC_PRESET_SELECTIVE_VERSION: usize = 5;
pub const PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN: usize = 13;
pub const PUBLIC_PRESET_CODEWORD_LEN: usize = 16;

/// Lotus J3D2 preset shared with v1 records and v2 seed-span records.
const LOTUS_J_BITS: usize = crate::header::LOTUS_J_BITS;
const LOTUS_TIERS: usize = crate::header::LOTUS_TIERS;

/// Lotus tag values that identify a frame in the public-preset selective
/// transform's bit-stream. The codeword frame is the common case and gets the
/// shorter Lotus code (value 0 < value 1 under J3D2).
pub const PUBLIC_PRESET_FRAME_TAG_CODEWORD: u64 = 0;
pub const PUBLIC_PRESET_FRAME_TAG_LITERAL: u64 = 1;

pub const PUBLIC_PRESET_TOKENS: &[&[u8]] = &[
    b"\"event\":",
    b"\"id\":",
    b"\"sku\":",
    b"\"status\":",
    b"\"amount_cents\":",
    b"\"order_update\"",
    b"\"queued\"",
    b"\"paid\"",
    b"\"fulfilled\"",
    b"\"$schema\":",
    b"\"properties\":",
    b"\"required\":",
    b"\"type\":",
    b"\"object\"",
    b"\"integer\"",
    b"\"boolean\"",
    b"city,region,country,population\n",
    b",United States,",
    b"Create an HTTP",
    b"Request::builder()",
    b"Response::builder()",
    b".header(",
    b".body(())",
    b"Some(",
    b"None",
    b"Option",
    b"level=INFO event=order_update",
    b"event=order_update",
    b"status=fulfilled",
    b"amount_cents=",
    b"region=us-east-1",
    // Frozen from held-out-free public schema/record fixtures. Keep append-only
    // so existing token seed assignments remain stable.
    b"          \"type\"",
    b"         \"type\":",
    b"        \"type\": ",
    b"       \"type\": \"",
    b",MA,United State",
    b"MA,United States",
    b"s\": {\n          ",
    b"\n            \"St",
    b"              \"t",
    b"             \"ty",
    b"            \"Str",
    b"            \"typ",
    b"           \"type",
    b"  \"properties\": ",
    b"  \"required\": [\n",
    b"  \"type\": \"objec",
    b" \"properties\": {",
    b" \"required\": [\n ",
    b" \"type\": \"object",
    b"\"properties\": {\n",
    b"\"required\": [\n  ",
    b"\"type\": \"object\"",
    b"e\": \"object\",\n  ",
    b"equired\": [\n    ",
    b"operties\": {\n   ",
    b"pe\": \"object\",\n ",
    b"perties\": {\n    ",
    b"properties\": {\n ",
    b"required\": [\n   ",
    b"roperties\": {\n  ",
    b"type\": \"object\",",
    // Frozen Rust source-family preset trained from public rust-src files with
    // core/src/result.rs, core/src/option.rs, alloc/src/string.rs, and
    // std/src/path.rs held out. Keep append-only so earlier token seed
    // assignments remain stable.
    b"#[stable(feature",
    b"#[inline",
    b"Examples",
    b"[inline]",
    b"self) ->",
    b"#[unstable(featu",
    b"pub const",
    b"function",
    b"\"rust1\", since =",
    b"= \"rust1\", since",
    b"#[rustc_",
    b"// SAFETY:",
    b"= \"1.0.0\")]",
    b"/// This",
    b"implementation",
    b"pub struct",
    b"the same",
    b"/// Returns",
    b"mut self,",
    b"-> fmt::Result",
    b"unsafe fn",
    b"fn fmt( self,",
    b"mut self)",
    b"#[must_use",
    b"/// let mut",
    b"Returns the",
    b"does not",
    b"reference",
    b"that the",
    b"target_os =",
    b"io::Result<()>",
    b"fmt( self, f:",
    b"const fn",
    b"returned",
    b"![stable(feature",
    b"with the",
    b"iterator",
    b"self, f: mut",
    b"fmt::Debug for",
    b"= unsafe",
    b"documentation",
    b"the value",
    b"from the",
    b"elements",
    b"the underlying",
    b"Note that",
    b"#[derive(",
    b"assert_eq!(",
    b"the current",
    b"number of",
    b"= \"1.1.0\")]",
    b"[must_use =",
    b"/// Creates",
    b"pub(crate)",
    b"\"raw_ext\", since",
    b"operation",
    b"issue = \"none\")]",
    b"#[cfg(not(",
    b"guaranteed",
    b"returns the",
    b"the result",
    b"stringify!(",
    b"#[cfg(target_",
    b"[must_use]",
    b"```no_run",
    b"the number",
    b"/// Safety",
    b"Creates a",
    b"the original",
    b"use crate::",
    b"fn main()",
    b"self, other:",
    b"impl fmt::Debug",
    b"fmt::Display for",
    b"= \"raw_ext\",",
    b"0, 0, 0,",
    b"usize) ->",
    b"currently",
    b"should be",
    b"#[doc(hidden)]",
    b"#[doc = ",
    b"pub unsafe",
    b"the following",
    b"#[cfg_attr(",
    b"fn next( mut",
    b"implemented",
    b"[derive(Debug)]",
    b"returning",
    b"that this",
    b"behavior",
    b"This method",
    b"Iterator for",
    b"the first",
    b"type Item =",
    b"value is",
    b"size_hint( self)",
    b"fn drop( mut",
    b"equivalent",
    b"initialized",
    b"instead of",
    b"different",
    b"possible",
    b"Returns a",
    b"value of",
    b"macro_rules!",
    b"specified",
    b"the caller",
    b"/// Panics",
    b"information",
    b"means that",
    b"[inline(always)]",
    b"the given",
    b"will return",
    b"which is",
    b"-> Result<(),",
    b"contains",
    b"provided",
    b"-> usize",
    b"pub(super)",
    b"For example,",
    b"available",
    b"Option<usize>)",
    b"println!(\"",
    b"representation",
    b"let result =",
    b"is created by",
    b"#[track_caller]",
    b"result of",
];

#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct PublicPresetTransformStats {
    pub preset_version: usize,
    pub min_token_len: usize,
    pub codeword_len: usize,
    pub token_count: usize,
    pub token_replacements: usize,
    pub literal_bytes: usize,
    pub transformed_bytes: usize,
}

fn lotus_err(e: LotusError) -> TelomereError {
    TelomereError::Header(format!("lotus codec error: {e}"))
}

/// Encode `data` as a stream of public-preset selective frames using full
/// Lotus framing. Wire layout (MSB-first bit stream):
///
/// ```text
/// frames* trailing-pad?
///
/// codeword-frame := lotus_J3D2(0=CODEWORD) [pad to byte boundary] [codeword_len raw bytes]
/// literal-frame  := lotus_J3D2(1=LITERAL) lotus_J3D2(len-1) [pad to byte boundary] [len raw bytes]
/// trailing-pad   := 0..7 zero bits to complete the final byte
/// ```
///
/// The raw bytes of a codeword are incompressible hash output; the raw bytes
/// of a literal are bytes the upstream pass already chose to skip. Both ride
/// on byte-aligned offsets so decoders can `memcpy` them out of the underlying
/// buffer.
pub fn public_preset_selective_framed(
    data: &[u8],
    hasher: HasherKind,
    min_token_len: usize,
    codeword_len: usize,
) -> Result<(Vec<u8>, PublicPresetTransformStats), TelomereError> {
    validate_public_preset_params(min_token_len, codeword_len)?;
    let codebook = public_preset_codebook(hasher, min_token_len, codeword_len)?;
    let mut token_order: Vec<&[u8]> = codebook.keys().map(Vec::as_slice).collect();
    token_order.sort_by(|a, b| b.len().cmp(&a.len()).then_with(|| a.cmp(b)));

    let mut writer = LotusBitWriter::new();
    let mut literal: Vec<u8> = Vec::new();
    let mut replacements = 0usize;
    let mut literal_bytes = 0usize;

    for token in &token_order {
        if token.len() < min_token_len {
            return Err(TelomereError::Config(
                "public preset token shorter than min_token_len".into(),
            ));
        }
    }

    let mut pos = 0usize;
    while pos < data.len() {
        let mut matched = None;
        for token in &token_order {
            if data[pos..].starts_with(token) {
                matched = Some(*token);
                break;
            }
        }

        let Some(token) = matched else {
            literal.push(data[pos]);
            pos += 1;
            continue;
        };

        flush_literal_frame(&mut writer, &mut literal, &mut literal_bytes)?;
        let codeword = codebook
            .get(token)
            .ok_or_else(|| TelomereError::Header("missing public preset codeword".into()))?;
        if codeword.len() != codeword_len {
            return Err(TelomereError::Header(
                "public preset codeword length mismatch".into(),
            ));
        }
        lotus_encode_into_writer(
            PUBLIC_PRESET_FRAME_TAG_CODEWORD,
            LOTUS_J_BITS,
            LOTUS_TIERS,
            &mut writer,
        )
        .map_err(lotus_err)?;
        // Byte-align so the codeword payload can be read via memcpy.
        align_writer_to_byte(&mut writer)?;
        for byte in codeword {
            writer.write_bits(*byte as u64, 8).map_err(lotus_err)?;
        }
        replacements += 1;
        pos += token.len();
    }
    flush_literal_frame(&mut writer, &mut literal, &mut literal_bytes)?;

    let out = writer.into_bytes();

    Ok((
        out.clone(),
        PublicPresetTransformStats {
            preset_version: PUBLIC_PRESET_SELECTIVE_VERSION,
            min_token_len,
            codeword_len,
            token_count: codebook.len(),
            token_replacements: replacements,
            literal_bytes,
            transformed_bytes: out.len(),
        },
    ))
}

pub fn public_preset_selective_decode_framed(
    framed: &[u8],
    hasher: HasherKind,
    min_token_len: usize,
    codeword_len: usize,
    output_limit: usize,
) -> Result<Vec<u8>, TelomereError> {
    validate_public_preset_params(min_token_len, codeword_len)?;
    let reverse = public_preset_reverse_codebook(hasher, min_token_len, codeword_len)?;
    let mut reader = LotusBitReader::new(framed);
    let mut out = Vec::new();

    while out.len() < output_limit {
        let (tag, _) = lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS)
            .map_err(|_| TelomereError::Header("truncated public preset frame".into()))?;
        match tag {
            PUBLIC_PRESET_FRAME_TAG_LITERAL => {
                let (len_minus_one, _) =
                    lotus_decode_from_reader(&mut reader, LOTUS_J_BITS, LOTUS_TIERS).map_err(
                        |_| TelomereError::Header("truncated public preset literal length".into()),
                    )?;
                let len_minus_one_usize = usize::try_from(len_minus_one).map_err(|_| {
                    TelomereError::Header(
                        "public preset literal length exceeds platform usize".into(),
                    )
                })?;
                let len = len_minus_one_usize.checked_add(1).ok_or_else(|| {
                    TelomereError::Header("invalid public preset literal length".into())
                })?;
                consume_byte_alignment(&mut reader, "literal")?;
                let next_len = out.len().checked_add(len).ok_or_else(|| {
                    TelomereError::Header("invalid public preset literal frame".into())
                })?;
                if next_len > output_limit {
                    return Err(TelomereError::Header(
                        "public preset output limit exceeded".into(),
                    ));
                }
                for _ in 0..len {
                    let byte = reader.read_bits(8).map_err(|e| {
                        TelomereError::Header(format!("public preset literal byte: {e}"))
                    })?;
                    out.push(byte as u8);
                }
            }
            PUBLIC_PRESET_FRAME_TAG_CODEWORD => {
                consume_byte_alignment(&mut reader, "codeword")?;
                let mut codeword = vec![0u8; codeword_len];
                for slot in codeword.iter_mut() {
                    let byte = reader.read_bits(8).map_err(|e| {
                        TelomereError::Header(format!("public preset codeword byte: {e}"))
                    })?;
                    *slot = byte as u8;
                }
                let token = reverse.get(&codeword).ok_or_else(|| {
                    TelomereError::Header("unknown public preset codeword".into())
                })?;
                let next_len = out.len().checked_add(token.len()).ok_or_else(|| {
                    TelomereError::Header("invalid public preset codeword frame".into())
                })?;
                if next_len > output_limit {
                    return Err(TelomereError::Header(
                        "public preset output limit exceeded".into(),
                    ));
                }
                out.extend_from_slice(token);
            }
            _ => {
                return Err(TelomereError::Header(
                    "unknown public preset frame tag".into(),
                ));
            }
        }
    }

    if out.len() != output_limit {
        return Err(TelomereError::Header(
            "public preset decoded length mismatch".into(),
        ));
    }

    // Every frame ends on a byte boundary, so the writer's final
    // `into_bytes()` never appends any trailing pad bits. After the last
    // frame is consumed, the reader must therefore be at exactly
    // `framed.len() * 8` bits. Any leftover bits indicate truncated or
    // garbage trailing data and must be rejected.
    let consumed = reader.bits_consumed();
    let total_bits = framed.len() * 8;
    if consumed != total_bits {
        return Err(TelomereError::Header(
            "public preset has trailing bits after final frame".into(),
        ));
    }

    Ok(out)
}

fn align_writer_to_byte(writer: &mut LotusBitWriter) -> Result<(), TelomereError> {
    while writer.bits_written() % 8 != 0 {
        writer.write_bits(0, 1).map_err(lotus_err)?;
    }
    Ok(())
}

fn consume_byte_alignment(
    reader: &mut LotusBitReader<'_>,
    frame_kind: &str,
) -> Result<(), TelomereError> {
    while reader.bits_consumed() % 8 != 0 {
        let pad = reader
            .read_bits(1)
            .map_err(|e| TelomereError::Header(format!("public preset {frame_kind} pad: {e}")))?;
        if pad != 0 {
            return Err(TelomereError::Header(format!(
                "nonzero public preset {frame_kind} pad bit"
            )));
        }
    }
    Ok(())
}

fn validate_public_preset_params(
    min_token_len: usize,
    codeword_len: usize,
) -> Result<(), TelomereError> {
    if min_token_len == 0 || min_token_len > u16::MAX as usize {
        return Err(TelomereError::Config(
            "public preset min_token_len must be in 1..=65535".into(),
        ));
    }
    if codeword_len == 0 || codeword_len > u16::MAX as usize {
        return Err(TelomereError::Config(
            "public preset codeword_len must be in 1..=65535".into(),
        ));
    }
    if PUBLIC_PRESET_TOKENS.len() > u8::MAX as usize {
        return Err(TelomereError::Config(
            "public preset token table exceeds one-byte seed space".into(),
        ));
    }
    Ok(())
}

fn public_preset_codebook(
    hasher: HasherKind,
    min_token_len: usize,
    codeword_len: usize,
) -> Result<HashMap<Vec<u8>, Vec<u8>>, TelomereError> {
    let expander = hasher.get_expander();
    let mut codebook = HashMap::new();
    for (idx, token) in PUBLIC_PRESET_TOKENS.iter().enumerate() {
        if token.len() < min_token_len {
            continue;
        }
        let seed = [idx as u8];
        let mut codeword = vec![0; codeword_len];
        expander.expand_into(&seed, &mut codeword);
        codebook.insert(token.to_vec(), codeword);
    }
    Ok(codebook)
}

fn public_preset_reverse_codebook(
    hasher: HasherKind,
    min_token_len: usize,
    codeword_len: usize,
) -> Result<HashMap<Vec<u8>, Vec<u8>>, TelomereError> {
    let mut reverse = HashMap::new();
    for (token, codeword) in public_preset_codebook(hasher, min_token_len, codeword_len)? {
        if reverse.insert(codeword, token).is_some() {
            return Err(TelomereError::Header(
                "public preset codeword collision".into(),
            ));
        }
    }
    Ok(reverse)
}

fn flush_literal_frame(
    writer: &mut LotusBitWriter,
    literal: &mut Vec<u8>,
    literal_bytes: &mut usize,
) -> Result<(), TelomereError> {
    while !literal.is_empty() {
        let take = literal.len().min(u16::MAX as usize);
        lotus_encode_into_writer(
            PUBLIC_PRESET_FRAME_TAG_LITERAL,
            LOTUS_J_BITS,
            LOTUS_TIERS,
            writer,
        )
        .map_err(lotus_err)?;
        // Lotus J3D2 encodes (len-1) for the length field; len is always >= 1
        // in this loop because the outer `while !literal.is_empty()` guards
        // against an empty drain.
        lotus_encode_into_writer((take - 1) as u64, LOTUS_J_BITS, LOTUS_TIERS, writer)
            .map_err(lotus_err)?;
        // Byte-align so the raw payload that follows can be read via memcpy.
        align_writer_to_byte(writer)?;
        for byte in &literal[..take] {
            writer.write_bits(*byte as u64, 8).map_err(lotus_err)?;
        }
        *literal_bytes += take;
        literal.drain(..take);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::HasherKind;

    fn run_roundtrip(input: &[u8]) {
        let (framed, stats) = public_preset_selective_framed(
            input,
            HasherKind::Blake3,
            PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
            PUBLIC_PRESET_CODEWORD_LEN,
        )
        .unwrap();
        assert_eq!(stats.preset_version, PUBLIC_PRESET_SELECTIVE_VERSION);
        let decoded = public_preset_selective_decode_framed(
            &framed,
            HasherKind::Blake3,
            PUBLIC_PRESET_SELECTIVE_MIN_TOKEN_LEN,
            PUBLIC_PRESET_CODEWORD_LEN,
            input.len(),
        )
        .unwrap();
        assert_eq!(decoded, input);
    }

    #[test]
    fn roundtrip_empty() {
        run_roundtrip(b"");
    }

    #[test]
    fn roundtrip_pure_literal() {
        run_roundtrip(b"hello, world without any tokens");
    }

    #[test]
    fn roundtrip_pure_codewords() {
        let mut buf = Vec::new();
        buf.extend_from_slice(b"\"order_update\"");
        buf.extend_from_slice(b"\"amount_cents\":");
        buf.extend_from_slice(b"\"$schema\":");
        run_roundtrip(&buf);
    }

    #[test]
    fn roundtrip_mixed() {
        let mut buf = Vec::new();
        buf.extend_from_slice(b"prefix ");
        buf.extend_from_slice(b"\"order_update\"");
        buf.extend_from_slice(b" middle ");
        buf.extend_from_slice(b"\"amount_cents\":");
        buf.extend_from_slice(b" suffix");
        run_roundtrip(&buf);
    }
}
