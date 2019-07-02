build:
	docker build -t metabolomicsusi .

bash:
	docker run -it -p 5000:5000 --rm --name metabolomicsusi metabolomicsusi bash

interactive:
	docker run -it -p 5000:5000 -v $(PWD)/temp:/temp --rm --name metabolomicsusi metabolomicsusi /app/run_server.sh

server:
	docker run -d -p 5011:5000 -v $(PWD)/temp:/temp --rm --name metabolomicsusi metabolomicsusi /app/run_server.sh
