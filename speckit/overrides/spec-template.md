---
feature: "[###-feature-name]"   # equals this directory's name, e.g. 012-payment-qr
status: draft                    # draft | approved | accepted | released | superseded
epic: "[EPIC]"                   # a label; the roadmap groups specs by it
owner: "[OWNER]"                 # who drives this spec
approved_by:                     # the owner's name, written when the owner approves (HARD-GATE)
approved_on:                     # YYYY-MM-DD, written with approved_by
---
<!-- TEMPLATE NOTE - delete this comment from the generated spec.md.
     WHO READS ME: /speckit-specify and .specify/scripts/bash/create-new-feature.sh, which copy
     me to specs/<id>/spec.md. The AI Factory Kit installs me as
     .specify/templates/overrides/spec-template.md (bin/adopt.py); Spec Kit reads an override
     before its own template.
     I POINT TO (kit paths; factory/... once adopted): speckit/README.md (what this override
     changes and why) · model/SPEC-FLOW.md (the frontmatter and the status lifecycle) ·
     gates/check-plan-sync.sh and gates/check-spec-approval.sh (the gates that read it).
     Kit changes to Spec Kit's spec-template (specify-cli 1.0.12): (1) the frontmatter above,
     which opens at line 1 and holds the only status - the upstream body line
     "**Status**: Draft" is removed; (2) the "**Tests**:" line under User Scenarios & Testing,
     because /speckit-tasks writes test tasks only when the specification asks for them.
     Everything else is upstream text. Adapted from github/spec-kit - MIT License,
     Copyright GitHub, Inc. (THIRD_PARTY_NOTICES.md). -->

# Feature Specification: [FEATURE NAME]

**Feature Branch**: `[###-feature-name]`

**Created**: [DATE]

**Input**: User description: "$ARGUMENTS"

## User Scenarios & Testing *(mandatory)*

**Tests**: required. This project works test-first (constitution Article VI): every user
story below gets test tasks, written and seen to fail before the code that makes them pass.

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

## Assumptions

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right assumptions based on reasonable defaults
  chosen when the feature description did not specify certain details.
-->

- [Assumption about target users, e.g., "Users have stable internet connectivity"]
- [Assumption about scope boundaries, e.g., "Mobile support is out of scope for v1"]
- [Assumption about data/environment, e.g., "Existing authentication system will be reused"]
- [Dependency on existing system/service, e.g., "Requires access to the existing user profile API"]
