import redis
import os
import time
import sys
import ssl
from urllib.parse import urlparse, urlunparse

def flush_redis():
    # workers/celery_app.py와 동일하게 REDIS_URL 환경 변수 사용
    raw_redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    print(f"[FlushScript] Raw Redis URL: {raw_redis_url}")

    # Remove query parameters (like ssl_cert_reqs=CERT_NONE) to avoid parsing errors
    parsed = urlparse(raw_redis_url)
    clean_url = urlunparse(parsed._replace(query=""))
    print(f"[FlushScript] Clean Redis URL: {clean_url}")

    # Fix for "Invalid SSL Certificate Requirements Flag: CERT_NONE" error
    # If using rediss:// (SSL) and Upstash, we might need to explicitly set ssl_cert_reqs
    connection_kwargs = {}
    if clean_url.startswith("rediss://"):
        connection_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE

    max_retries = 5
    for i in range(max_retries):
        try:
            # Pass ssl_cert_reqs explicitly to handle Upstash URLs correctly
            r = redis.from_url(clean_url, **connection_kwargs)
            # Check connection
            r.ping()
            # Flush all keys (Stale tasks 제거)
            r.flushall()
            print("[FlushScript] Successfully flushed Redis (removed all keys).")
            return
        except Exception as e:
            print(f"[FlushScript] Connection failed ({i+1}/{max_retries}): {e}")
            if i < max_retries - 1:
                print("[FlushScript] Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("[FlushScript] Max retries reached. Proceeding to start worker anyway.")
                sys.exit(0) 

if __name__ == "__main__":
    flush_redis()
