set shell := ["powershell", "-c"]

build:
	docker build -t catering-api .

docker:
	docker run --rm -p 8000:8000 --env-file .env catering-api