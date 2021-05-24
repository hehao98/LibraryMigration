import os
import sys

# ref: https://codereview.stackexchange.com/questions/25417/
# to install silently
class StdoutToFile:
    def __init__(self,stdout = None, stderr = None, file = ''):
        if not file:
            self.devnull = open(os.devnull,'w')
        else:
            self.devnull = open(file,'w+')
        self._stdout = stdout or self.devnull or sys.stdout
        self._stderr = stderr or self.devnull or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, traceback):
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        self.devnull.close()


# ref: https://stackoverflow.com/questions/1218933/
# >>> with RedirectedStdout() as out:
# >>>     print('asdf')
# >>>     s = str(out)
# >>>     print('bsdf')
# >>> print(s, out)
# 'asdf\n' 'asdf\nbsdf\n'

import sys
from io import StringIO

class StdoutToString:
    def __init__(self):
        self._stdout = None
        self._stderr = None
        self._string_io = None

    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = sys.stderr = self._string_io = StringIO()
        return self

    def __exit__(self, type, value, traceback):
        sys.stdout = self._stdout
        sys.stderr = self._stderr

    def __str__(self):
        return self._string_io.getvalue()