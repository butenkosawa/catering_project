set shell := ["powershell", "-c"]

install:
	pipenv lock; pipenv sync

installdev:
	pipenv lock; pipenv sync --dev

run:
    python manage.py runserver

build:
	docker build -t catering-api .

docker:
	docker run --rm -p 8000:8000 --env-file .env catering-api

iclean:
    docker image prune

vclean:
    docker volume prune

worker_low:
    celery -A config worker -l INFO -Q low_priority --pool=solo

worker_high:
    celery -A config worker -l INFO -Q high_priority --pool=solo