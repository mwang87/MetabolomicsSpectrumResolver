build:
	docker build -t flasktemplate .

bash:
	docker run -it -p 5000:5000 --rm --name flasktemplate flasktemplate bash

interactive:
	docker run -it -p 5000:5000 -v $(PWD)/temp:/temp --rm --name flasktemplate flasktemplate /app/run_server.sh

server:
	docker run -it -p 5011:5000 --rm --name flasktemplate flasktemplate /app/run_server.sh
