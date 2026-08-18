# Buyer Matching Specification

## Purpose

Define the weighted multi-factor matching engine that scores properties against buyer preferences. Provides explainable score breakdowns, match history, and automatic re-computation triggers.

## Requirements

### Requirement: Buyer Preference Profile
**ID**: REQ-INMO-020
**Priority**: CRITICAL
**Capability**: buyer-matching

The system SHALL store buyer preferences used for matching. Preferences MUST include: budget_min, budget_max (COP), preferred_locations (JSONB array of city names or coordinates), property_types (ENUM array), rooms_min, bathrooms_min, area_min, area_max, features (JSONB array). Preferences are stored in the BuyerProfile and linked to the base User.

#### Scenario: Buyer sets matching preferences
**Given** an authenticated buyer
**When** the buyer PATCHes /api/v1/profiles/buyer/preferences with budget, locations, and features
**Then** the preferences are persisted in BuyerProfile
**And** a match computation is triggered for this buyer

#### Scenario: Buyer preferences are validated
**Given** an authenticated buyer
**When** the buyer submits budget_min > budget_max
**Then** the system returns 400 Bad Request
**And** no preferences are saved

### Requirement: Match Scoring Algorithm
**ID**: REQ-INMO-021
**Priority**: CRITICAL
**Capability**: buyer-matching

The system SHALL compute a match score (0-100) for each property against a buyer's preferences using weighted multi-factor scoring. The formula MUST be: Score = (price_match × 0.30) + (location_match × 0.25) + (features_match × 0.25) + (area_match × 0.20). Each sub-score MUST be normalized to 0-100. The system SHALL store score_breakdown as JSONB showing per-factor contribution.

#### Scenario: Score computation for a matching property
**Given** a buyer with budget 200M-300M COP, prefers Bogotá, wants 3 rooms
**And** a published property at 250M COP in Bogotá with 3 rooms
**When** the matching engine computes the score
**Then** price_match is high (within budget range)
**And** location_match is high (matches preferred location)
**And** features_match reflects room count alignment
**And** the final score is between 70-100

#### Scenario: Score breakdown is explainable
**Given** a computed match with score 75
**When** the buyer requests the match detail
**Then** the response includes score_breakdown with price_match, location_match, features_match, area_match values
**And** each sub-score shows its weighted contribution

#### Scenario: Non-matching property scores low
**Given** a buyer with budget 100M-150M COP
**And** a property priced at 500M COP in a different city
**When** the matching engine computes the score
**Then** price_match is near 0 (far outside budget)
**And** location_match is near 0 (not in preferred area)
**And** the final score is below 30

### Requirement: Match Results and Pagination
**ID**: REQ-INMO-022
**Priority**: CRITICAL
**Capability**: buyer-matching

The system SHALL return match results sorted by score descending with pagination. Only "published" properties SHALL be included in matching. Results MUST include the property summary, match score, and score_breakdown.

#### Scenario: Buyer retrieves match results
**Given** a buyer with saved preferences and matching properties exist
**When** the buyer sends GET /api/v1/matches?page=1&limit=10
**Then** results are sorted by score descending
**And** each result includes property summary, score (0-100), and score_breakdown
**And** results are paginated with metadata

#### Scenario: No matches found
**Given** a buyer with very restrictive preferences
**When** no published properties match the criteria
**Then** the system returns an empty results array
**And** the response includes a suggestion to broaden preferences

### Requirement: Match History
**ID**: REQ-INMO-023
**Priority**: MEDIUM
**Capability**: buyer-matching

The system SHALL store match computation history. Each computation MUST record: computed_at timestamp, buyer_id, number of properties scored, top matches. Buyers MAY view their match history to track how matches change over time.

#### Scenario: Buyer views match history
**Given** a buyer with 3 previous match computations
**When** the buyer sends GET /api/v1/matches/history
**Then** the response lists all past computations with timestamps
**And** each entry shows the number of properties scored and top score

#### Scenario: Match history is paginated
**Given** a buyer with 50 match computations
**When** the buyer requests history with limit=10
**Then** only the 10 most recent computations are returned
**And** pagination metadata indicates more pages exist

### Requirement: Match Re-computation Triggers
**ID**: REQ-INMO-024
**Priority**: HIGH
**Capability**: buyer-matching

The system SHALL re-compute matches when: (a) buyer updates preferences, or (b) a new property is published. Re-computation MUST be async and cached in Redis with key prefix "match:{buyer_id}". The system SHOULD debounce rapid preference changes (within 60 seconds).

#### Scenario: Re-compute on preference change
**Given** a buyer with existing match results
**When** the buyer updates their budget range
**Then** the match cache is invalidated
**And** a new match computation is triggered asynchronously
**And** the next GET /api/v1/matches returns updated results

#### Scenario: Re-compute on new property
**Given** published properties with existing match results for buyers
**When** a seller publishes a new property
**Then** match scores are recomputed for affected buyers
**And** the new property appears in relevant match results

#### Scenario: Debounced preference updates
**Given** a buyer updates preferences at T=0
**When** the buyer updates preferences again at T=30 seconds
**Then** only one match computation is triggered
**And** the second update is merged before computation
