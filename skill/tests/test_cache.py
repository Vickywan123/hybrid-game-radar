import sys, os, json, time, tempfile, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import search_stores as ss

def test_cache_roundtrip_and_ttl():
    with tempfile.TemporaryDirectory() as d:
        ss.CACHE_DIR = d
        # miss before put
        assert ss.cache_get("apple_search", "arrow drop") is None
        # roundtrip
        ss.cache_put("apple_search", "arrow drop", [{"trackName": "Arrow Drop"}])
        got = ss.cache_get("apple_search", "arrow drop")
        assert got == [{"trackName": "Arrow Drop"}]
        # expired entry returns None (write a stale timestamp directly)
        p = os.path.join(d, "apple_search_" + hashlib.md5(b"arrow drop").hexdigest() + ".json")
        json.dump({"ts": time.time() - 2 * 86400, "data": ["stale"]}, open(p, "w"))
        assert ss.cache_get("apple_search", "arrow drop") is None
        # gp_app has a 7-day TTL: 2-day-old entry still valid
        ss.cache_put("gp_app", "com.drop.arrow", {"title": "Arrow Drop"})
        p2 = os.path.join(d, "gp_app_" + hashlib.md5(b"com.drop.arrow").hexdigest() + ".json")
        json.dump({"ts": time.time() - 2 * 86400, "data": {"title": "Arrow Drop"}}, open(p2, "w"))
        assert ss.cache_get("gp_app", "com.drop.arrow") == {"title": "Arrow Drop"}
    print("test_cache_roundtrip_and_ttl OK")

test_cache_roundtrip_and_ttl()
