#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.61])
AC_INIT([python-taningia], [0.1], [http://projects.comum.org/taningia])
AC_CONFIG_SRCDIR([src])
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE(foreign)

# Checks for programs.
AC_PROG_CC
AC_PROG_LIBTOOL

# Python stuff
AM_PATH_PYTHON(2.5.0)
PY_PREFIX=`$PYTHON -c 'import sys ; print sys.prefix'`
PYTHON_LIBS="-lpython$PYTHON_VERSION"
PYTHON_CFLAGS="-I$PY_PREFIX/include/python$PYTHON_VERSION"
AC_SUBST([PYTHON])
AC_SUBST([PYTHON_LIBS])
AC_SUBST([PYTHON_CFLAGS])

# Checks for .pc packages
PKG_CHECK_MODULES([TANINGIA], [taningia])
AC_SUBST([TANINGIA_CFLAGS])
AC_SUBST([TANINGIA_LIBS])

AC_CONFIG_FILES([
    Makefile
    src/Makefile
])
AC_OUTPUT
