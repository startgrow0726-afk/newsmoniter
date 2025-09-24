import zlib
def url_hash(url:str)->int:
    return zlib.adler32(url.encode("utf-8"))
