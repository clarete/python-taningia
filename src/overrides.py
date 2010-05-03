# -*- coding: utf-8; -*-
#
# Copyright (C) 2009, 2010  Lincoln de Sousa <lincoln@comum.org>
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

ta_xmpp_client_event_connect = '''
struct py_hook_data {
  PyObject *callback;
  PyObject *data;
};

static int
_call_py_xmpp_client_event_connect (ta_xmpp_client_t *PYBINDGEN_UNUSED(client),
                                    void *PYBINDGEN_UNUSED(data1), void *data2)
{
    PyObject *result, *args;
    struct py_hook_data *hdata = (struct py_hook_data *) data2;
    PyGILState_STATE threadstate;

    threadstate = PyGILState_Ensure ();
    args = Py_BuildValue ("(O)", hdata->data);
    result = PyObject_CallObject (hdata->callback, args);

    /* Time to free stuff */
    Py_DECREF (args);
    if (result == NULL)
        PyErr_Print ();
    else
        Py_DECREF (result);
    free (hdata);

    PyGILState_Release (threadstate);
    return 0;
}

static PyObject *
_wrap_ta_xmpp_client_event_connect(PyTa_xmpp_client_t *self,
                                   PyObject *args,
                                   PyObject *kwargs,
                                   PyObject **return_exception)

{
    PyObject *py_retval;
    int retval;
    const char *event = NULL;
    const char *keywords[] = {"event", "callback", "user_data", NULL};
    PyObject *callback = NULL;
    PyObject *user_data = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "sO|O", (char **)keywords,
                                     &event, &callback, &user_data)) {
        PyObject *exc_type, *traceback;
        PyErr_Fetch(&exc_type, return_exception, &traceback);
        Py_XDECREF(exc_type);
        Py_XDECREF(traceback);
        return NULL;
    }
    if (!PyCallable_Check (callback)) {
        PyErr_SetString (PyExc_TypeError, "Param 2 must be callable.");
        return NULL;
    } else {
        PyObject *data = NULL;
        struct py_hook_data *hook_data;
        if (user_data)
            data = user_data;
        else
            data = Py_None;

        hook_data = malloc (sizeof (struct py_hook_data));

        Py_INCREF (callback);
        hook_data->callback = callback;

        Py_INCREF (data);
        hook_data->data = data;
        retval = ta_xmpp_client_event_connect (self->obj, event,
                                               _call_py_xmpp_client_event_connect,
                                               hook_data);

        py_retval = Py_BuildValue((char *) "i", retval);
        return py_retval;
    }
}
'''

ta_xmpp_client_send_and_filter = '''
static void
_call_py_xmpp_client_send_and_filter (ta_xmpp_client_t *PYBINDGEN_UNUSED(client),
                                      iks *stanza,
                                      void *data)
{
    PyObject *result, *args;
    PyIks *pystanza;
    struct py_hook_data *hdata = (struct py_hook_data *) data;
    PyGILState_STATE threadstate;

    threadstate = PyGILState_Ensure ();
    pystanza = PyObject_New(PyIks, &PyIks_Type);
    pystanza->obj = stanza;
    pystanza->flags = PYBINDGEN_WRAPPER_FLAG_OBJECT_NOT_OWNED;
    args = Py_BuildValue ("(OO)", hdata->data, stanza);
    result = PyObject_CallObject (hdata->callback, args);

    /* Time to free stuff */
    Py_DECREF (args);
    if (result == NULL)
        PyErr_Print ();
    else
        Py_DECREF (result);
    free (hdata);

    PyGILState_Release (threadstate);
}

static PyObject *
_wrap_ta_xmpp_client_send_and_filter(PyTa_xmpp_client_t *self,
                                     PyObject *args,
                                     PyObject *kwargs,
                                     PyObject **return_exception)

{
    PyObject *py_retval;
    PyObject *stanza;
    int retval;
    const char *keywords[] = {"stanza", "callback", "user_data", NULL};
    PyObject *callback = NULL;
    PyObject *user_data = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO|O", (char **)keywords,
                                     &stanza, &callback, &user_data)) {
        PyObject *exc_type, *traceback;
        PyErr_Fetch(&exc_type, return_exception, &traceback);
        Py_XDECREF(exc_type);
        Py_XDECREF(traceback);
        return NULL;
    }
    if (0) {
        PyErr_SetString (PyExc_TypeError, "Param 1 must be an Iks instance");
        return NULL;
    }
    if (!PyCallable_Check (callback)) {
        PyErr_SetString (PyExc_TypeError, "Param 2 must be callable.");
        return NULL;
    } else {
        PyObject *data = NULL;
        struct py_hook_data *hook_data;
        if (user_data)
            data = user_data;
        else
            data = Py_None;

        hook_data = malloc (sizeof (struct py_hook_data));

        Py_INCREF (callback);
        hook_data->callback = callback;

        Py_INCREF (data);
        hook_data->data = data;
        retval = ta_xmpp_client_send_and_filter (self->obj,
                     ((PyIks *) stanza)->obj,
                     _call_py_xmpp_client_send_and_filter,
                     hook_data, NULL);

        py_retval = Py_BuildValue((char *) "i", retval);
        return py_retval;
    }
}'''

OVERRIDES = {
    'ta_xmpp_client_event_connect': ta_xmpp_client_event_connect,
    'ta_xmpp_client_send_and_filter': ta_xmpp_client_send_and_filter,
}
