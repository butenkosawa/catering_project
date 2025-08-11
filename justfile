set shell := ["powershell.exe", "-c"]

build:
    docker build -t catering-api

docker:
    docker run --rm -p 8000:8000 catering-api

clean:
    docker image prune