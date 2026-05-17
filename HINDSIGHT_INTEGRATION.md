# Hindsight Client Integration - Implementation Summary

## Overview
This document describes the integration of the Hindsight client into the Vector Space Ablation Engine for tracking ablation history and preventing overlapping concept deletions.

## Changes Made

### 1. backend/ablation.py

#### Removed
- `_ablation_metadata` dictionary (in-memory storage)

#### Added
- **Hindsight client imports** with graceful fallback if not installed
- **`_hindsight_client`** global variable for the Hindsight memory client
- **`HINDSIGHT_BANK_ID`** constant set to "vsae-bank"
- **`initialize_hindsight()`** function to initialize the Hindsight client using `HINDSIGHT_API_KEY` environment variable
- **`check_ablation_overlap(concept, similarity_threshold=0.70)`** function for pre-ablation semantic overlap detection:
  - Uses `client.recall()` to query past ablations
  - Compares semantic embeddings using cosine similarity
  - Returns warning if similarity > 0.70
- **`log_ablation_to_hindsight()`** function to log successful ablations:
  - Uses `client.retain()` to store ablation records
  - Format: "Ablated concept: {concept} at layers {layers} with post_perplexity {perplexity}"
- **Updated `ablate()` function** to accept `concept` and `pre_perplexity` parameters
- **Updated `get_active_ablations()`** to query from Hindsight using `recall()` instead of in-memory storage

### 2. backend/main.py

#### Added
- Import of `initialize_hindsight`, `check_ablation_overlap`, and `log_ablation_to_hindsight` from backend.ablation
- **Startup event handler** to initialize Hindsight on application startup
- **Pre-ablation intercept** in `/ablate` endpoint:
  - Calls `check_ablation_overlap()` before proceeding with ablation
  - Returns warning JSON if overlap detected (similarity > 0.70)
  - Pauses ablation and requires user confirmation
- **Updated ablate() call** to pass `concept` and `pre_perplexity` parameters
- **Post-ablation logging** using `log_ablation_to_hindsight()` to retain ablation in Hindsight memory bank

## Key Features

### 1. Semantic Overlap Detection
When a user requests to forget a concept (e.g., "Harry Potter"), the system:
1. Queries Hindsight using `recall()` with query: "Concepts related to {concept}"
2. Parses recalled ablation records from the results
3. Computes embeddings for both new and past concepts
4. Compares semantic similarity using cosine similarity
5. If similarity > 0.70 with any past ablation, returns a warning

### 2. Warning Payload Format
```json
{
  "status": "warning",
  "message": "Warning: The new concept overlaps 0.71 with historical deletion 'J.K. Rowling'. Stacking these ablations historically degraded perplexity by 18%. Proceed?",
  "past_concept": "J.K. Rowling",
  "similarity": 0.71,
  "historical_perplexity_degradation": 18.0,
  "past_ablation_id": "uuid-here"
}
```

### 3. Ablation History Storage
Each successful ablation is retained in Hindsight using the format:
```
"Ablated concept: {concept} at layers {layers} with post_perplexity {perplexity}"
```

Example:
```
"Ablated concept: Harry Potter at layers 5, 10, 15, 20, 25 with post_perplexity 12.34"
```

This format allows:
- Semantic search via `recall()` to find related concepts
- Easy parsing to extract concept, layers, and perplexity
- Natural language queries for ablation history

## Installation

To use this integration, install the Hindsight client:

```bash
pip install hindsight-client
```

Set the API key as an environment variable:

```bash
export HINDSIGHT_API_KEY="your-api-key-here"
```

The client will automatically use this environment variable on initialization.

## Usage Flow

### Normal Ablation (No Overlap)
1. User requests: `POST /ablate` with `{"forget_text": "Harry Potter"}`
2. System calls `check_ablation_overlap()` which uses `recall()` to query past ablations
3. No overlap found → proceeds with ablation
4. After successful ablation, calls `log_ablation_to_hindsight()` which uses `retain()` to store the record
5. Returns success response with perplexity metrics

### Ablation with Overlap Detected
1. User requests: `POST /ablate` with `{"forget_text": "Hermione Granger"}`
2. System uses `recall()` to query: "Concepts related to Hermione Granger"
3. Finds past ablation of "Harry Potter" in results
4. Computes cosine similarity = 0.85 (> 0.70 threshold)
5. **Pauses ablation** and returns warning JSON
6. User must acknowledge warning and re-submit to proceed

## Benefits

1. **Prevents Model Degradation**: Warns before stacking semantically similar ablations
2. **Historical Context**: Provides perplexity impact data from past similar ablations
3. **Semantic Search**: Uses Hindsight's `recall()` for intelligent overlap detection
4. **Persistent Memory**: Ablation history stored in Hindsight memory bank
5. **Natural Language Storage**: Human-readable ablation records
6. **Graceful Degradation**: Works without Hindsight client (logs warnings)

## Configuration

### Similarity Threshold
Default: `0.70` (70% cosine similarity)

Adjust in the code:
```python
overlap_warning = check_ablation_overlap(
    concept=request.forget_text,
    similarity_threshold=0.70  # Adjust this value
)
```

### Bank ID
Default: `"vsae-bank"`

Change the `HINDSIGHT_BANK_ID` constant in `backend/ablation.py` to use a different memory bank.

## Error Handling

- If Hindsight client is not installed, the system logs warnings but continues operation
- If `HINDSIGHT_API_KEY` is not set, initialization fails gracefully
- If Hindsight initialization fails, overlap detection is disabled
- If `recall()` or `retain()` operations fail, the system logs errors but allows ablation to proceed
- All Hindsight operations are wrapped in try-except blocks for resilience

## Testing

To test the integration:

1. Set environment variable: `export HINDSIGHT_API_KEY="your-key"`
2. Start the server: `uvicorn backend.main:app --reload`
3. Perform first ablation: `POST /ablate` with concept "Harry Potter"
4. Verify ablation is retained in Hindsight (check logs)
5. Perform second ablation: `POST /ablate` with concept "Hermione Granger"
6. Verify warning is returned due to semantic overlap (similarity > 0.70)
7. Check logs for `recall()` and `retain()` operations

## Future Enhancements

- Add user override mechanism to proceed despite warnings
- Implement ablation rollback tracking in Hindsight
- Add analytics dashboard for ablation history
- Support for custom similarity thresholds per request
- Batch ablation overlap checking