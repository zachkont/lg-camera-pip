#!/usr/bin/env python3
"""Run shell commands on a rooted LG TV over the Homebrew Channel's telnet root shell.

Usage: tvshell.py <tv-ip> '<command>'            run it, print its output, exit with its status
       tvshell.py <tv-ip> --put <local> <remote>  copy a file (sent as base64 over telnet)

The telnet shell has no authentication: anything that can reach port 23 on the TV
is root. Keep the TV on a trusted network.
"""
import base64
import shlex
import socket
import sys
import time
import uuid

IAC, DONT, DO, WONT, WILL, SB, SE = 255, 254, 253, 252, 251, 250, 240


class Telnet:
    def __init__(self, host, port=23, timeout=10):
        self.s = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""

    def _recv(self):
        data = self.s.recv(65536)
        if not data:
            raise EOFError("connection closed")
        out = bytearray()
        i = 0
        while i < len(data):
            b = data[i]
            if b == IAC and i + 1 < len(data):
                cmd = data[i + 1]
                if cmd in (DO, DONT, WILL, WONT) and i + 2 < len(data):
                    opt = data[i + 2]
                    # Refuse every option: plain line mode is all we need.
                    reply = WONT if cmd in (DO, DONT) else DONT
                    self.s.sendall(bytes([IAC, reply, opt]))
                    i += 3
                    continue
                if cmd == SB:
                    j = data.find(bytes([IAC, SE]), i)
                    i = j + 2 if j != -1 else len(data)
                    continue
                i += 2
                continue
            out.append(b)
            i += 1
        return bytes(out)

    def read_until(self, marker, timeout=60):
        end = time.time() + timeout
        while marker not in self.buf:
            if time.time() > end:
                raise TimeoutError("timed out waiting for output")
            self.s.settimeout(max(0.1, end - time.time()))
            self.buf += self._recv()
        idx = self.buf.index(marker) + len(marker)
        out, self.buf = self.buf[:idx], self.buf[idx:]
        return out

    def run(self, cmd, timeout=60):
        tag = uuid.uuid4().hex[:12]
        start, done = ("__S%s__" % tag).encode(), ("__E%s__" % tag).encode()
        # Typed as __S""<tag>__ so the terminal's echo of the line never matches;
        # only the shell's printed output reads __S<tag>__.
        line = 'echo __S""%s__; %s; echo __E""%s__:$?\n' % (tag, cmd, tag)
        self.s.sendall(line.encode())
        self.read_until(start, timeout)
        out = self.read_until(done, timeout)[: -len(done)]
        rc_line = self.read_until(b"\n", timeout)
        rc = int(rc_line.strip(b":\r\n ") or b"0")
        return out.decode(errors="replace").replace("\r", "").strip("\n"), rc


# Base64 is sent in short lines: the TV's terminal stalls on long input lines.
CHUNK = 400


def put(t, local, remote):
    raw = open(local, "rb").read()
    data = base64.b64encode(raw).decode()
    r, tmp = shlex.quote(remote), shlex.quote(remote + ".b64")
    t.run(": > %s" % tmp)
    for i in range(0, len(data), CHUNK):
        _, rc = t.run("printf '%%s' '%s' >> %s" % (data[i:i + CHUNK], tmp))
        if rc != 0:
            sys.exit("write to %s failed (exit %d)" % (remote, rc))
    out, rc = t.run("base64 -d %s > %s && rm %s && wc -c < %s" % (tmp, r, tmp, r))
    if rc != 0 or out.strip() != str(len(raw)):
        sys.exit("copy to %s failed: got %r bytes, expected %d" % (remote, out.strip(), len(raw)))
    return out


def main():
    if len(sys.argv) == 3:
        host, cmd = sys.argv[1], sys.argv[2]
    elif len(sys.argv) == 5 and sys.argv[2] == "--put":
        host, cmd = sys.argv[1], None
    else:
        sys.exit(__doc__.strip())
    t = Telnet(host)
    time.sleep(0.5)
    if cmd is None:
        print(put(t, sys.argv[3], sys.argv[4]))
        return
    out, rc = t.run(cmd, timeout=120)
    print(out)
    sys.exit(rc)


if __name__ == "__main__":
    main()
