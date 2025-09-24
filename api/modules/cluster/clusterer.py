from .shingling import normalize, simhash, hamming
from storage.pg import get_conn

def assign_cluster(article_id:int, title:str, summary:str, severity:str="LOW"):
    sig = simhash(normalize(f"{title} {summary}"))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, title, sig, severity FROM clusters ORDER BY last_seen DESC LIMIT 200")
        rows = cur.fetchall()
        for cid, ctitle, csig, csev in rows:
            if csig and hamming(int(csig), sig) <= 6:
                # severity는 더 높은 쪽으로 승급
                sev_rank = {"LOW":0,"MEDIUM":1,"HIGH":2}
                new_sev = csev if sev_rank[csev] >= sev_rank[severity] else severity
                cur.execute("UPDATE clusters SET last_seen=now(), article_count=article_count+1, severity=%s WHERE id=%s",
                            (new_sev, cid))
                cur.execute("INSERT INTO cluster_articles(cluster_id, article_id, rank) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                            (cid, article_id, 0))
                return cid, new_sev
        cid = f"C{article_id}"
        cur.execute("INSERT INTO clusters(id,title,severity,first_seen,last_seen,article_count,sig) VALUES (%s,%s,%s,now(),now(),1,%s)",
                    (cid, title, severity, str(sig)))
        cur.execute("INSERT INTO cluster_articles(cluster_id, article_id, rank) VALUES (%s,%s,%s)", (cid, article_id, 0))
        return cid, severity