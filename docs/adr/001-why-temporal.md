# ADR 001: Use Temporal for Workflow Orchestration

**Status:** Accepted

**Date:** 2024-01-15

**Decision Makers:** Platform Architecture Team

## Context

The enterprise agent orchestrator requires reliable workflow orchestration for complex, multi-step agent deployment and coordination processes. These workflows must handle:

- Long-running operations (deployments lasting minutes to hours)
- Automatic retry logic with exponential backoff
- Compensating transactions for rollbacks
- Visibility into workflow execution state
- Distributed coordination across multiple agents
- Guaranteed exactly-once execution semantics

We evaluated three primary options:

1. **Custom workflow engine** built on Redis queues and PostgreSQL state tracking
2. **AWS Step Functions** for managed workflow orchestration
3. **Temporal** for durable workflow orchestration

## Decision

We will use Temporal as our workflow orchestration platform.

## Rationale

### Temporal Advantages

**Developer Experience:**
- Workflows written in Python using familiar async/await patterns
- Type-safe workflow definitions with full IDE support
- Local development and testing without cloud dependencies
- Strong debugging capabilities with workflow replay

**Operational Reliability:**
- Automatic retries with configurable policies
- Built-in compensation and rollback patterns
- Event sourcing ensures complete audit trail
- Handles failure scenarios (worker crashes, network partitions) transparently
- Guaranteed execution even if worker processes restart

**Scalability:**
- Proven at scale (handles millions of workflows at Uber, Netflix, Stripe)
- Horizontal scaling of workers
- Efficient workflow state management
- Low operational overhead

**Flexibility:**
- Cloud-agnostic (runs on-premise or any cloud)
- Support for both short and long-running workflows
- Rich querying and monitoring capabilities
- Active open-source community

### Alternatives Considered

**Custom Workflow Engine:**
- Pros: Full control, no external dependencies
- Cons: High development cost, operational complexity, risk of bugs in critical infrastructure, limited observability
- Rejected because: Building a reliable workflow engine is a substantial engineering investment that diverts resources from core business value

**AWS Step Functions:**
- Pros: Managed service, integrates with AWS ecosystem
- Cons: Vendor lock-in, limited local development, JSON-based workflow definitions are verbose, higher costs at scale, less flexible retry/compensation logic
- Rejected because: Tight AWS coupling limits deployment flexibility and JSON definitions reduce developer productivity

## Consequences

### Positive

- **Faster Development:** Engineers write workflows in Python without learning new DSLs
- **Operational Confidence:** Battle-tested system with proven reliability
- **Audit Compliance:** Complete event history for regulatory requirements
- **Failure Resilience:** Automatic handling of transient failures reduces operational burden

### Negative

- **Additional Infrastructure:** Requires running Temporal server (adds operational complexity)
- **Learning Curve:** Team must learn Temporal concepts (workflows, activities, signals)
- **Resource Overhead:** Temporal server requires database and compute resources

### Mitigation Strategies

- Use Temporal Cloud for production to eliminate server management overhead (optional)
- Provide team training and internal documentation
- Start with Docker Compose for local development to minimize setup friction
- Use Temporal's Web UI for workflow visibility and debugging

## Implementation Notes

- Temporal server runs in Docker Compose for local development
- Production deployment uses managed Temporal Cloud or self-hosted on ECS
- Workflow definitions stored in `apps/worker/workflows/`
- Activity implementations in `apps/worker/activities/`
- Task queue: `enterprise-agents`

## References

- [Temporal Documentation](https://docs.temporal.io/)
- [Temporal Python SDK](https://github.com/temporalio/sdk-python)
- [Temporal Architecture](https://docs.temporal.io/concepts/what-is-temporal)
