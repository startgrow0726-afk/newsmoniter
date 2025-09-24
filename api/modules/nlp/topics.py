import re
MAP = {
 "반도체": r"\b(GPU|HBM|foundry|TSMC|ASML|NPU|lithography|HBM3E|CoWoS)\b",
 "클라우드·AI": r"\b(datacenter|inference|LLM|cloud|SaaS|hyperscaler)\b",
 "EV·배터리": r"\b(EV|battery|4680|solid-state|autonomous)\b"
}
def tag_topics(text:str)->list[str]:
    out=[]
    for k,pat in MAP.items():
        if re.search(pat, text, flags=re.I): out.append(k)
    return out[:3]
