//! Batch header encoding using EVQL bit packing as defined in the project specification.
//!
//! A header begins with a small fixed layout describing the batch
//! metadata followed by a sequence of span descriptors. Each span
//! stores an arity and seed index. All fields are packed bitwise using
//! a simple `BitWriter` so no alignment padding is inserted.
//!
//! Layout (from most significant bit to least):
//!
//! ```text
//! version:2 | block_size:4 | hash_len:10 | EVQL(block_count)
//! [ per span: arity bits | EVQL(seed_index) ]*
//! ```
//!
//! Arity encoding uses the July 2025 scheme:
//! - `0`                => arity 1
//! - `10`               => arity 2 / literal marker
//! - `EVQL(n)` (n>=3)   => arity n
//!
//! All helper routines return the number of bits consumed so callers can
//! advance the byte stream if additional data follows.

use thiserror::Error;

/// Span descriptor consisting of a block count (arity) and seed index.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Span {
    pub arity: usize,
    pub seed_index: usize,
}

/// Header metadata and associated spans.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Header {
    pub version: u8,
    pub block_size: u8,
    pub hash_len: u16,
    pub spans: Vec<Span>,
}

#[derive(Debug, Error, PartialEq, Eq)]
pub enum TelomereError {
    #[error("unexpected end of input")]
    UnexpectedEof,
}

/// Alias maintained for backwards compatibility with older code. All
/// header routines now use [`TelomereError`].
pub type HeaderError = TelomereError;

/// Encode a batch header as described in §3 of the July 2025 Telomere
/// specification.
///
/// The bitstream layout is:
/// `version:2 | block_size:4 | hash_len:10 | EVQL(span_count)` followed by
/// one or more span descriptors.  Each span descriptor encodes the arity using
/// the `0`/`10`/`EVQL` scheme and then the `seed_index` as an EVQL value.
///
/// Returns a `Vec<u8>` containing the packed big‑endian bits.
pub fn encode_header(header: &Header) -> Vec<u8> {
    let mut bw = BitWriter::new();
    bw.write_bits(header.version as u64, 2);
    bw.write_bits(header.block_size as u64, 4);
    bw.write_bits(header.hash_len as u64, 10);
    write_evql(&mut bw, header.spans.len());
    for span in &header.spans {
        match span.arity {
            1 => bw.write_bit(false),
            2 => {
                bw.write_bit(true);
                bw.write_bit(false);
            }
            n => write_evql(&mut bw, n),
        }
        write_evql(&mut bw, span.seed_index);
    }
    bw.finish()
}

/// Decode a batch header previously written by [`encode_header`].
///
/// Returns the reconstructed [`Header`] along with the number of bits
/// consumed from the input.  `TelomereError::UnexpectedEof` is
/// returned if the input ends prematurely.
pub fn decode_header(data: &[u8]) -> Result<(Header, usize), TelomereError> {
    let mut br = BitReader::new(data);
    let version = br.read_bits(2)? as u8;
    let block_size = br.read_bits(4)? as u8;
    let hash_len = br.read_bits(10)? as u16;
    let span_count = read_evql(&mut br)?;
    let mut spans = Vec::with_capacity(span_count);
    for _ in 0..span_count {
        let first = br.read_bit()?;
        let arity = if !first {
            1
        } else if !br.read_bit()? {
            2
        } else {
            read_evql(&mut br)?
        };
        let seed = read_evql(&mut br)?;
        spans.push(Span { arity, seed_index: seed });
    }
    let used = br.bits_read();
    Ok((Header { version, block_size, hash_len, spans }, used))
}

// --------------------------------------------------------------------------
// bitstream helpers

struct BitWriter {
    out: Vec<u8>,
    cur: u8,
    used: u8,
}

impl BitWriter {
    fn new() -> Self {
        Self { out: Vec::new(), cur: 0, used: 0 }
    }

    fn write_bit(&mut self, bit: bool) {
        self.cur = (self.cur << 1) | bit as u8;
        self.used += 1;
        if self.used == 8 {
            self.out.push(self.cur);
            self.cur = 0;
            self.used = 0;
        }
    }

    fn write_bits(&mut self, val: u64, bits: usize) {
        for i in (0..bits).rev() {
            self.write_bit(((val >> i) & 1) != 0);
        }
    }

    fn finish(mut self) -> Vec<u8> {
        if self.used > 0 {
            self.cur <<= 8 - self.used;
            self.out.push(self.cur);
        }
        if self.out.is_empty() {
            self.out.push(0);
        }
        self.out
    }
}

struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

impl<'a> BitReader<'a> {
    fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    fn read_bit(&mut self) -> Result<bool, TelomereError> {
        if self.pos / 8 >= self.data.len() {
            return Err(TelomereError::UnexpectedEof);
        }
        let bit = ((self.data[self.pos / 8] >> (7 - (self.pos % 8))) & 1) != 0;
        self.pos += 1;
        Ok(bit)
    }

    fn read_bits(&mut self, bits: usize) -> Result<u64, TelomereError> {
        let mut v = 0u64;
        for _ in 0..bits {
            v = (v << 1) | self.read_bit()? as u64;
        }
        Ok(v)
    }

    fn bits_read(&self) -> usize {
        self.pos
    }
}

fn write_evql(w: &mut BitWriter, mut value: usize) {
    let mut width = 1usize;
    let mut n = 0usize;
    while value >= (1usize << width) {
        width <<= 1;
        n += 1;
    }
    for _ in 0..n {
        w.write_bit(true);
    }
    w.write_bit(false);
    for i in (0..width).rev() {
        w.write_bit(((value >> i) & 1) != 0);
    }
}

fn read_evql(r: &mut BitReader) -> Result<usize, TelomereError> {
    let mut n = 0usize;
    loop {
        match r.read_bit()? {
            true => n += 1,
            false => break,
        }
    }
    let width = 1usize << n;
    let mut value = 0usize;
    for _ in 0..width {
        value = (value << 1) | r.read_bit()? as usize;
    }
    Ok(value)
}

// --------------------------------------------------------------------------
// Tests

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_known_stream() -> Result<(), TelomereError> {
        let header = Header {
            version: 1,
            block_size: 4,
            hash_len: 12,
            spans: vec![
                Span { arity: 1, seed_index: 3 },
                Span { arity: 2, seed_index: 1 },
                Span { arity: 5, seed_index: 2 },
            ],
        };
        let enc = encode_header(&header);
        let (dec, used) = decode_header(&enc)?;
        assert_eq!(dec, header);
        assert!(used <= enc.len() * 8);
        Ok(())
    }

    #[test]
    fn literal_marker_bits() {
        let header = Header {
            version: 0,
            block_size: 2,
            hash_len: 10,
            spans: vec![Span { arity: 2, seed_index: 0 }],
        };
        let enc = encode_header(&header);
        // expected prefix length: 2 + 4 + 10 + EVQL(1) = 18 bits
        let bits: Vec<char> = enc
            .iter()
            .flat_map(|b| (0..8).rev().map(move |i| if (b >> i) & 1 == 1 { '1' } else { '0' }))
            .collect();
        let prefix = 18usize;
        assert_eq!(&bits[prefix..prefix + 2], ['1', '0']);
    }
}
