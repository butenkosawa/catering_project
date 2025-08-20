set shell := ["powershell.exe", "-c"]

install:
    pipenv lock; pipenv sync

installdev:
    pipenv lock; pipenv sync --dev

run:
    python manage.py runserver
    
build:
    docker-compose build

docker:
    docker-compose up -d database cache broker mailing

silpo_mock:
    python -m uvicorn tests.providers.silpo:app --port 8001 --reload

kfc_mock:
    python -m uvicorn tests.providers.kfc:app --port 8002 --reload
    
uklon_mock:
    python -m uvicorn tests.providers.uklon:app --port 8003 --reload

clean:
    docker image prune

worker_default:
    watchmedo auto-restart --recursive --pattern='*.py' -- celery -A config worker -l INFO -Q default --pool=solo

worker_high:
    watchmedo auto-restart --recursive --pattern='*.py' -- celery -A config worker -l INFO -Q high_priority --pool=solo