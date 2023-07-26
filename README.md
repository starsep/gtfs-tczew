# gtfs-tczew

## validation:
`make validate`


## Docker
```
docker build -t gtfs-tczew .
docker run --rm \
    --env GITHUB_USERNAME=example \
    --env GITHUB_TOKEN=12345 \
    --env TZ=Europe/Warsaw \
    -t gtfs-tczew
```
