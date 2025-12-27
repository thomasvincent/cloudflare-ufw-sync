docker-build:
	@docker build -t cloudflare-ufw-sync:dev .

docker-test: docker-build
	@docker run --rm -t --entrypoint pytest cloudflare-ufw-sync:dev -q --maxfail=1 --disable-warnings

docker-tox: docker-build
	@docker run --rm -t --entrypoint bash cloudflare-ufw-sync:dev -lc "pip install -q tox && tox -q -p auto"