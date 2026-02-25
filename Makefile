build:
	docker build -f Dockerfile -t metabolomicsusi .

clean:
	docker rm metabolomicsusi |:

development: clean
	docker run -it -p 5087:5000 --name metabolomicsusi metabolomicsusi /app/run_dev_server.sh

server: clean
	docker run -d -p 5087:5000 --name metabolomicsusi metabolomicsusi /app/run_server.sh

interactive: clean
	docker run -it -p 5087:5000 --name metabolomicsusi metabolomicsusi /app/run_server.sh

bash: clean
	docker run -it -p 5087:5000 --name metabolomicsusi metabolomicsusi bash

clear-cache:
	sudo rm tmp/joblibcache -rf



#Docker Compose
server-compose-interactive:
	docker compose --compatibility build
	docker compose --compatibility up

server-compose-autotest-interactive:
	docker compose --compatibility build
	docker compose -f docker-compose.yml -f docker-compose-autotest.yml --compatibility up

server-compose:
	docker compose --compatibility build
	docker compose --compatibility up -d

server-compose-production-interactive:
	docker compose --compatibility build
	docker compose -f docker-compose.yml -f docker-compose-production.yml --compatibility up

server-compose-production:
	docker compose --compatibility build
	docker compose -f docker-compose.yml -f docker-compose-production.yml --compatibility up -d

attach:
	docker exec -i -t metabolomicsusi-web /bin/bash

submodule_init:
	git submodule update --init --recursive