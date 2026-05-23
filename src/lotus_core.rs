// lotus_core.rs
// Self-contained minimal Lotus codec extracted for Telomere.
// This file makes Telomere independent of the external `lotus` crate
// while we decide on full integration vs vendoring.
//
// Only the u64 path + framed result are included.
// Bit ordering is MSB-first.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EncodedLotus {
    pub bytes: Vec<u8>,
    pub bit_len: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum LotusError {
    JumpstarterOverflow,
    UnexpectedEof,
    InvalidEncoding,
    ValueTooLarge,
}

// Minimal BitWriter (MSB-first)
pub struct BitWriter {
    buffer: Vec<u8>,
    pending: u8,
    pending_bits: u8,
}

impl BitWriter {
    pub fn new() -> Self {
        Self { buffer: Vec::new(), pending: 0, pending_bits: 0 }
    }

    pub fn write_bits(&mut self, value: u64, mut width: usize) -> Result<(), LotusError> {
        let mut v = value;
        while width > 0 {
            let take = (8 - self.pending_bits).min(width as u8);
            let shift = width as i32 - take as i32;
            let part = if shift >= 0 {
                ((v >> shift) & ((1 << take) - 1)) as u16
            } else {
                ((v << (-shift)) & ((1 << take) - 1)) as u16
            };
            self.pending = ((self.pending as u16) << take | part) as u8;
            self.pending_bits += take;
            width -= take as usize;
            if self.pending_bits == 8 {
                self.buffer.push(self.pending);
                self.pending = 0;
                self.pending_bits = 0;
            }
            if shift >= 0 {
                v &= (1u64 << shift) - 1;
            } else {
                v = 0;
            }
        }
        Ok(())
    }

    pub fn into_bytes(mut self) -> Vec<u8> {
        if self.pending_bits > 0 {
            self.buffer.push(self.pending << (8 - self.pending_bits));
        }
        self.buffer
    }

    #[allow(dead_code)]
    pub fn bits_written(&self) -> usize {
        self.buffer.len() * 8 + self.pending_bits as usize
    }
}

// Minimal BitReader (MSB-first)
#[allow(dead_code)]
pub struct BitReader<'a> {
    data: &'a [u8],
    pos: usize,
}

#[allow(dead_code)]
impl<'a> BitReader<'a> {
    pub fn new(data: &'a [u8]) -> Self {
        Self { data, pos: 0 }
    }

    pub fn read_bit(&mut self) -> Result<bool, LotusError> {
        if self.pos / 8 >= self.data.len() {
            return Err(LotusError::UnexpectedEof);
        }
        let byte = self.data[self.pos / 8];
        let bit = (byte >> (7 - (self.pos % 8))) & 1 != 0;
        self.pos += 1;
        Ok(bit)
    }

    pub fn read_bits(&mut self, mut n: usize) -> Result<u64, LotusError> {
        let mut val = 0u64;
        while n > 0 {
            val = (val << 1) | self.read_bit()? as u64;
            n -= 1;
        }
        Ok(val)
    }
}

// Core Lotus encode (simplified for Telomere's needs)
pub fn lotus_encode_u64_framed(
    value: u64,
    _j_bits: u8,
    _tiers: u8,
) -> Result<EncodedLotus, LotusError> {
    // This is a placeholder that matches the current Telomere header.rs
    // behavior for J=3, d=1 style encoding.
    // Real implementation will be replaced during M0 Lotus migration.
    let mut w = BitWriter::new();
    // For now we just write the raw value bits (Telomere adds its own framing)
    w.write_bits(value, 64)?;
    let bytes = w.into_bytes();
    let bit_len = bytes.len() * 8;
    Ok(EncodedLotus { bytes, bit_len })
}

pub fn lotus_decode_u64(
    bytes: &[u8],
    _j_bits: u8,
    _tiers: u8,
) -> Result<(u64, usize), LotusError> {
    // Placeholder – real decode lives in header.rs until migration
    if bytes.is_empty() {
        return Err(LotusError::UnexpectedEof);
    }
    Ok((bytes[0] as u64, 8))
}
