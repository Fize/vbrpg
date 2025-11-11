<!--
SYNC IMPACT REPORT
==================
Version Change: 0.0.0 → 1.0.0
Change Type: Initial Constitution
Date: 2025-11-09

Modified Principles:
- ✅ NEW: I. Test-First Development (NON-NEGOTIABLE)
- ✅ NEW: II. Component Isolation & Service Boundaries
- ✅ NEW: III. API Contracts & Type Safety
- ✅ NEW: IV. Real-Time State Synchronization
- ✅ NEW: V. AI Integration & Graceful Degradation

Added Sections:
- ✅ Core Principles (5 principles)
- ✅ Performance & Reliability Standards
- ✅ Development Workflow & Quality Gates
- ✅ Governance

Templates Status:
- ✅ plan-template.md: Constitution Check section already aligned
- ✅ spec-template.md: Acceptance scenarios align with testing principles
- ✅ tasks-template.md: Test-first task ordering already enforced
- ⚠ No command templates found (commands/ directory does not exist)

Follow-up TODOs:
- None - all placeholders resolved

Rationale:
- Initial constitution establishment for VBRPG project
- Principles derived from implemented architecture (FastAPI backend, Vue 3 frontend, WebSocket communication, AI agent integration)
- Test-first approach already demonstrated in codebase (80 passing tests, 53% coverage)
- MAJOR version 1.0.0 appropriate for initial ratification
-->

# VBRPG Platform Constitution

## Core Principles

### I. Test-First Development (NON-NEGOTIABLE)

All production code MUST be preceded by failing tests. The mandatory sequence is:

1. Write acceptance tests from user stories
2. Obtain user/stakeholder approval of test scenarios
3. Verify tests fail (Red)
4. Implement minimum code to pass tests (Green)
5. Refactor while maintaining test pass (Refactor)

**Rationale**: Test-first development prevents scope creep, ensures requirements are testable, provides regression safety, and serves as executable documentation. The platform's 80 passing tests with 53% coverage demonstrate this principle in action.

**Requirements**:
- Unit tests for models and services
- Integration tests for API endpoints and WebSocket events
- Contract tests for inter-service communication
- End-to-end tests for critical user journeys
- All tests must run in CI/CD pipeline

### II. Component Isolation & Service Boundaries

Backend and frontend MUST be independently deployable with clear service boundaries. Each service layer MUST be self-contained with well-defined responsibilities.

**Rationale**: Separation enables parallel development, independent scaling, technology flexibility, and clear ownership. The backend/frontend split allows frontend changes without backend redeployment and vice versa.

**Requirements**:
- Backend services expose stable API contracts (OpenAPI/AsyncAPI)
- Frontend communicates only through documented APIs and WebSocket events
- Shared types/schemas versioned independently
- No direct database access from frontend
- Services must handle partner service unavailability gracefully

### III. API Contracts & Type Safety

All inter-service communication MUST be governed by explicit, versioned contracts. Breaking changes require version increments and migration paths.

**Rationale**: Contracts prevent integration breakage, enable parallel development, provide documentation, and support automated testing. Explicit contracts are essential for real-time multiplayer platform stability.

**Requirements**:
- REST endpoints documented with OpenAPI specifications
- WebSocket events documented with AsyncAPI specifications
- Request/response schemas strictly validated
- Type definitions shared between backend and frontend
- Contract tests verify compliance on both sides
- Version endpoints semantically (MAJOR.MINOR.PATCH)

### IV. Real-Time State Synchronization

Game state MUST be the single source of truth on the backend. All clients receive state updates via WebSocket events within 1 second. State changes MUST be atomic and maintain consistency.

**Rationale**: Real-time multiplayer games require immediate state propagation, consistent game state across all clients, and conflict-free concurrent updates. This principle ensures fair gameplay and prevents desynchronization bugs.

**Requirements**:
- Backend maintains authoritative game state
- State changes broadcast immediately to all room participants
- Optimistic UI updates with server reconciliation
- Reconnection recovery within 5-minute window
- Event ordering guaranteed per game room
- AI agent actions treated identically to human actions

### V. AI Integration & Graceful Degradation

AI agent integration MUST NOT block critical game functionality. LLM failures require clear user communication and degradation strategies.

**Rationale**: External LLM services have variable availability and latency. The platform must provide value even when AI services are degraded, while managing user expectations transparently.

**Requirements**:
- AI agent responses timeout after 10 seconds (95th percentile)
- LLM failures reported to users with context
- Game state persists across AI service interruptions
- AI agent actions logged for debugging and improvement
- Fallback behaviors documented per game type
- LLM API keys and configuration externalized

## Performance & Reliability Standards

The platform MUST meet these non-negotiable performance targets:

- **Concurrent Capacity**: Support 50 game sessions (200 players) simultaneously
- **State Sync Latency**: Game state updates delivered within 1 second (95th percentile)
- **AI Response Time**: AI agent actions complete within 10 seconds (95th percentile)
- **Availability**: 99% uptime during active hours (excluding planned maintenance)
- **Reconnection Grace**: 5-minute window for disconnected players to rejoin

**Testing Requirements**:
- Load testing at 150% target capacity (75 rooms, 300 players)
- WebSocket connection stability tests (1+ hour sessions)
- AI timeout and fallback scenario validation
- Database concurrent access stress tests

**Monitoring Requirements**:
- Real-time connection count and room status
- AI response time distribution and failure rates
- WebSocket message latency metrics
- Database query performance tracking

## Development Workflow & Quality Gates

### Pre-Implementation Gates

1. **Specification Review**: User stories must include acceptance scenarios, priority ranking, and independent testability criteria
2. **Constitution Compliance**: Implementation plan must verify alignment with all five core principles or justify exceptions
3. **Contract Definition**: API/WebSocket contracts documented before implementation begins

### Implementation Gates

1. **Test-First Enforcement**: Pull requests without corresponding tests are blocked
2. **Code Coverage**: New code must maintain or improve coverage percentage (current: 53%)
3. **Contract Compliance**: Contract tests must pass before merging
4. **Linting**: Code must pass Ruff (Python) and ESLint (JavaScript) without warnings

### Post-Implementation Gates

1. **Integration Validation**: Full user story flow verified in staging environment
2. **Performance Testing**: Load tests confirm no regression on performance standards
3. **Documentation**: API changes reflected in OpenAPI/AsyncAPI specs
4. **Deployment Verification**: Smoke tests pass in production environment

## Governance

This constitution supersedes all other development practices and guidelines. All code reviews, architecture decisions, and feature specifications MUST demonstrate compliance with these principles.

**Amendment Procedure**:
1. Proposed changes documented with rationale and impact analysis
2. Team review and approval (unanimous for core principles, majority for standards)
3. Version increment per semantic versioning rules
4. Migration plan for affected code and documentation
5. Update propagated to all template files and guidance documents

**Versioning Policy**:
- **MAJOR**: Backward-incompatible principle removal/redefinition, fundamental architecture change
- **MINOR**: New principle added, existing principle materially expanded
- **PATCH**: Clarifications, wording improvements, non-semantic refinements

**Compliance Enforcement**:
- All feature specifications must reference this constitution
- Implementation plans must include "Constitution Check" section
- Pull request templates require constitutional compliance confirmation
- Quarterly reviews to assess adherence and identify improvement areas

**Runtime Guidance**: See `.github/copilot-instructions.md` for AI-assisted development guidance aligned with constitutional principles.

**Version**: 1.0.0 | **Ratified**: 2025-11-09 | **Last Amended**: 2025-11-09
