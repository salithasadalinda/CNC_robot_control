# Security Policy

## Supported Versions

Security fixes are handled on the default branch during early development.

| Version | Supported |
| ------- | --------- |
| main    | Yes       |

## Reporting A Vulnerability

Please do not open a public issue for a security vulnerability.

Report security concerns by contacting the project maintainer through GitHub, or by opening a private security advisory if the repository has advisories enabled.

Include:

- A clear description of the issue.
- Steps to reproduce it.
- Any affected operating systems or CNC controller setups.
- Whether the issue could cause unintended machine movement, unsafe serial commands, or data loss.

## CNC Safety Notes

This project can send G-code commands to CNC or printer firmware. Treat bugs that may cause unexpected movement, unsafe homing, incorrect probing, or uncontrolled command execution as high severity.

Always test new workflows with motors disabled, a simulator, or a safe mock setup before using real hardware.
