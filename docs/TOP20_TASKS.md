# Top 20 Voice Tasks (v1)

These are the first commands the product must do reliably for non-technical users.

## Everyday Controls

1. "open firefox" -> `open_app`
2. "go to docs.openai.com" -> `open_url`
3. "check my gmail" -> `open_url` (mail.google.com)
4. "search for weather in austin" -> `open_url` (search URL)
5. "set volume to 40 percent" -> `set_volume`
6. "set brightness to 60 percent" -> `set_brightness`
7. "turn on wifi" -> `network_wifi_on`
8. "turn off wifi" -> `network_wifi_off`
9. "turn on bluetooth" -> `network_bluetooth_on`
10. "turn off bluetooth" -> `network_bluetooth_off`

## Files and Memory

11. "list files in home" -> `list_files`
12. "list files in downloads" -> `list_files`
13. "remember that my printer is upstairs" -> `remember`
14. "what do you remember" -> `read_context`
15. "show my notes" -> `read_context`

## System and Assistant

16. "update the system" -> `system_update` (confirmation required)
17. "install vim and curl" -> `package_install` (confirmation required)
18. "restart the computer" -> `power_reboot` (confirmation required)
19. "what can you do" -> `get_capabilities`
20. "are you there" -> `ping`

## Release Gate

- Target: `>= 95%` on these 20 intents
- Target: `100%` confirmation enforcement for risky actions
- Target: `0` destructive action without confirmation
