use sha2::{Digest, Sha256};

/// Encode a usize using LEB128 variable-length encoding.
pub fn encode_varint(mut value: usize) -> Vec<u8> {
    let mut out = Vec::new();
    loop {
        let mut byte = (value & 0x7f) as u8;
        value >>= 7;
        if value != 0 {
            byte |= 0x80;
        }
        out.push(byte);
        if value == 0 {
            break;
        }
    }
    out
}

/// Decode a usize from LEB128 encoding, updating the input offset.
pub fn decode_varint(input: &[u8], offset: &mut usize) -> Option<usize> {
    let mut result = 0usize;
    let mut shift = 0usize;
    while *offset < input.len() {
        let byte = input[*offset];
        *offset += 1;
        result |= ((byte & 0x7f) as usize) << shift;
        if byte & 0x80 == 0 {
            return Some(result);
        }
        shift += 7;
    }
    None
}

/// Build a file header for the given data and block size.
/// Returns the encoded header bytes.
pub fn encode_file_header(data: &[u8], block_size: usize) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&encode_varint(data.len()));
    out.extend_from_slice(&encode_varint(block_size));
    let digest: [u8; 32] = Sha256::digest(data).into();
    out.extend_from_slice(&digest);
    out
}

/// Parse a file header from the start of `input`.
/// Returns the bytes consumed, original size, block size and sha256 hash.
pub fn parse_file_header(input: &[u8]) -> Option<(usize, usize, usize, [u8; 32])> {
    let mut offset = 0usize;
    let orig_size = decode_varint(input, &mut offset)?;
    let block_size = decode_varint(input, &mut offset)?;
    if offset + 32 > input.len() {
        return None;
    }
    let mut hash = [0u8; 32];
    hash.copy_from_slice(&input[offset..offset + 32]);
    offset += 32;
    Some((offset, orig_size, block_size, hash))
}
