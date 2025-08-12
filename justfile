set shell := ["powershell", "-c"]

install:
	pipenv lock; pipenv sync

installdev:
	pipenv lock; pipenv sync --dev

build:
	docker build -t catering-api .

docker:
	docker run --rm -p 8000:8000 --env-file .env catering-api

iclean:
    docker image prune

vclean:
    docker volume prune