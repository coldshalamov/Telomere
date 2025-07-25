__constant uint k[64] = {
 0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
 0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
 0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
 0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
 0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
 0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

inline uint rotr(uint x, uint n) {
    return rotate(x, (int)(32 - n));
}

void sha256_pad(const __global uchar *input, uint len, uint *w) {
    for(int i=0;i<16;i++) w[i]=0;
    for(uint i=0;i<len;i++) {
        w[i>>2] |= (uint)input[i] << (24 - ((i & 3) << 3));
    }
    w[len>>2] |= 0x80u << (24 - ((len & 3) << 3));
    w[15] = len * 8;
}

void sha256_digest(const __global uchar *input, uint len, __global uchar *out) {
    uint w[64];
    sha256_pad(input, len, w);
    for(int i=16;i<64;i++) {
        uint s0 = rotr(w[i-15],7) ^ rotr(w[i-15],18) ^ (w[i-15]>>3);
        uint s1 = rotr(w[i-2],17) ^ rotr(w[i-2],19) ^ (w[i-2]>>10);
        w[i] = w[i-16] + s0 + w[i-7] + s1;
    }
    uint a=0x6a09e667,b=0xbb67ae85,c=0x3c6ef372,d=0xa54ff53a;
    uint e=0x510e527f,f=0x9b05688c,g=0x1f83d9ab,h=0x5be0cd19;
    for(int i=0;i<64;i++) {
        uint S1 = rotr(e,6)^rotr(e,11)^rotr(e,25);
        uint ch = (e & f) ^ (~e & g);
        uint temp1 = h + S1 + ch + k[i] + w[i];
        uint S0 = rotr(a,2)^rotr(a,13)^rotr(a,22);
        uint maj = (a & b) ^ (a & c) ^ (b & c);
        uint temp2 = S0 + maj;
        h=g; g=f; f=e; e=d+temp1; d=c; c=b; b=a; a=temp1+temp2;
    }
    uint dig[8]={
        0x6a09e667+a,0xbb67ae85+b,0x3c6ef372+c,0xa54ff53a+d,
        0x510e527f+e,0x9b05688c+f,0x1f83d9ab+g,0x5be0cd19+h};
    for(int i=0;i<8;i++) {
        out[i*4+0]=(dig[i]>>24)&0xff;
        out[i*4+1]=(dig[i]>>16)&0xff;
        out[i*4+2]=(dig[i]>>8)&0xff;
        out[i*4+3]=(dig[i])&0xff;
    }
}

kernel void seed_match(
    global const uchar *block_data,
    global const uint *block_offsets,
    global const uint *block_lens,
    uint block_count,
    ulong start_seed,
    uint max_seed_len,
    global uint2 *out_records,
    global uint *out_count
) {
    ulong gid = get_global_id(0);
    ulong seed_index = start_seed + gid;
    uchar seed[8];
    ulong idx=seed_index;
    for(uint i=0;i<max_seed_len;i++){
        seed[i]= (uchar)(idx & 0xff);
        idx >>=8;
    }
    uint buf_max=0;
    for(uint i=0;i<block_count;i++){
        if(block_lens[i]>buf_max) buf_max=block_lens[i];
    }
    __local uchar lbuf[512];
    // expand seed
    uint produced=0;
    uchar cur[32];
    for(uint i=0;i<max_seed_len;i++) cur[i]=seed[i];
    uint cur_len=max_seed_len;
    while(produced<buf_max){
        sha256_digest(cur,cur_len,lbuf+produced);
        for(int j=0;j<32;j++) cur[j]=lbuf[produced+j];
        cur_len=32;
        produced+=32;
    }
    for(uint blk=0; blk<block_count; blk++){
        uint len=block_lens[blk];
        const global uchar *block=&block_data[block_offsets[blk]];
        int match=1;
        for(uint j=0;j<len;j++){
            if(lbuf[j]!=block[j]){ match=0; break; }
        }
        if(match){
            uint pos=atomic_inc(out_count);
            out_records[pos]=(uint2)(seed_index,(uint)blk);
        }
    }
}

