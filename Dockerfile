FROM pypy:3.10-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install --no-install-recommends -y git &&\
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* &\
    pip install uv
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

COPY . .
ENTRYPOINT ["/app/update-server.sh"]
