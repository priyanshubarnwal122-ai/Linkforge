.PHONY: test lint compile docker-config

test:
	python -m unittest discover -s tests -q

lint:
	python -m ruff check backend/app --select E,F,W,I --ignore E501

compile:
	python -m compileall -q backend/app tests scripts

docker-config:
	cp .env.example .env
	docker compose config --quiet
