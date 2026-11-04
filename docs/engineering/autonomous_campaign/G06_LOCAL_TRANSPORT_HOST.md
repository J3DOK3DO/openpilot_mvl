# G06 local Galaxy transport host prototype

Source: `openpilot/sunnypilot/starpilot_galaxy/local_transport.py`. This is an
explicitly invoked **host-only** Unix-domain socket adapter for `GalaxyHandler`.
Importing it creates no socket, thread, process, Params key or manager entry.
There is no production startup registration, TCP listener or vehicle-control
publisher. The default handler and listener state is OFF.

The caller must construct an enabled `GalaxyHandler`, pass `enable=True`, and
provide an existing directory owned by the current UID with no group/other
permissions. The adapter binds `galaxy.sock` there with mode 0600, checks
Linux `SO_PEERCRED` UID before reading any bytes, and accepts one request per
connection. A single `serve_once()` call handles at most one client; concurrent
calls are rejected. `close()` closes the listener and removes only the socket
inode it created. The caller owns the loop, service lifetime and directory.

The local protocol is a 4-byte big-endian length followed by UTF-8 JSON with
exact fields `method`, `path`, `headers`, and `body`. A response uses the same
frame shape with `status`, `headers`, and `body`. Only the canonical
`X-Galaxy-Token` header is accepted; duplicate JSON keys and case variants
are rejected. The core permits only authenticated GET requests on its three
read-only routes. Nonempty bodies are rejected. Limits: 8192 request bytes,
4096 header bytes, 256 path bytes, 16384 response bytes, one active client,
200 ms accept polling, and a two-second total request-read deadline. One
request closes the connection, so parser errors cannot be reused.

Host negative tests cover disabled construction, directory permissions,
unauthorized peer, wrong token, method/path/body/header rejection, duplicate
and malformed JSON, oversized and truncated frames, slow clients, concurrent
serve calls, provider failure, response secrecy and socket cleanup.

**G06 live transport remains HOLD.** The handler's caller-supplied snapshot
and model providers must be separately proven bounded: Python cannot safely
interrupt a blocked callback in this synchronous adapter. A device access
policy must identify the exact allowed UID and private runtime directory.
Independent security review, target CPU/RAM/IPC timing, shutdown under actual
service loss, and protected recovery remain unexecuted. This prototype is
not a device service or deployment authorization.
