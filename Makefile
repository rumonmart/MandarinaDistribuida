clean:
	rm -rf /tmp/db/node1
	rm -rf /tmp/db/registry
	rm -rf /tmp/db/distribution
stop:
	sudo systemctl stop icegridregistry
	sudo systemctl stop icegridnode
1:
	mkdir -p /tmp/db/node1
	mkdir -p /tmp/db/registry
	mkdir -p /tmp/db/distribution
	cp downloader.ice /tmp/db/distribution
	cp server.py /tmp/db/distribution
	cp download_scheduler.py /tmp/db/distribution
	cp work_queue.py /tmp/db/distribution
	chmod -R 777 /tmp/db/*
	icepatch2calc /tmp/db/distribution
	icegridnode --Ice.Config=node1.config
