"""MIT License

Copyright (c) 2020 popnotsoda95

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

import gc
gc.collect()
gc.threshold(gc.mem_free() // 4 + gc.mem_alloc())  # sets threshold to 1/4 of heap size

HTTP__version__ = "1.0"
__version__ = (0, 0, 2)


class TimeoutError(Exception):
    pass


class ConnectionError(Exception):
    pass


class Response:
    def __init__(self, reader, chunked, charset):
        self.raw = reader
        self.chunked = chunked
        self.encoder = charset
        self.chunk_size = 0

    async def read(self, sz=-1):
        content = b''
        # keep reading chunked data
        if self.chunked:
            sz = 4 * 1024 * 1024
            while True:
                if self.chunk_size == 0:
                    l = await self.raw.readline()  # get Hex size
                    l = l.split(b";", 1)[0]
                    self.chunk_size = int(l, 16)  # convert to int
                    if self.chunk_size == 0:  # end of message
                        sep = await self.raw.read(2)
                        assert sep == b"\r\n"
                        break
                data = await self.raw.read(min(sz, self.chunk_size))
                self.chunk_size -= len(data)
                content += data
                if self.chunk_size == 0:
                    sep = await self.raw.read(2)
                    assert sep == b"\r\n"
                    break
        # non chunked data
        else:
            while True:
                data = await self.raw.read(sz)
                if not data or data == b"":
                    break
                content += data
        return content

    @property
    def text(self):
        return str(self.content, self.encoder)

    def json(self):
        try:
            import json
        except ImportError:
            import ujson as json
        return json.loads(self.content)

    def close(self):
        pass

    def __repr__(self):
        return "<Response [%d]>" % (self.status_code)


class Requests:
    @staticmethod
    async def open_connection(host, port, ssl):
        try:
            from asyncio import core
        except ImportError:
            from uasyncio import core
        gc.collect()
        try:
            from asyncio.stream import Stream
        except ImportError:
            from uasyncio.stream import Stream
        gc.collect()
        try:
            from errno import EINPROGRESS
        except ImportError:
            from uerrno import EINPROGRESS
        gc.collect()
        try:
            import socket
        except ImportError:
            import usocket as socket
        gc.collect()

        ai = socket.getaddrinfo(host, port)[0]
        s = socket.socket(ai[0], ai[1], ai[2])
        s.setblocking(False)
        try:
            s.connect(ai[-1])
        except OSError as er:
            if er.args[0] != EINPROGRESS:
                raise er
        yield core._io_queue.queue_write(s)
        if ssl:
            try:
                import ssl as _ssl
            except ImportError:
                import ussl as _ssl
            s = _ssl.wrap_socket(s, server_hostname=host)
        yield core._io_queue.queue_write(s)
        ss = Stream(s)
        return ss, ss

    async def _request_raw(self, method, url, data, json):
        try:
            proto, dummy, host, path = url.split("/", 3)
        except ValueError:
            proto, dummy, host = url.split("/", 2)
            path = ""
        try:
            host, port = host.split(":")
            if proto == "https:":
                ssl = True
            elif proto == "http:":
                ssl = False
            else:
                raise ValueError("Unsupported protocol: %s" % (proto))
        except ValueError:
            if proto == "http:":
                port = 80
                ssl = False
            elif proto == "https:":
                port = 443
                ssl = True
            else:
                raise ValueError("Unsupported protocol: %s" % (proto))

        reader, writer = await self.open_connection(host, port, ssl)
        query = "%s /%s HTTP/%s\r\nHost: %s\r\nConnection: close\r\n" % (method, path, HTTP__version__, host)
        if "User-Agent:" not in query:
            query += "User-Agent: compat\r\n"
        if json is not None:
            import ujson
            data = ujson.dumps(json)
            if "Content-Type:" not in query:
                query += "Content-Type: application/json\r\n"
        if data:
            if "Content-Length:" not in query:
                query += "Content-Length: %d\r\n" % len(data)
        query += "\r\n"
        if data:
            query += data
        await writer.awrite(query.encode())
        return reader

    async def _request(self, method, url, params={}, data={},
                       files=None, allow_redirects=False, json=None):
        try:
            if params:
                url = url.rstrip("?")
                url += "?"
                for p in params:
                    url += p
                    url += "="
                    url += str(params[p])
                    url += "&"
                url = url[0:len(url) - 1]
        except Exception as e:
            raise e
        try:
            redir_cnt = 0
            while redir_cnt < 2:
                reader = await self._request_raw(method=method, url=url, data=data, json=json)
                sline = await reader.readline()
                sline = sline.split(None, 2)
                status_code = int(sline[1])
                if len(sline) > 1:
                    reason = sline[2].decode().rstrip()
                chunked = False
                json = None
                headers = []
                charset = 'utf-8'
                # read headers
                while True:
                    line = await reader.readline()
                    if not line or line == b"\r\n":
                        break
                    headers.append(line)
                    if line.startswith(b"Transfer-Encoding:"):
                        if b"chunked" in line:
                            chunked = True
                    elif line.startswith(b"Location:"):
                        url = line.rstrip().split(None, 1)[1].decode()
                    elif line.startswith(b"Content-Type:"):
                        if b"application/json" in line:
                            json = True
                        if b"charset" in line:
                            # get decoder
                            charset = line.rstrip().decode().split(None, 2)[-1].split("=")[-1]
                # look for redirects
                if allow_redirects is False:
                    break
                if 301 <= status_code <= 303:
                    redir_cnt += 1
                    await reader.wait_closed()
                    continue
                break

            resp = Response(reader, chunked, charset)
            resp.data = await resp.read()
            resp.status_code = status_code
            resp.reason = reason
            resp.url = url
            return resp

        except Exception as e:
            raise e
        finally:
            try:
                await reader.wait_closed()
            except NameError:
                pass
            gc.collect()

    async def get(self, url, **kwargs):
        return await self._request("GET", url, **kwargs)

    async def post(self, url, **kwargs):
        return await self._request("POST", url, **kwargs)
