CC      = gcc
CFLAGS  = -O2 -Wall

ntt_driver: ntt_driver.c
	$(CC) $(CFLAGS) -o $@ $< -lcma -lpthread

test: ntt_driver
	python3 run_tests.py

bench: ntt_driver
	sudo ./ntt_driver -t > /dev/null

clean:
	rm -f ntt_driver

.PHONY: test bench clean
