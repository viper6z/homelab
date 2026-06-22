# TCP service

A small custom application-layer protocol built on TCP.

## Protocol

**Transport:** TCP
**Port:** `9000`
**Encoding:** UTF-8
**Message format:** One command per line, terminated by `\n`

```text
COMMAND [argument]\n
```

## Connection policy

1. The client opens a TCP connection.
2. The client sends one command.
3. The server validates and handles the command.
4. The server sends one response.
5. The server closes the client connection.

The client opens a new TCP connection for every command.

## Commands

### `PING`

Request:

```text
PING\n
```

Response:

```text
PONG\n
```

`PING` does not accept an argument.

### `ECHO <text>`

Request:

```text
ECHO hello world\n
```

Response:

```text
ECHO hello world\n
```

`ECHO` requires an argument.

## Errors

Unknown commands return:

```text
ERROR: unknown command\n
```

Known commands with an invalid format return:

```text
ERROR: invalid request\n
```

Examples:

```text
PING hello
→ ERROR: invalid request

ECHO
→ ERROR: invalid request

FAKECOMMAND hello
→ ERROR: unknown command
```

## Internal networking

The service is only available on the internal Docker `backend` network.

It is not exposed through a host port or Nginx.

Other containers connect using Docker Compose DNS:

```text
tcp-service:9000
```

