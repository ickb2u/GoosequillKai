MMH = https://raw.githubusercontent.com/skishore/makemeahanzi/master
ACJK = https://raw.githubusercontent.com/parsimonhi/animCJK/master
ACJK_FILES = graphicsZhHans.txt graphicsZhHant.txt graphicsJa.txt graphicsKo.txt graphicsJaKana.txt

help:
	@echo "make data     - 获取笔画骨架数据 (Make Me a Hanzi, AnimCJK)"
	@echo "make build    - 生成全部字重到 fonts/"
	@echo "make specimen - 生成字样图到 documentation/"

data:
	mkdir -p sources/data
	test -f sources/data/graphics.txt || curl -fL -o sources/data/graphics.txt $(MMH)/graphics.txt
	for f in $(ACJK_FILES); do test -f sources/data/$$f || curl -fL -o sources/data/$$f $(ACJK)/$$f; done

build: data
	python3 sources/build.py

specimen:
	python3 sources/specimen.py
