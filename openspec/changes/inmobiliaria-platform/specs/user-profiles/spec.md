# User Profiles Specification

## Purpose

Define role-based user registration and profile management for the Inmobiliaria platform. Extends the auth-login-platform User model with buyer, seller, and agent profiles. Supports CRUD operations and admin user oversight.

## Requirements

### Requirement: Buyer Registration and Profile
**ID**: REQ-INMO-001
**Priority**: CRITICAL
**Capability**: user-profiles

The system SHALL allow users to register as buyers with a profile containing search preferences. The profile MUST link to the base User model via a one-to-one relationship and include: budget_min, budget_max (COP), preferred_locations (JSONB array), rooms_min, bathrooms_min, area_min, area_max, preferred_features (JSONB array), preferred_property_types (ENUM array). Registration MUST reuse the auth-login-platform JWT + RBAC flow.

#### Scenario: Buyer registers with preferences
**Given** a new user completes registration with role "buyer"
**When** the system creates a BuyerProfile linked to the User
**Then** the profile is persisted with all provided preference fields
**And** the user receives a valid JWT with role "buyer"

#### Scenario: Buyer updates preferences
**Given** an authenticated buyer with an existing profile
**When** the buyer submits updated preferences via PATCH /api/v1/profiles/buyer
**Then** the profile fields are updated
**And** the match cache for this buyer is invalidated

#### Scenario: Buyer views own profile
**Given** an authenticated buyer
**When** the buyer sends GET /api/v1/profiles/buyer
**Then** the system returns the full BuyerProfile with all preference fields

#### Scenario: Unauthenticated user cannot access profile
**Given** no valid JWT in the request
**When** the user sends GET /api/v1/profiles/buyer
**Then** the system returns 401 Unauthorized

### Requirement: Seller Registration and Profile
**ID**: REQ-INMO-002
**Priority**: CRITICAL
**Capability**: user-profiles

The system SHALL allow users to register as sellers with a profile containing company information. The profile MUST include: phone (required), company_name (nullable), and a reference to the base User. Sellers MUST have the "seller" RBAC role.

#### Scenario: Seller registers with company info
**Given** a new user completes registration with role "seller"
**When** the system creates a SellerProfile with phone and optional company_name
**Then** the profile is linked to the User
**And** the user receives a JWT with role "seller"

#### Scenario: Seller updates company information
**Given** an authenticated seller
**When** the seller PATCHes /api/v1/profiles/seller with new company_name
**Then** the company_name is updated
**And** the response returns the updated profile

### Requirement: Agent Registration and Profile
**ID**: REQ-INMO-003
**Priority**: CRITICAL
**Capability**: user-profiles

The system SHALL allow users to register as agents with professional credentials. The profile MUST include: license_number (required, unique), agency_name (required), and a reference to the base User. Agents MUST have the "agent" RBAC role.

#### Scenario: Agent registers with license
**Given** a new user completes registration with role "agent"
**When** the user provides license_number and agency_name
**Then** an AgentProfile is created and linked to the User
**And** the user receives a JWT with role "agent"

#### Scenario: Duplicate license number rejected
**Given** an agent profile already exists with license_number "LIC-001"
**When** a new registration attempts to use license_number "LIC-001"
**Then** the system returns 409 Conflict
**And** no new profile is created

### Requirement: Profile CRUD Operations
**ID**: REQ-INMO-004
**Priority**: HIGH
**Capability**: user-profiles

The system SHALL provide CRUD endpoints for each profile type. Users MAY only view and edit their own profile. The system MUST enforce ownership via JWT subject matching.

#### Scenario: User edits own profile
**Given** an authenticated buyer with an existing profile
**When** the buyer sends PATCH /api/v1/profiles/buyer with valid fields
**Then** only the provided fields are updated
**And** the response returns the updated profile with 200 OK

#### Scenario: User cannot edit another user's profile
**Given** an authenticated buyer A
**When** buyer A attempts to PATCH /api/v1/profiles/buyer with buyer B's ID
**Then** the system returns 403 Forbidden

### Requirement: Admin User Management
**ID**: REQ-INMO-005
**Priority**: HIGH
**Capability**: user-profiles

The system SHALL allow admin users to view all registered users across all roles. Admins MUST have the "admin" RBAC role. The admin endpoint MUST support pagination and role filtering.

#### Scenario: Admin lists all users with pagination
**Given** an authenticated admin user
**When** the admin sends GET /api/v1/admin/users?page=1&limit=20
**Then** the system returns paginated users with their roles and profile summaries
**And** the response includes total count and page metadata

#### Scenario: Admin filters users by role
**Given** an authenticated admin user
**When** the admin sends GET /api/v1/admin/users?role=agent
**Then** only users with the "agent" role are returned

#### Scenario: Non-admin cannot access user list
**Given** an authenticated buyer
**When** the buyer sends GET /api/v1/admin/users
**Then** the system returns 403 Forbidden
