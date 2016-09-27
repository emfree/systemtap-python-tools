import os
import re
import subprocess

shared_library_re = re.compile("\.so[0-9\.]*$")
libpython_re = re.compile(r'\t.* => (.*libpython.*) \(0x')


def abspath(f):
    return os.path.join(os.path.dirname(__file__), f)


def gen_tapset_macros(pid, tapset_dir):
    binary_path = os.path.realpath('/proc/{}/exe'.format(pid))
    python_lib_path = binary_path
    lines = subprocess.check_output(["ldd", binary_path]).splitlines()
    for line in lines:
        m = libpython_re.match(line)
        if not m:
            continue
        python_lib_path = m.group(1)
        break

    with open(os.path.join(tapset_dir, 'py_library.stpm'), 'w') as f:
        f.write('@define PYTHON_LIBRARY %( "{}" %)'.format(python_lib_path))


def child_pids(main_pid):
    children = subprocess.Popen(['pgrep', '--parent', main_pid],
                                stdout=subprocess.PIPE).communicate()[0]
    return children.splitlines()


def shared_libs(main_pid, child_pids):
    binary_path = os.path.realpath('/proc/{}/exe'.format(main_pid))
    shared_libs = {binary_path, "kernel"}

    pids = [main_pid] + child_pids

    # Try to automatically load symbols for any shared libraries
    # the process and corresponding subprocesses (if any) are using.
    for pid in pids:
        with open("/proc/{}/maps".format(pid), "r") as fhandler:
            for line in fhandler:
                line = line.strip()
                cols = line.split(None, 5)
                if len(cols) != 6:
                    continue
                lib_path = cols[5]
                if shared_library_re.findall(lib_path):
                    shared_libs.add(lib_path)
    return shared_libs


def build_stap_args(main_pid):
    args = ['-x', main_pid]

    children = child_pids(main_pid)
    for pid in children:
        args.extend(("-x", pid))

    for lib in shared_libs(main_pid, children):
        if lib:
            args.extend(('-d', lib))
    return args
