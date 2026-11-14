help:
	@echo "make data   - 获取笔画骨架数据 (Make Me a Hanzi)"
	@echo "make build  - 生成全部字重到 fonts/"
	@echo "make specimen - 生成字样图到 documentation/"

data:
	mkdir -p sources/data
	test -f sources/data/graphics.txt || curl -L -o sources/data/graphics.txt https://raw.githubusercontent.com/skishore/makemeahanzi/master/graphics.txt

build: data
	python3 sources/build.py

specimen:
	python3 sources/specimen.py
