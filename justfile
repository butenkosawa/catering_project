set shell := ["powershell.exe", "-c"]

install:
    pipenv lock; pipenv sync

installdev:
    pipenv lock; pipenv sync --dev

run:
    python manage.py runserver
    
build:
    docker build -t catering-api

docker:
    docker run --rm -p 8000:8000 catering-api

clean:
    docker image prune

worker_default:
    celery -A config worker -l INFO -Q default --pool=solo

worker_high:
    celery -A config worker -l INFO -Q high_priority --pool=solo