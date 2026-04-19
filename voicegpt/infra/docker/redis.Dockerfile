# ── VoiceGPT Redis Dockerfile ─────────────────────────────────────────────────
# Custom Redis with our config baked in.
FROM redis:7.4-alpine

COPY redis.conf /usr/local/etc/redis/redis.conf

EXPOSE 6379

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD redis-cli ping || exit 1

CMD ["redis-server", "/usr/local/etc/redis/redis.conf"]
