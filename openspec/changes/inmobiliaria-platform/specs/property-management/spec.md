# Property Management Specification

## Purpose

Define property CRUD, search, filtering, photo management, and status workflow for the Inmobiliaria platform. Supports sellers and agents as property creators, with admin moderation.

## Requirements

### Requirement: Property Creation
**ID**: REQ-INMO-010
**Priority**: CRITICAL
**Capability**: property-management

The system SHALL allow authenticated sellers and agents to create properties. A property MUST include: type (ENUM: house, apartment, office, land, commercial, warehouse), operation (ENUM: sale, rent), price (DECIMAL, default COP), area_m2, location (GEOGRAPHY POINT via PostGIS), rooms, bathrooms, features (JSONB). Properties are created in "draft" status by default.

#### Scenario: Seller creates a property
**Given** an authenticated seller
**When** the seller POSTs /api/v1/properties with valid type, operation, price, area, and location
**Then** a property is created with status "draft"
**And** the response includes the property ID and all provided fields

#### Scenario: Agent creates a property
**Given** an authenticated agent
**When** the agent POSTs /api/v1/properties with valid fields
**Then** a property is created with status "draft"
**And** the property is linked to the agent's profile

#### Scenario: Buyer cannot create properties
**Given** an authenticated buyer
**When** the buyer POSTs /api/v1/properties
**Then** the system returns 403 Forbidden

#### Scenario: Property without required fields rejected
**Given** an authenticated seller
**When** the seller POSTs /api/v1/properties missing type or price
**Then** the system returns 400 Bad Request with field-level validation errors

### Requirement: Property Status Workflow
**ID**: REQ-INMO-011
**Priority**: CRITICAL
**Capability**: property-management

The system SHALL enforce a status workflow: draft → published → reserved → sold → archived. Transitions MUST follow this order. Only the property owner or an admin MAY trigger a transition.

#### Scenario: Seller publishes a draft property
**Given** a property in "draft" status owned by the seller
**When** the seller PATCHes the status to "published"
**Then** the property status becomes "published"
**And** the property becomes visible in public search results

#### Scenario: Invalid status transition rejected
**Given** a property in "draft" status
**When** the owner attempts to transition directly to "sold"
**Then** the system returns 400 Bad Request
**And** the status remains "draft"

#### Scenario: Only owner can change status
**Given** a property owned by seller A
**When** seller B attempts to change the property status
**Then** the system returns 403 Forbidden

### Requirement: Property Search and Filtering
**ID**: REQ-INMO-012
**Priority**: CRITICAL
**Capability**: property-management

The system SHALL provide property search with filters: type, operation, price_min, price_max, location (city or radius via PostGIS ST_DWithin), rooms_min, bathrooms_min, area_min, area_max. Results MUST be paginated and sorted by relevance or date. Search MUST complete in <500ms for up to 10K properties.

#### Scenario: Search by price range and type
**Given** published properties exist in the system
**When** a user sends GET /api/v1/properties?type=apartment&price_min=100000000&price_max=300000000
**Then** only apartments within the price range are returned
**And** results are paginated

#### Scenario: Search by geospatial radius
**Given** published properties with geographic locations
**When** a user sends GET /api/v1/properties?lat=4.6097&lon=-74.0817&radius_km=10
**Then** only properties within 10km of the point are returned
**And** results include distance from the query point

#### Scenario: Search with multiple filters combined
**Given** published properties with varying attributes
**When** a user sends GET /api/v1/properties?type=house&rooms_min=3&price_max=500000000&operation=sale
**Then** only houses with 3+ rooms, under 500M COP, for sale are returned

#### Scenario: Search returns only published properties
**Given** properties in draft, published, and sold statuses
**When** an unauthenticated user sends GET /api/v1/properties
**Then** only "published" properties are returned

### Requirement: Property Detail View
**ID**: REQ-INMO-013
**Priority**: HIGH
**Capability**: property-management

The system SHALL provide a detailed property view including all fields, photos, and owner information. The detail endpoint MUST return the full property with associated PropertyPhoto records.

#### Scenario: View property detail with photos
**Given** a published property with 3 uploaded photos
**When** a user sends GET /api/v1/properties/{property_id}
**Then** the response includes all property fields
**And** the response includes an array of photo URLs
**And** the response includes the owner's public profile info

#### Scenario: Detail of non-existent property
**Given** no property with ID "999"
**When** a user sends GET /api/v1/properties/999
**Then** the system returns 404 Not Found

### Requirement: Property Photo Management
**ID**: REQ-INMO-014
**Priority**: HIGH
**Capability**: property-management

The system SHALL allow property owners to upload and manage photos. Photos MUST be stored in S3-compatible storage. Each property MAY have up to 20 photos. The system SHALL generate thumbnails for each uploaded photo.

#### Scenario: Owner uploads property photos
**Given** an authenticated seller with a draft property
**When** the seller POSTs /api/v1/properties/{id}/photos with image files
**Then** photos are uploaded to S3
**And** PropertyPhoto records are created with S3 URLs
**And** thumbnails are generated

#### Scenario: Photo upload exceeds limit
**Given** a property already has 20 photos
**When** the owner attempts to upload another photo
**Then** the system returns 400 Bad Request
**And** no new photo is stored

### Requirement: Property Edit and Delete
**ID**: REQ-INMO-015
**Priority**: HIGH
**Capability**: property-management

The system SHALL allow property owners to edit and delete their own properties. Deletion of a "published" property MUST require confirmation. Deleted properties are soft-deleted (is_active = false).

#### Scenario: Owner edits property details
**Given** a draft property owned by the seller
**When** the seller PATCHes /api/v1/properties/{id} with updated price
**Then** the price is updated
**And** the response returns the updated property

#### Scenario: Owner deletes own property
**Given** a draft property owned by the seller
**When** the seller DELETEs /api/v1/properties/{id}
**Then** the property is soft-deleted (is_active = false)
**And** the property no longer appears in search results

### Requirement: Admin Property Moderation
**ID**: REQ-INMO-016
**Priority**: HIGH
**Capability**: property-management

The system SHALL allow admins to approve or reject published property listings. Rejected properties MUST revert to "draft" status with a rejection reason.

#### Scenario: Admin approves a property
**Given** a property in "published" status
**When** an admin POSTs /api/v1/admin/properties/{id}/approve
**Then** the property status remains "published"
**And** an approved_at timestamp is recorded

#### Scenario: Admin rejects a property
**Given** a property in "published" status
**When** an admin POSTs /api/v1/admin/properties/{id}/reject with reason "Incomplete information"
**Then** the property status reverts to "draft"
**And** the rejection reason is stored
**And** the owner is notified
