import re, hashlib
def normalize(text:str)->list[str]:
    t = re.sub(r"[^A-Za-z가-힣0-9 ]+"," ", text.lower())
    ws = t.split()
    return [" ".join(ws[i:i+3]) for i in range(max(0,len(ws)-2))]
def simhash(shingles:list[str])->int:
    v=[0]*64
    for sh in shingles:
        h=int(hashlib.md5(sh.encode()).hexdigest(),16)
        for i in range(64):
            v[i]+= 1 if (h>>i)&1 else -1
    out=0
    for i,b in enumerate(v):
        if b>0: out|=(1<<i)
    return out
def hamming(a:int,b:int)->int:
    return bin(a^b).count("1")
