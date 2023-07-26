FROM pypy:3.10-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install --no-install-recommends -y git &&\
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV GITHUB_USERNAME ""
ENV GITHUB_TOKEN ""
ENTRYPOINT ["/app/update-server.sh"]
