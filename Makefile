init:
	pip install -r requirements.txt

test:
	nosetests tests --with-coverage --cover-package llspy
