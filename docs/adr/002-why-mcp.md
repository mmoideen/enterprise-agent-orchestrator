# ADR 002: Use Model Context Protocol for Agent Integration

**Status:** Accepted

**Date:** 2024-01-15

**Decision Makers:** Platform Architecture Team

## Context

Enterprise agents need to access external tools and services (databases, APIs, internal systems) in a standardized, discoverable, and secure manner. We need a mechanism that allows:

- Dynamic tool discovery and invocation
- Standardized interface for diverse tool types
- Security controls and audit logging
- Version management for tool APIs
- Language-agnostic integration

We evaluated three approaches:

1. **Custom RPC framework** with proprietary protocol
2. **OpenAPI/REST** for tool exposure
3. **Model Context Protocol (MCP)** for standardized tool integration

## Decision

We will use the Model Context Protocol (MCP) for agent-to-tool integration.

## Rationale

### MCP Advantages

**Standardization:**
- Emerging industry standard for AI agent tool integration
- Well-defined specification for tool discovery and invocation
- JSON Schema for input/output validation
- Consistent across different agent implementations

**Developer Productivity:**
- Tools exposed once are available to all agents
- Clear contract between tool providers and consumers
- Automatic client generation from tool definitions
- Rich metadata for tool discovery

**Security and Governance:**
- Structured input validation prevents injection attacks
- Audit logging at protocol level
- Fine-grained access control per tool
- Input/output inspection for policy enforcement

**Ecosystem Growth:**
- Growing library of MCP-compatible tools
- Community contributions reduce development effort
- Integration with existing tooling ecosystems

### Alternatives Considered

**Custom RPC Framework:**
- Pros: Full control over protocol design, optimized for our specific needs
- Cons: No ecosystem, requires building client libraries, documentation burden, limited adoption outside our organization
- Rejected because: Reinventing the wheel slows development and limits integration options

**OpenAPI/REST:**
- Pros: Ubiquitous, well-understood, many tools available
- Cons: Verbose for agent use cases, lacks semantic metadata for tool selection, no standard for multi-step workflows, limited streaming support
- Rejected because: Generic HTTP API design does not capture AI agent-specific requirements

## Consequences

### Positive

- **Rapid Integration:** Agents connect to new tools with minimal code
- **Discoverability:** Agents can query available tools dynamically
- **Type Safety:** JSON Schema validation prevents runtime errors
- **Future-Proof:** Align with emerging AI agent standards
- **Interoperability:** MCP tools work with agents from other vendors

### Negative

- **Early Standard:** MCP specification still evolving (potential breaking changes)
- **Limited Tooling:** Fewer existing MCP servers compared to REST APIs
- **Adapter Overhead:** Existing tools require MCP adapter layer

### Mitigation Strategies

- Implement adapter layer to wrap existing REST/gRPC services as MCP tools
- Version MCP server APIs and support backward compatibility
- Contribute to MCP specification development
- Maintain internal tool registry with approved MCP servers

## Implementation Notes

- MCP client: `packages/mcp-adapter/client.py`
- MCP server: `packages/mcp-adapter/server.py`
- Tool discovery endpoint: `GET /tools`
- Tool invocation endpoint: `POST /tools/{tool_name}/invoke`
- JSON Schema validation on all inputs
- Audit logging for all tool invocations

## Security Considerations

- **Input Validation:** All tool inputs validated against JSON Schema
- **Authentication:** MCP clients authenticate using JWT tokens
- **Authorization:** Policy engine controls which agents can invoke which tools
- **Rate Limiting:** Prevent abuse through quota management
- **Output Filtering:** PII detection on tool outputs

## Example Tool Definition

```json
{
  "name": "query_customer_database",
  "description": "Query customer information from CRM",
  "inputSchema": {
    "type": "object",
    "properties": {
      "customer_id": {"type": "string"},
      "fields": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["customer_id"]
  }
}
```

## References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Anthropic MCP Announcement](https://www.anthropic.com/news/model-context-protocol)
