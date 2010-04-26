FLAGS=-Wall -Wextra -g -O0
FLAGS+=$(shell pkg-config --cflags taningia)
FLAGS+=$(shell python-config --cflags)

LIBS=$(shell pkg-config --libs taningia)
LIBS+=$(shell python-config --libs)

all:
	/usr/bin/python main.py #1> /dev/null
	gcc $(FLAGS) -c taningiamodule.c
	gcc $(LIBS) -shared -o taningiamodule.so taningiamodule.o

clean:
	rm -rf *~ *.pyc *.so *.o taningiamodule.c
