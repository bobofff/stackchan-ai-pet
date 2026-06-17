.PHONY: setup-brain migrate-brain-db run-brain simulate simulate-web test-brain

setup-brain:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r brain/requirements.txt

migrate-brain-db:
	. .venv/bin/activate && PYTHONPATH=brain python -m app.migrations

run-brain:
	. .venv/bin/activate && uvicorn app.main:app --app-dir brain --host 0.0.0.0 --port 8787 --reload

simulate:
	. .venv/bin/activate && python simulator/chat.py

simulate-web:
	@echo "启动 make run-brain 后访问 http://127.0.0.1:8787/simulator/"

test-brain:
	. .venv/bin/activate && python -m unittest discover -s brain/tests
