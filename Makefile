install:
	pipenv lock && pipenv sync

installdev:
	pipenv lock && pipenv sync --dev

build:
	docker build -t catering-api .

iclean:
	docker image prune

vclean:
	docker volume prune

run:
	python manage.py runserver

docker:
	docker compose up -d database cache broker mailing

silpo_mock:
	python -m uvicorn tests.providers.silpo:app --port 8001 --reload

kfc_mock:
	python -m uvicorn tests.providers.kfc:app --port 8002 --reload

uklon_mock:
	python -m uvicorn tests.providers.uklon:app --port 8003 --reload

uber_mock:
	python -m uvicorn tests.providers.uber:app --port 8004 --reload

worker_low:
	watchmedo auto-restart --recursive --pattern='*.py' -- celery -A config worker -l INFO -Q low_priority

worker_high:
	watchmedo auto-restart --recursive --pattern='*.py' -- celery -A config worker -l INFO -Q high_priority

fix:
	python -m black .
	python -m isort .

check:
	python -m flake8 .
	python -m black --check .
	python -m isort --check .
	python -m mypy --exclude archive --exclude docs --check-untyped-defs .