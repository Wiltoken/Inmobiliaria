# Inquiries and Contact Specification

## Purpose

Define the buyer-to-seller/agent inquiry flow for property contact. Supports inquiry creation, status tracking, and response management without real-time chat.

## Requirements

### Requirement: Inquiry Creation
**ID**: REQ-INMO-030
**Priority**: CRITICAL
**Capability**: inquiries-contact

The system SHALL allow authenticated buyers to create inquiries about published properties. An inquiry MUST include: from_user (buyer), to_user (property owner: seller/agent), property_id, message, and contact_preference (email, phone, both). The inquiry status starts as "pending".

#### Scenario: Buyer creates an inquiry
**Given** an authenticated buyer and a published property
**When** the buyer POSTs /api/v1/inquiries with property_id, message, and contact_preference
**Then** an inquiry is created with status "pending"
**And** the property owner receives a notification
**And** the response returns the inquiry ID

#### Scenario: Inquiry on own property rejected
**Given** a seller who owns property ID 42
**When** the seller attempts to create an inquiry on property 42
**Then** the system returns 400 Bad Request
**And** no inquiry is created

#### Scenario: Inquiry on non-published property rejected
**Given** a property in "draft" status
**When** a buyer attempts to create an inquiry on that property
**Then** the system returns 400 Bad Request

### Requirement: Inquiry Status Workflow
**ID**: REQ-INMO-031
**Priority**: CRITICAL
**Capability**: inquiries-contact

The system SHALL enforce an inquiry status workflow: pending → responded → closed. Only the property owner (to_user) MAY transition from "pending" to "responded". Either party MAY close an inquiry.

#### Scenario: Seller responds to inquiry
**Given** an inquiry in "pending" status
**When** the property owner POSTs /api/v1/inquiries/{id}/respond with a response message
**Then** the inquiry status becomes "responded"
**And** the response message is stored
**And** the buyer is notified

#### Scenario: Seller declines inquiry
**Given** an inquiry in "pending" status
**When** the property owner POSTs /api/v1/inquiries/{id}/decline with reason
**Then** the inquiry status becomes "closed"
**And** the decline reason is stored
**And** the buyer is notified

#### Scenario: Invalid status transition rejected
**Given** an inquiry in "closed" status
**When** any user attempts to transition to "responded"
**Then** the system returns 400 Bad Request

### Requirement: Inquiry Response
**ID**: REQ-INMO-032
**Priority**: HIGH
**Capability**: inquiries-contact

The system SHALL allow property owners to respond to inquiries with a message and action (accept, decline, request_more_info). Responses MUST be stored and visible to both parties.

#### Scenario: Owner accepts inquiry
**Given** a pending inquiry
**When** the owner responds with action "accept" and a message
**Then** the inquiry status becomes "responded"
**And** the acceptance message is stored
**And** the buyer can view the response

#### Scenario: Owner requests more information
**Given** a pending inquiry
**When** the owner responds with action "request_more_info" and a message
**Then** the inquiry status becomes "responded"
**And** the buyer receives the follow-up request

### Requirement: Buyer Inquiry History
**ID**: REQ-INMO-033
**Priority**: HIGH
**Capability**: inquiries-contact

The system SHALL allow buyers to view all inquiries they have created. Results MUST be paginated and sortable by date or status. Each inquiry entry MUST include property summary, status, and last response.

#### Scenario: Buyer views inquiry history
**Given** a buyer with 5 inquiries across different properties
**When** the buyer sends GET /api/v1/inquiries/mine
**Then** all 5 inquiries are returned with property summaries
**And** each entry shows status, created_at, and last response

#### Scenario: Buyer filters inquiries by status
**Given** a buyer with inquiries in pending, responded, and closed statuses
**When** the buyer sends GET /api/v1/inquiries/mine?status=pending
**Then** only pending inquiries are returned

### Requirement: Inquiry Notifications
**ID**: REQ-INMO-034
**Priority**: MEDIUM
**Capability**: inquiries-contact

The system SHALL notify the property owner when a new inquiry is created. Notifications MUST use the contact method specified in the inquiry (email, phone, or both). The notification SHALL include: buyer name (or anonymized), property title, inquiry message, and a link to respond.

#### Scenario: Email notification on new inquiry
**Given** a seller with email notifications enabled
**When** a buyer creates an inquiry on the seller's property
**Then** an email is sent to the seller with inquiry details
**And** the email includes a link to the inquiry management page

#### Scenario: Notification respects contact preference
**Given** a buyer sets contact_preference to "email"
**When** an inquiry is created
**Then** only email notification is sent
**And** no phone notification is attempted
