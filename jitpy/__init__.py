
import py
import cffi
import os

ptr = None

def setup(pypy_home):
    ffi = cffi.FFI()
    ffi.cdef("""
    void rpython_startup_code(void);

    long pypy_setup_home(char* home, int verbose);

    int pypy_execute_source(char* source);

    int pypy_execute_source_ptr(char* source, void* ptr);

    """)
    pypy_home = os.path.abspath(pypy_home)

    lib = ffi.verify("""
    #include <include/PyPy.h>
    """, libraries=["pypy-c"], include_dirs=[pypy_home, os.path.dirname(pypy_home)],
        library_dirs=[pypy_home],
        extra_link_args=['-Wl,-rpath,%s' % pypy_home])
    curdir = os.path.dirname(os.path.abspath(__file__))
    defs = os.path.join(curdir, 'pypy.defs')
    ffi.cdef(open(defs).read())
    lib.rpython_startup_code()
    res = lib.pypy_setup_home(os.path.join(pypy_home, 'bin'), 1)
    pypy_side = os.path.join(curdir, 'pypy_side.py')
    if res == 1:
        raise Exception("cannot init pypy")
    ptr = ffi.new("struct pypy_defs*")
    res = lib.pypy_execute_source_ptr(str(py.code.Source("""
    import sys, traceback
    try:
        import os
        cur_dir = '%s'
        execfile('%s')
    except Exception, e:
        traceback.print_tb(sys.exc_info()[2])
        print "%%s:%%s" %% (e.__class__.__name__, e)
        raise
    """ % (curdir, pypy_side))), ptr)
    if res:
        raise Exception("error running pypy side")

    ffi2 = cffi.FFI()
    ffi2.cdef("""
    typedef struct {
       ...;
    } PyObject;

    typedef struct {
       char kind;
       char type;
       int type_num;
       ...;
    } PyArray_Descr;
    
    typedef struct {
       char *data;
       int nd;
       intptr_t *dimensions;
       intptr_t *strides;
       PyObject *base;
       PyArray_Descr *descr;
       int flags;
       PyObject *weakreflist;
       ...;
    } PyArrayObject_fields;
    """)
    lib = ffi2.verify("""
    #include <Python.h>
    #define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
    #include <numpy/arrayobject.h>
    """)
    ptr.setup_numpy_data(ffi2.new("int[6]", [
        ffi2.offsetof("PyArrayObject_fields", "data"),
        ffi2.offsetof("PyArrayObject_fields", "strides"),
        ffi2.offsetof("PyArrayObject_fields", "dimensions"),
        ffi2.offsetof("PyArrayObject_fields", "nd"),
        ffi2.offsetof("PyArrayObject_fields", "descr"),
        ffi2.offsetof("PyArray_Descr", "type_num"),
    ]))

    globals()['ffi'] = ffi
    globals()['ptr'] = ptr

def extra_source(source):
    if not ptr:
        raise Exception("jitpy not initialized, call jitpy.setup(pypy_home)")
    ptr.extra_source(source)
