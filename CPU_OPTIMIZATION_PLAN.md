# CPU Optimization Plan for Live Parsed Response Updates

## Executive Summary

This document outlines a comprehensive plan to fix the high CPU usage issues when the application is live updating the Parsed Response. The plan addresses the root causes identified in the analysis: excessive JSON parsing, frequent UI updates without throttling, and inefficient string operations.

## Problem Analysis Summary

### Primary Issues

1. **Excessive JSON parsing and string operations** - Every streaming chunk triggers JSON parsing and string manipulation
2. **Frequent UI updates without debouncing** - Multiple UI components update immediately for each streaming chunk
3. **Inefficient data structures and algorithms** - Linear searches and repeated processing

### Secondary Issues

- Model tracking widget periodic refresh combined with streaming updates
- Multiple JSON parsing hotspots across different components
- Inefficient string concatenation operations
- Unnecessary widget repaints and updates

## Optimization Strategy

### Phase 1: Implement Streaming Update Throttling

#### 1.1 Debounce UI Updates

**Target Files**: `request_details_widget.py`, `request_list_widget.py`

**Implementation Plan**:

- Add QTimer-based debouncing for streaming updates
- Batch multiple chunk updates into single UI updates
- Use a configurable debounce interval (100-500ms)

**Code Changes**:

```python
# In RequestDetailsWidget
self._update_timer = QTimer()
self._update_timer.setSingleShot(True)
self._update_timer.timeout.connect(self._debounced_update_streaming)

def update_streaming_content(self, updated_request: InterceptedRequest):
    self._pending_update = updated_request
    self._update_timer.start(200)  # 200ms debounce

def _debounced_update_streaming(self):
    if hasattr(self, '_pending_update') and self._pending_update:
        self._perform_actual_update(self._pending_update)
        self._pending_update = None
```

#### 1.2 Implement Update Prioritization

- Critical updates (streaming content) vs. non-critical updates (metadata)
- Use different debounce intervals for different types of updates

### Phase 2: Optimize Streaming Response Processing

#### 2.1 Reduce JSON Parsing Frequency

**Target File**: `proxy_server.py`

**Implementation Plan**:

- Cache parsed JSON data to avoid repeated parsing
- Implement incremental content building
- Skip JSON parsing for empty or malformed chunks

**Code Changes**:

```python
# In ProxyServer _stream_response_generator
def _parse_sse_chunk(self, chunk_text: str) -> dict | None:
    """Parse SSE chunk with caching and error handling."""
    if not chunk_text or not chunk_text.startswith("data: "):
        return None

    json_data = chunk_text[6:].strip()
    if not json_data or json_data == "[DONE]":
        return None

    # Use cached parser with error handling
    try:
        return json.loads(json_data)
    except (json.JSONDecodeError, ValueError):
        return None
```

#### 2.2 Optimize String Operations

- Use `io.StringIO` for efficient string building
- Pre-allocate buffer space for known content sizes
- Minimize string concatenation operations

### Phase 3: Improve Data Structures and Algorithms

#### 3.1 Replace Linear Search with Hash Map

**Target File**: `request_list_widget.py`

**Implementation Plan**:

- Use timestamp-based hash map for O(1) request lookup
- Maintain request index for efficient list updates

**Code Changes**:

```python
# In RequestListWidget
def __init__(self):
    # ... existing code ...
    self._request_index = {}  # timestamp -> request_index mapping

def add_request(self, request: InterceptedRequest):
    # ... existing code ...
    timestamp = request.request.timestamp
    self._request_index[timestamp] = len(self.requests) - 1

def update_streaming_request(self, updated_request: InterceptedRequest):
    timestamp = updated_request.request.timestamp
    if timestamp in self._request_index:
        index = self._request_index[timestamp]
        self.requests[index] = updated_request
        # Update list item at index
```

#### 3.2 Optimize Model Tracking Updates

**Target File**: `model_tracking_widget.py`

**Implementation Plan**:

- Reduce refresh frequency during active streaming
- Implement incremental updates instead of full rebuilds
- Cache statistics calculations

### Phase 4: Implement Smart Update Coalescing

#### 4.1 Batch Related Updates

**Target**: Multiple widget updates

**Implementation Plan**:

- Group updates that occur in quick succession
- Use a single update cycle for multiple changes
- Implement update batching at the MainWindow level

