PY ?= .venv/bin/python

.PHONY: setup check eval queue app dataset stability

setup:            ## create a venv inside the repo and install pinned dependencies
	python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt

check:            ## offline: tests + re-score everything from committed files (no key needed)
	$(PY) -m pytest -q tests

eval:             ## rebuild metrics, tables and the abstention curve from cached model outputs
	$(PY) scripts/evaluate.py

queue:            ## rebuild the review queue and citation scores the app replays
	$(PY) scripts/build_queue.py

app:              ## open the review queue (offline replay unless OPENROUTER_API_KEY is set)
	$(PY) -m streamlit run app/app.py

dataset:          ## rebuild data/advice_boundary_v1.csv from the committed raw generations
	$(PY) scripts/make_dataset.py

stability:        ## label stability check on the 60-item blind sample
	$(PY) labeling/stability_check.py
