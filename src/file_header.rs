
/// Encode a usize using EVQL (Exponentially Variable Quantization Length).
///
/// The payload width is `2^N` **bits** where `N` is chosen such that
/// `value < 2^(2^N)`. The prefix is encoded as `N` consecutive one bits
/// followed by a zero stop bit. All bits are packed big endian.
pub fn encode_evql(value: usize) -> Vec<u8> {
    let mut width = 1usize; // number of bits
    let mut n = 0usize;
    while width < usize::BITS as usize && value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    let mut bits = Vec::new();
    for _ in 0..n {
        bits.push(true);
    }
    bits.push(false);
    for i in (0..width).rev() {
        bits.push(((value >> i) & 1) != 0);
    }
    pack_bits(&bits)
}

/// Decode a usize from EVQL encoding. Returns `(value, bytes_consumed)`.
pub fn decode_evql(data: &[u8]) -> Option<(usize, usize)> {
    let mut pos = 0usize;
    let mut n = 0usize;
    loop {
        match get_bit(data, pos) {
            Some(true) => {
                n += 1;
                pos += 1;
            }
            Some(false) => {
                pos += 1;
                break;
            }
            None => return None,
        }
    }
    let width = 1usize << n;
    let mut value = 0usize;
    for _ in 0..width {
        match get_bit(data, pos) {
            Some(bit) => {
                value = (value << 1) | (bit as usize);
                pos += 1;
            }
            None => return None,
        }
    }
    Some((value, (pos + 7) / 8))
}

/// Build a file header using EVQL encoded file and block sizes.
/// Returns the encoded header bytes.
pub fn encode_file_header(file_size: usize, block_size: usize) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(&encode_evql(file_size));
    out.extend_from_slice(&encode_evql(block_size));
    out
}

/// Parse an EVQL header from the start of `data`.
/// Returns `(bytes_consumed, file_size, block_size)`.
pub fn decode_file_header(data: &[u8]) -> Option<(usize, usize, usize)> {
    let (file_size, used1) = decode_evql(data)?;
    let (block_size, used2) = decode_evql(&data[used1..])?;
    Some((used1 + used2, file_size, block_size))
}

fn get_bit(input: &[u8], pos: usize) -> Option<bool> {
    if pos / 8 >= input.len() {
        None
    } else {
        Some(((input[pos / 8] >> (7 - (pos % 8))) & 1) != 0)
    }
}

fn pack_bits(bits: &[bool]) -> Vec<u8> {
    let mut out = Vec::new();
    let mut byte = 0u8;
    let mut used = 0u8;
    for &b in bits {
        byte = (byte << 1) | (b as u8);
        used += 1;
        if used == 8 {
            out.push(byte);
            byte = 0;
            used = 0;
        }
    }
    if used > 0 {
        byte <<= 8 - used;
        out.push(byte);
    }
    if out.is_empty() {
        out.push(0);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evql_roundtrip_examples() {
        let values = [0usize, 3, 4, 5, 15, 16, 255, 256, 65_535, 65_536];
        for &v in &values {
            let enc = encode_evql(v);
            let (val, used) = decode_evql(&enc).expect("decode failed");
            assert_eq!(val, v);
            assert_eq!(used, enc.len());
        }
    }
}