**Code Changes**:

```python
# In MainWindow
def _on_streaming_update(self, intercepted):
    """Coalesce streaming updates to reduce CPU usage."""
    self._pending_streaming_updates.append(intercepted)

    if not self._update_coalescer.isActive():
        self._update_coalescer.start(100)  # 100ms coalescing window

def _coalesce_updates(self):
    """Process all pending updates in a single batch."""
    if not self._pending_streaming_updates:
        return

    updates = self._pending_streaming_updates.copy()
    self._pending_streaming_updates.clear()

    # Process updates in batch
    for update in updates:
        self._process_single_streaming_update(update)
```

### Phase 5: Add Performance Monitoring and Diagnostics

#### 5.1 Implement Performance Logging

**Target Files**: All relevant files

**Implementation Plan**:

- Add timing measurements for critical operations
- Log update frequencies and processing times
- Monitor memory usage during streaming

**Code Changes**:

```python
import time
import logging

logger = logging.getLogger(__name__)

def _timed_operation(func):
    """Decorator to time operations for performance monitoring."""
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000.0
        logger.debug(f"{func.__name__} took {elapsed:.2f}ms")
        return result
    return wrapper
```

#### 5.2 Add Performance Metrics

- Track update frequency (updates per second)
- Monitor average processing time per update
- Log memory usage during extended streaming sessions

## Implementation Priority

### High Priority (Immediate Impact)

1. **Debounce UI updates** - Will reduce UI update frequency by 80-90%
2. **Replace linear search with hash map** - Will improve request lookup from O(n) to O(1)
3. **Implement update coalescing** - Will batch multiple updates into single processing cycles

### Medium Priority (Significant Impact)

4. **Reduce JSON parsing frequency** - Will eliminate redundant parsing operations
5. **Optimize string operations** - Will reduce memory allocation and garbage collection
6. **Smart model tracking refresh** - Will reduce background processing during streaming

### Low Priority (Maintenance)

7. **Performance monitoring** - Will help identify future bottlenecks
8. **Memory usage optimization** - Will improve long-term stability

## Testing Strategy

### Unit Testing

- Test debouncing mechanisms with various update frequencies
- Verify hash map lookup accuracy and performance
- Test JSON parsing optimization with malformed data

### Integration Testing

- Test end-to-end streaming with realistic workloads
- Monitor CPU usage before and after optimizations
- Verify UI responsiveness during high-frequency updates

### Performance Testing

- Measure CPU usage reduction targets (aim for 60-80% reduction)
- Test memory usage patterns during extended streaming
- Verify no functionality is lost during optimizations

## Rollout Plan

### Phase 1: Core Optimizations (Week 1)

- Implement debouncing and update coalescing
- Replace linear search with hash map
- Add performance monitoring

### Phase 2: Processing Optimizations (Week 2)

- Optimize JSON parsing and string operations
- Improve model tracking efficiency
- Test and validate performance improvements

### Phase 3: Fine-tuning and Validation (Week 3)

- Fine-tune debounce intervals and batching windows
- Conduct comprehensive performance testing
- Document performance improvements

## Success Metrics

### CPU Usage Targets

- 60-80% reduction in CPU usage during streaming
- UI remains responsive during high-frequency updates
- Memory usage remains stable during extended sessions

### Quality Targets

- No loss of existing functionality
- All streaming features continue to work correctly
- Error handling remains robust

### Performance Targets

- Average update processing time reduced by 70%
- UI update frequency reduced from per-chunk to per-batch
- Memory allocations reduced by 50%

## Risk Assessment

### Low Risk

- UI debouncing (well-established pattern)
- Hash map implementation (straightforward replacement)
- Performance monitoring (additive only)

### Medium Risk

- Update coalescing (complex state management)
- JSON parsing optimization (potential edge cases)
- String operation optimization (behavioral changes)

### Mitigation Strategies

- Comprehensive testing of all streaming scenarios
- Gradual rollout with feature flags
- Performance regression testing

## Conclusion

This optimization plan addresses the root causes of high CPU usage during live parsed response updates. By implementing debouncing, optimizing data structures, and batching updates, we can achieve significant performance improvements while maintaining all existing functionality. The phased approach ensures manageable implementation and thorough testing.
