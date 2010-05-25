pyexecdir = $(pythondir)
pyexec_LTLIBRARIES = taningiamodule.la

taningiamodule.c:
	$(PYTHON) $(top_builddir)/src/main.py

taningiamodule_la_SOURCES = taningiamodule.c

AM_CPPFLAGS = \
	$(TANINGIA_CFLAGS) \
	$(PYTHON_CFLAGS)

AM_LDFLAGS = \
	-module -avoid-version \
	$(TANINGIA_LIBS) \
	$(PYTHON_LIBS)

CLEANFILES = taningiamodule.c
