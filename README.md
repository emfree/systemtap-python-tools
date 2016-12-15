
Do you need to profile a Python program that spends a lot of its time in C extension code? Debug a memory leak? Or understand a particular codepath in an unfamiliar codebase?

[SystemTap](https://sourceware.org/systemtap/) is a powerful and flexible Linux tracing tool. It can be used to great effect to solve these problems and more. However, some leg work is required. Here are a few utilities to help trace Python programs.

(I gave a talk about this at PyBay 2016, discussing some of the background, motivation, and implementation in depth. [Slides here](https://speakerdeck.com/emfree/python-tracing-superpowers-with-systems-tools))

# Getting started

This will only work with CPython on Linux. Python 2 and 3 are both supported.

1. Install SystemTap. I recommend just building the latest version from source.
    ```
    sudo apt-get install -y gcc g++ gettext libdw-dev linux-headers-`uname -r`
    git clone git://sourceware.org/git/systemtap.git
    cd systemtap
    ./configure && make && sudo make install
    ```

2. You'll need to run a CPython binary that contains debugging symbols. Many distributions ship one; `apt-get install python-dbg` will give you a `python-dbg` binary on Debian or Ubuntu.[1]
    If your program relies on any C extension modules, you'll need to rebuild those against the new binary. If you're using `virtualenv`, this is straightforward:
    ```
    virtualenv -p /usr/bin/python-dbg venv
    . venv/bin/activate
    # install your project's dependencies.
    ```

3. For profiling support, clone [https://github.com/brendangregg/FlameGraph](https://github.com/brendangregg/FlameGraph) and add it to your `$PATH`.


In general, SystemTap scripts need to be run as root.


# Careful!
Tracing overhead can vary dramatically! SystemTap bugs could crash your system! Test in a safe environment before you use any of this in production!


# Examples


## CPU profiling

![A flamegraph showing user, interpreter and kernel stacks.](/static/flamegraph_expanded.png)
-- An example flame graph combining Python, interpreter, and kernel call stacks.


### Basic Usage

To profile a running process $PID for 60 seconds, run

```
scripts/sample -x $PID -t 60 | flamegraph.pl --colors=java > profile.svg
```

If you're using Python 3, pass `--py3`:

```
scripts/sample --py3 -x $PID -t 60 | flamegraph.pl --colors=java > profile.svg
```

### Rationale

There are a [number](https://github.com/joerick/pyinstrument) [of](https://github.com/bdarnell/plop) [sampling](https://github.com/vmprof/vmprof-python) [profiler](https://github.com/nylas/nylas-perftools) [implementations](https://github.com/what-studio/profiling) available for Python, and it's easy to roll your own if you don't like any of them. The most common strategy is to sample the Python call stack from within the interpreter. But this approach has two limitations:

* Calls into C extension code are largely invisible
* You'll need to integrate the profiler into your application code.

In contrast, tools like Linux `perf` can profile unmodified native binaries. But using `perf` on a Python program will only give you C call stacks in the interpreter, and little insight into what your _Python_ code is doing.

With SystemTap, we can get something of the best of both worlds. We don't need to change any application code, and the resultant profile transparently combines native and Python callstacks.


## Memory allocation tracing

Run
```
scripts/memtrace -x $PID -t 60
```
to trace all Python object memory allocations for 60 seconds. At the end, for all surviving objects, the allocation timestamp and traceback will be printed. This can help track down memory leaks.



## C Function execution tracing

Run
```
scripts/callgraph -x $PID -t $TRIGGER -n 20
```
to trace 20 executions of function $TRIGGER, and print a microsecond-timed callgraph. $TRIGGER should be a C function in the interpreter (so this is pretty low level).


---


[1] The "debug" Python binary is built with `--with-pydebug`, which also builds the interpreter with `-O0`, and enables the debug memory allocator. Those changes can negatively affect application performance, when all we really need here is a binary with DWARF debugging symbols in it. If this is a factor, consider building your own Python binary instead. E.g.
```
export $VER=2.7.11
wget https://www.python.org/ftp/python/$VER/Python-$VER.tar.xz
tar -xvJf Python-$VER.tar.xz
cd Python-$VER
./configure CFLAGS='-g -fno-omit-frame-pointer' --prefix=/opt/python-$VER-dbg
make
sudo make install
```
