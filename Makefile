.PHONY: all run validate
all: run validate

run:
	python main.py

validate: gtfs-validator-cli.jar
	java -jar gtfs-validator-cli.jar -i output/gtfs-tczew.zip -o validation

gtfs-validator-cli.jar:
	# Hardcoded version.
	wget https://github.com/MobilityData/gtfs-validator/releases/download/v4.1.0/gtfs-validator-4.1.0-cli.jar -O gtfs-validator-cli.jar

