

Dynamic profiling for Python, including C extensions.

## Motivation

There are a [number](https://github.com/joerick/pyinstrument) [of](https://github.com/bdarnell/plop) [sampling](https://github.com/vmprof/vmprof-python) [profiler](https://github.com/nylas/nylas-perftools) [implementations](https://github.com/what-studio/profiling) available for Python, and it's very easy to roll your own if you don't like any of them. The most common strategy is to sample the Python call stack from within the interpreter. This approach has two limitations:

* Calls into C extension code are largely invisible
* Live profiling of long-running server applications requires some modicum of support in application code.

On the other hand, tools like Linux `perf` can be used to great effect for ad-hoc profiling of native binaries. But using `perf` to profile a Python application will only give you C call stacks in the interpreter, and little insight into what your _Python_ code is doing.[1]
This toolkit bridges that gap by providing support for ad-hoc, low overhead profiling of unmodified Python applications, combining native and Python call stacks.


## Prereqs

This'll only work with CPython on Linux. You'll need a fairly recent kernel with debuginfo enabled.

1. Get kernel debug symbols ([instructions](https://wiki.ubuntu.com/Kernel/Systemtap#Where_to_get_debug_symbols_for_kernel_X.3F) for Ubuntu)

2. Install SystemTap. I recommend just building the latest version from source.
    ```
    sudo apt-get install gcc g++ textinfo libdw-dev linux-headers-`uname -r`
    git clone git://sourceware.org/git/systemtap.git
    cd systemtap
    ./configure && make && sudo make install
    ```

3. You'll need to run a CPython binary that has debugging symbols in it. Many distributions ship one; `apt-get install python-dbg` will give you a `python-dbg` binary on Debian or Ubuntu.[2]
    If your program relies on any C extension modules, you'll need to rebuild those against the new binary. If you're using `virtualenv`, this is straightforward:
    ```
    virtualenv -p /usr/bin/python-dbg venv
    . venv/bin/activate
    # install your project's dependencies.
    ```


## CPU tracing

To profile a running process $PID for 60 seconds, run

```
scripts/sample -x $PID -t 60 | tee prof-$PID.txt
```

You may see warning output like
```
WARNING: Missing unwind data for a module, rerun with 'stap -d /lib/x86_64-linux-gnu/libpthread-2.23.so'
```

resulting in missing stack information because SystemTap can't resolve symbols.
To fix this, rerun passing the additional library paths, e.g.,
```
scripts/sample -x $PID -t 60 -d /lib/x86_64-linux-gnu/libpthread-2.23.so -d /lib/x86_64-linux-gnu/libc-2.23.so
```

The output data can be visualized with [FlameGraph](https://github.com/brendangregg/FlameGraph):

```
flamegraph.pl prof-$PID.txt > prof-$PID.svg
```


---
[1] Note that we're only talking about CPython here. JITted runtimes are totally their own story.

[2] The "debug" Python binary is built with `--with-pydebug`, which also builds the interpreter with `-O0`, and enables the debug memory allocator. Those changes can negatively affect application performance, when all we really need here is a binary with DWARF debugging symbols in it. If this is a factor, consider building your own Python binary instead. E.g.
```
export $VER=2.7.11
wget https://www.python.org/ftp/python/$VER/Python-$VER.tar.xz
tar -xvJf Python-$VER.tar.xz
cd Python-$VER
./configure CFLAGS='-g -fno-omit-frame-pointer' --prefix=/opt/python-$VER-dbg
make
sudo make install
```
