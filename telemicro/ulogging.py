"""MIT License

Copyright (c) 2022 Youkii-Chen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

try:
    import time
except ImportError:
    import utime as time

try:
    from micropython import const
except ImportError:
    const = lambda x: x

from io import TextIOWrapper

__version__ = "v1.2"

DEBUG: int = const(10)
INFO: int = const(20)
WARN: int = const(30)
ERROR: int = const(40)
CRITICAL: int = const(50)

TO_FILE = const(100)
TO_TERM = const(200)

_level = const(0)
_msg = const(1)
_time = const(2)
_name = const(3)
_fnname = const(4)


def level_name(level: int, color: bool = False) -> str:
    if not color:
        if level == INFO:
            return "INFO"
        elif level == DEBUG:
            return "DEBUG"
        elif level == WARN:
            return "WARN"
        elif level == ERROR:
            return "ERROR"
        elif level == CRITICAL:
            return "CRITICAL"
    else:
        if level == INFO:
            return "\033[97mINFO\033[0m"
        elif level == DEBUG:
            return "\033[37mDEBUG\033[0m"
        elif level == WARN:
            return "\033[93mWARN\033[0m"
        elif level == ERROR:
            return "\033[35mERROR\033[0m"
        elif level == CRITICAL:
            return "\033[91mCRITICAL\033[0m"


class BaseClock:
    def __call__(self) -> str:
        return '%d' % time.time()


class Handler:
    _template: str
    _map: bytes
    level: int
    _direction: int
    _clock: BaseClock
    _color: bool
    _file_name: str
    _max_size: int
    _file = TextIOWrapper

    def __init__(self,
                 level: int = INFO,
                 colorful: bool = True,
                 fmt: str = "&(time)% - &(level)% - &(name)% - &(msg)%",
                 clock: BaseClock = None,
                 direction: int = TO_TERM,
                 file_name: str = "logging.log",
                 max_file_size: int = 4096
                 ):
        self._direction = direction
        self.level = level
        self._clock = clock if clock else BaseClock()
        self._color = colorful
        self._file_name = file_name if direction == TO_FILE else ''
        self._max_size = max_file_size if direction == TO_FILE else 0

        if direction == TO_FILE:
            self._file = open(file_name, 'a+')

        self._map = bytearray()
        idx = 0
        while True:
            idx = fmt.find("&(", idx)
            if idx >= 0:
                a_idx = fmt.find(")%", idx + 2)
                if a_idx < 0:
                    raise Exception(
                        "Unable to parse text format successfully.")
                text = fmt[idx + 2:a_idx]
                idx = a_idx + 2
                if text == "level":
                    self._map.append(_level)
                elif text == "msg":
                    self._map.append(_msg)
                elif text == "time":
                    self._map.append(_time)
                elif text == "name":
                    self._map.append(_name)
                elif text == "fnname":
                    self._map.append(_fnname)
            else:
                break

        self._template = fmt.replace("&(level)%", "%s") \
                             .replace("&(msg)%", "%s") \
                             .replace("&(time)%", "%s") \
                             .replace("&(name)%", "%s") \
                             .replace("&(fnname)%", "%s") \
                         + "\n" if fmt[:-1] != '\n' else ''

    def _msg(self, *args, level: int, name: str, fnname: str):
        if level < self.level:
            return
        # generate msg
        temp_map = []
        text = ''
        for item in self._map:
            if item == _msg:
                for text_ in args:
                    text = "%s%s" % (text, text_)
                temp_map.append(text)
            elif item == _level:
                if self._direction == TO_TERM:
                    temp_map.append(level_name(level, self._color))
                else:
                    temp_map.append(level_name(level))
            elif item == _time:
                temp_map.append(self._clock())
            elif item == _name:
                temp_map.append(name)
            elif item == _fnname:
                temp_map.append(fnname if fnname else "unknownfn")

        if self._direction == TO_TERM:
            self._to_term(tuple(temp_map))
        else:
            self._to_file(tuple(temp_map))

    def _to_term(self, map: tuple):
        print(self._template % map, end='')

    def _to_file(self, map: tuple):
        fp = self._file
        prev_idx = fp.tell()
        fp.seek(self._max_size)
        if fp.read(1):
            fp = self._file = open(self._file_name, 'w')
        else:
            fp.seek(prev_idx)

        fp.write(self._template % map)
        fp.flush()


class Logger():
    _handlers: list

    def __init__(self,
                 name: str,
                 handlers: list = None,
                 ):

        self.name = name
        if not handlers:
            self._handlers = [Handler()]
        else:
            self._handlers = handlers

    @property
    def handlers(self):
        return self._handlers

    def _msg(self, *args, level: int, fn: str):

        for item in self._handlers:
            item._msg(*args, level=level, fnname=fn, name=self.name)

    def debug(self, *args, fn: str = None):
        self._msg(*args, level=DEBUG, fn=fn)

    def info(self, *args, fn: str = None):
        self._msg(*args, level=INFO, fn=fn)

    def warn(self, *args, fn: str = None):
        self._msg(*args, level=WARN, fn=fn)

    def error(self, *args, fn: str = None):
        self._msg(*args, level=ERROR, fn=fn)

    def critical(self, *args, fn: str = None):
        self._msg(*args, level=CRITICAL, fn=fn)


__all__ = [
    Logger, Handler,
    BaseClock,

    DEBUG, INFO,
    WARN, ERROR,
    CRITICAL,

    TO_FILE,
    TO_TERM,

    __version__
]