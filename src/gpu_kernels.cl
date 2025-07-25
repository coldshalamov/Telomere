__constant uint k[64] = {
    0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,
    0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
    0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,
    0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
    0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,
    0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
    0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,
    0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
    0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,
    0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
    0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,
    0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
    0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,
    0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
    0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,
    0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};

uint rotr(uint x, uint n) { return (x >> n) | (x << (32 - n)); }

void sha256_simple(const __private uchar *msg, uint len, __private uchar *out) {
    uint w[64];
    for(uint i=0;i<64;i++) w[i]=0u;
    for(uint i=0;i<len;i++) {
        uint idx = i >> 2;
        w[idx] |= ((uint)msg[i]) << (24 - 8*(i & 3));
    }
    w[len>>2] |= 0x80u << (24 - 8*(len & 3));
    w[15] = len * 8u;
    for(uint i=16;i<64;i++) {
        uint s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15]>>3);
        uint s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2]>>10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint a=0x6a09e667u;
    uint b=0xbb67ae85u;
    uint c=0x3c6ef372u;
    uint d=0xa54ff53au;
    uint e=0x510e527fu;
    uint f=0x9b05688cu;
    uint g=0x1f83d9abu;
    uint h=0x5be0cd19u;
    for(uint i=0;i<64;i++) {
        uint S1 = rotr(e,6) ^ rotr(e,11) ^ rotr(e,25);
        uint ch = (e & f) ^ (~e & g);
        uint temp1 = h + S1 + ch + k[i] + w[i];
        uint S0 = rotr(a,2) ^ rotr(a,13) ^ rotr(a,22);
        uint maj = (a & b) ^ (a & c) ^ (b & c);
        uint temp2 = S0 + maj;
        h = g;
        g = f;
        f = e;
        e = d + temp1;
        d = c;
        c = b;
        b = a;
        a = temp1 + temp2;
    }
    a += 0x6a09e667u;
    b += 0xbb67ae85u;
    c += 0x3c6ef372u;
    d += 0xa54ff53au;
    e += 0x510e527fu;
    f += 0x9b05688cu;
    g += 0x1f83d9abu;
    h += 0x5be0cd19u;
    uint digest[8] = {a,b,c,d,e,f,g,h};
    for(uint i=0;i<8;i++) {
        out[i*4+0] = (uchar)((digest[i] >> 24) & 0xff);
        out[i*4+1] = (uchar)((digest[i] >> 16) & 0xff);
        out[i*4+2] = (uchar)((digest[i] >> 8) & 0xff);
        out[i*4+3] = (uchar)(digest[i] & 0xff);
    }
}

__kernel void match_seeds(__global const uchar *block_data,
                          uint block_len,
                          __global const uint *seed_idx,
                          uint seeds_per_launch,
                          __global uint2 *out_matches) {
    uint gid = get_global_id(0);
    if (gid >= seeds_per_launch) return;
    uint seed = seed_idx[gid];
    __private uchar cur[32];
    __private uchar digest[32];
    cur[0] = (uchar)(seed & 0xffu);
    uint cur_len = 1u;
    uint produced = 0u;
    uint match = 1u;
    while (produced < block_len) {
        sha256_simple(cur, cur_len, digest);
        for(uint i=0u; i<32u && produced < block_len; i++, produced++) {
            if (digest[i] != block_data[produced]) { match = 0u; break; }
        }
        if (!match) break;
        cur_len = 32u;
        for(uint i=0u; i<32u; i++) cur[i] = digest[i];
    }
    if (match == 1u) {
        out_matches[gid] = (uint2)(gid, 1u);
    } else {
        out_matches[gid] = (uint2)(0xffffffffu, 0u);
    }
}
