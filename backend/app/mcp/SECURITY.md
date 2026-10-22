# MCP runtime security boundary

Remote Streamable HTTP MCP connections are disabled by default. Setting
`MCP_REMOTE_HTTP_EGRESS_PROTECTED=true` is an operator assertion that the
deployment has outbound network controls; it is not a request-level override.
Setting this flag alone does not create or enforce a firewall or network
policy. Leave it false until the deployment's egress controls have been
independently verified.

Application code provides these checks:

- HTTPS only, port 443 only, and no URL credentials.
- DNS answers that are private, loopback, link-local, multicast, reserved, or
  otherwise non-public are rejected before connection and before tool calls.
- HTTP redirects and environment proxy settings are disabled.
- Connection ownership, enabled state, configuration fingerprint, tool
  approval, and schema hash are rechecked before dispatch.
- PostgreSQL row locks keep normal application mutations from committing while
  an authorized call is being dispatched.

These checks do not pin the validated IP address to the TLS connection. DNS can
change between validation and socket connection, so DNS rebinding is still
possible at the application layer. Production egress controls must deny private,
loopback, link-local, metadata-service, multicast, reserved, cluster-internal,
and organization-internal destinations after DNS resolution. Controls should
apply to both IPv4 and IPv6 and should not permit an unrestricted outbound
proxy. TLS hostname and SNI verification must remain enabled.

The row-lock authorization contract applies to mutations made through the same
PostgreSQL records. Direct database administration, a service that bypasses
these records, and a remote operation that continues server-side after client
cancellation are outside that guarantee. Prefer read-only and idempotent tools
and enforce authorization again at the remote service.
