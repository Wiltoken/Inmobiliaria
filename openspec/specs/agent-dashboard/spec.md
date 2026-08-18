# Agent Dashboard Specification

## Purpose

Define the agent dashboard for managing multiple property listings, viewing client matches, and creating inquiries on behalf of clients. This is a V2 capability built on top of user-profiles, property-management, and buyer-matching.

## Requirements

### Requirement: Agent Managed Listings
**ID**: REQ-INMO-040
**Priority**: HIGH
**Capability**: agent-dashboard

The system SHALL provide agents with a dashboard view of all properties they have created. The view MUST include property status, creation date, view count, and inquiry count. Results MUST be filterable by status and sortable by date or score.

#### Scenario: Agent views all managed listings
**Given** an authenticated agent with 10 created properties
**When** the agent sends GET /api/v1/agent/dashboard/listings
**Then** all 10 properties are returned with status, created_at, and stats
**And** results include pagination metadata

#### Scenario: Agent filters listings by status
**Given** an agent with properties in draft, published, and sold statuses
**When** the agent requests listings with filter status=published
**Then** only published properties are returned

#### Scenario: Agent sees listing statistics
**Given** a published property with 5 inquiries and 100 views
**When** the agent views the listing detail in the dashboard
**Then** the response includes inquiry_count and view_count

### Requirement: Agent Client List
**ID**: REQ-INMO-041
**Priority**: HIGH
**Capability**: agent-dashboard

The system SHALL provide agents with a view of buyers assigned to them. Assignment occurs when a buyer selects an agent during registration or when an agent creates an inquiry on behalf of a buyer. The client list MUST include buyer name, preferences summary, and last activity date.

#### Scenario: Agent views assigned clients
**Given** an agent with 5 assigned buyers
**When** the agent sends GET /api/v1/agent/dashboard/clients
**Then** all 5 clients are returned with name, preference summary, and last_activity
**And** results are paginated

#### Scenario: Agent views client preferences
**Given** an agent with an assigned buyer
**When** the agent sends GET /api/v1/agent/dashboard/clients/{buyer_id}
**Then** the buyer's preference summary is returned (budget, locations, property types)
**And** sensitive personal data is excluded

### Requirement: Agent Client Match Results
**ID**: REQ-INMO-042
**Priority**: HIGH
**Capability**: agent-dashboard

The system SHALL allow agents to view match results for their assigned clients. The agent sees the same match data as the buyer: property summary, score, and score_breakdown. This enables agents to proactively recommend properties.

#### Scenario: Agent views matches for a client
**Given** an agent with an assigned buyer who has match results
**When** the agent sends GET /api/v1/agent/dashboard/clients/{buyer_id}/matches
**Then** the buyer's match results are returned sorted by score
**And** each result includes property summary and score_breakdown

#### Scenario: Agent sees no matches for new client
**Given** an agent with a newly assigned buyer with no preferences set
**When** the agent requests matches for that buyer
**Then** an empty results array is returned
**And** the response suggests setting buyer preferences

### Requirement: Agent Creates Inquiry for Client
**ID**: REQ-INMO-043
**Priority**: MEDIUM
**Capability**: agent-dashboard

The system SHALL allow agents to create inquiries on behalf of their assigned clients. The inquiry MUST reference both the agent (as creator) and the buyer (as the interested party). The property owner sees the buyer as the inquirer, with the agent as facilitator.

#### Scenario: Agent creates inquiry for assigned client
**Given** an agent with an assigned buyer and a published property
**When** the agent POSTs /api/v1/agent/inquiries with buyer_id, property_id, and message
**Then** an inquiry is created with the buyer as from_user
**And** the inquiry is flagged as agent_facilitated
**And** the property owner receives notification referencing both buyer and agent

#### Scenario: Agent cannot create inquiry for unassigned buyer
**Given** an agent and a buyer not assigned to them
**When** the agent attempts to create an inquiry for that buyer
**Then** the system returns 403 Forbidden

### Requirement: Dashboard Statistics
**ID**: REQ-INMO-044
**Priority**: MEDIUM
**Capability**: agent-dashboard

The system SHALL provide aggregated dashboard statistics for agents. Stats MUST include: active_listings count, pending_inquiries count, recent_matches count (last 7 days), and total_clients count. Stats MUST be returned in a single endpoint.

#### Scenario: Agent views dashboard summary
**Given** an agent with 5 active listings, 3 pending inquiries, 10 recent matches, and 8 clients
**When** the agent sends GET /api/v1/agent/dashboard/stats
**Then** the response includes active_listings: 5, pending_inquiries: 3, recent_matches: 10, total_clients: 8

#### Scenario: Dashboard stats update in real-time
**Given** an agent with current dashboard stats
**When** a new inquiry is created on one of the agent's properties
**Then** the next GET /api/v1/agent/dashboard/stats reflects the updated pending_inquiries count
