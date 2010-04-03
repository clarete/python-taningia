#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# Copyright (C) 2010  Lincoln de Sousa <lincoln@comum.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import sys
from scanner import scan_files, purge_lib_prefix, purge_type_sufix
from pybindgen import FileCodeSink, Module, retval, param, cppclass

def underscore_to_camel(name):
    nname = ''
    nsize = len(name)
    i = 0
    while i < nsize:
        if name[i] == '_':
            i += 1
            nname += name[i].upper()
        else:
            if i == 0:
                nname += name[i].upper()
            else:
                nname += name[i]
        i += 1
    return nname

def main():
    modules = scan_files(sys.argv[1:])
    for m in modules:
        module = modules[m]
        print "Processing module `%s'" % m

        mod = Module(m)
        mod.add_include('<taningia/log.h>')

        for enum in module['enums']:
            print " - enum `%s'" % enum['name']
            mod.add_enum(enum['name'], enum['entries'])

        for ctype in module['types']:
            ktype = module['types'][ctype]

            # Preparing the custom name of our class. All pedantic C
            # namespace and type conventions are being purged and
            # underscore style is replaced by camelcase style.
            custom_name = purge_lib_prefix(ktype['cname'])
            custom_name = purge_type_sufix(custom_name)
            custom_name = underscore_to_camel(custom_name)

            print " - class `%s'" % custom_name

            # Preparing vars to receive constructor, destructor and
            # other ordinary methods of our class.
            constructor = None
            destructor = None
            methods = []

            # Separating constructor, destructor and other ordinary
            # methods.
            for method in ktype['methods']:
                print "  * method `%s'" % method['name']['name']
                cname = '%(class)s_%(name)s' % method['name']
                method['cname'] = cname

                if method['type']['name'] == 'constructor':
                    constructor = method
                elif method['type']['name'] == 'destructor':
                    destructor = cppclass.FreeFunctionPolicy(cname)
                else:
                    if method['name']['name'] == 'set_handler':
                        continue
                    methods.append(method)

            # Time to create our class!
            klass = mod.add_class(
                ktype['cname'],
                memory_policy=destructor,
                custom_name=custom_name)

            # And set its constructor.
            klass.add_function_as_constructor(
                constructor['cname'],
                retval(constructor['rtype']),
                [param(x['type'], x['name']) for x in constructor['params']])

            for i in methods:
                params = []
                for index, item in enumerate(i['params']):
                    if item['type'] == 'varargs':
                        continue
                    if index != 0:
                        params.append(param(item['type'], item['name']))
                    else:
                        params.append(param(item['type'], item['name'],
                                            transfer_ownership=False))

                print i
                klass.add_function_as_method(
                    i['cname'], retval(i['rtype']), params,
                    custom_name=i['name']['name'])

        mod.generate(FileCodeSink(open('logmodule.c', 'w')))

def gen(output):
    mod = Module('log')
    mod.add_include('<taningia/log.h>')

    destructor = cppclass.FreeFunctionPolicy('ta_log_free')
    log = mod.add_class('ta_log_t', memory_policy=destructor,
                        custom_name='Log')
    log.add_function_as_constructor('ta_log_new',
                                    retval('ta_log_t*',
                                           caller_owns_return=True),
                                    [param('const char*', 'domain_name')])

    log.add_function_as_method('ta_log_info', None,
                               [param('ta_log_t*', 'log', transfer_ownership=False),
                                param('const char *', 'fmt')],
                               custom_name='info')

    mod.generate(FileCodeSink(output))

if __name__ == '__main__':
    main()
