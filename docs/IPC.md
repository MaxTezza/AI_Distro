# IPC Protocol

This document describes the line-delimited JSON protocol used by `ai-distro-agent`.

## Request

Each request is a single JSON object on a single line:

```json
{"version":1,"name":"package_install","payload":"vim,curl"}
```

### Fields
- `version` (number, optional): IPC protocol version. Default is `1`.
- `name` (string, required): action name.
- `payload` (string, optional): action payload. For `package_install`, this is a comma-separated list of packages.

### Natural Language Request

To send a natural English command through IPC, use the special action name:

```json
{"version":1,"name":"natural_language","payload":"install firefox and vim"}
```

The agent will parse the payload into an internal action and execute it using policy rules.

## Response

Each response is a single JSON object on a single line:

```json
{"version":1,"action":"package_install","status":"confirm","message":"user confirmation required","capabilities":null}
```

### Fields
- `version` (number): IPC protocol version for the response.
- `action` (string): action name from the request.
- `status` (string): one of `ok`, `confirm`, `deny`, `error`.
- `message` (string, optional): additional details.
- `capabilities` (object, optional): present for `get_capabilities` responses.
- `confirmation_id` (string, optional): present when status is `confirm`.

## Payload Schemas

### `package_install`

Payload is a comma-separated list of package names:

```text
vim,curl,openssl
```

Rules:
- Whitespace is trimmed around each package.
- Empty entries are ignored.

### `system_update`

Payload is a channel string:

```text
stable
```

### `read_context`

Payload is a context identifier:

```text
default
```

### `get_capabilities`

Payload is empty or omitted:

```text
<empty>
```

Response includes a `capabilities` object:

```json
{
  "ipc_version": 1,
  "protocol_version": 1,
  "actions": [
    "package_install",
    "system_update",
    "read_context",
    "get_capabilities",
    "ping",
    "open_url",
    "open_app",
    "set_volume",
    "set_brightness",
    "network_wifi_on",
    "network_wifi_off",
    "network_bluetooth_on",
    "network_bluetooth_off",
    "power_reboot",
    "power_shutdown",
    "power_sleep",
    "remember"
  ]
}
```

### `ping`

Payload is empty or omitted:

```text
<empty>
```

Response message:

```json
{"version":1,"action":"ping","status":"ok","message":"pong","capabilities":null,"confirmation_id":null}
```

### `open_url`

Payload is a URL string:

```text
https://mail.google.com/
```

### `open_app`

Payload is an application identifier:

```text
firefox
```

### `set_volume`

Payload is a percentage:

```text
40
```

### `set_brightness`

Payload is a percentage:

```text
60
```

### `remember`

Payload is a short note to store in local memory:

```text
my name is Sam
```

### `confirm`

Payload is a confirmation id returned in a `confirm` response:

```json
{"version":1,"name":"confirm","payload":"<id>"}
```

If valid and not expired, the original request is executed.

## Examples

### Package install requiring confirmation

```json
{"version":1,"name":"package_install","payload":"vim,openssl"}
```

```json
{"version":1,"action":"package_install","status":"confirm","message":"user confirmation required","capabilities":null}
```

### Denied action

```json
{"version":1,"name":"package_install","payload":"badpkg"}
```

```json
{"version":1,"action":"package_install","status":"deny","message":"action denied by policy","capabilities":null}
```
