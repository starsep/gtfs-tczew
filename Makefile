.PHONY: all run validate
all: run validate

run:
	python main.py

validate: gtfs-validator-cli.jar
	java -jar gtfs-validator-cli.jar -i output/gtfs-tczew.zip -o validation

gtfs-validator-cli.jar:
	# Hardcoded version, it will fail with next release
	wget https://github.com/MobilityData/gtfs-validator/releases/latest/download/gtfs-validator-4.0.0-cli.jar -O gtfs-validator-cli.jar

