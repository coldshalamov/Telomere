# Net-size FLOOR vs arity, with INFINITE search (a match found for every bundle).
# An arity-A bundle replaces a wrapped run (A*content + A*marker) with one record
# (content_index ~ A*content bits + framing). So per bundle it claws back A markers
# but pays framing ONCE -> bigger A amortizes framing over more blocks.
B=3; RAW=B*8; MARKER=3
def framing(A, content):
    p=content; w=max(1,p.bit_length()); ab=max(3, A.bit_length()+1)  # arity code grows w/ A
    return ab+3+w
print("FLOOR of net file size vs ARITY (infinite search), 3-byte blocks, 3-bit marker:")
print(f"{'arity':>6} | {'floor % of raw':>14} | {'seeds needed':>14}")
for A in (1,2,5,10,50,100,1000):
    content=A*RAW
    fr=framing(A,content)
    floor=100*(1 + fr/content)     # record=content+framing vs raw content
    print(f"{A:>6} | {floor:>13.3f}% | {'2^'+str(content):>14}")
print("\n--> arity DOES lower the floor toward 100% (your arity intuition, confirmed).")
print("    It asymptotes to 100% from ABOVE and never crosses, for two reasons:")
print("      1. naming A*24 random bits costs >= A*24 bits, so record >= raw content always;")
print("      2. to beat RAW you'd need headroom > framing, P = 2^-framing per span --")
print("         SAME at every arity (the variability columns were span-invariant).")
print("    And reaching arity-A needs 2^(A*24) seeds: 2^2400 at A=100. Theoretical, not runnable.")
