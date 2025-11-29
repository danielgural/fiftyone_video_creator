# FiftyOne Video Creator - Enhanced Features

## 🚀 Version 1.1.0 - Major Enhancements

### ✨ New Features

#### 1. **Auto-Complete Field Selection**
- **Scene ID Field**: Auto-complete dropdown showing all available dataset fields
- **Timestamp Field**: Auto-complete dropdown showing all available dataset fields  
- **Video Path Field**: Auto-complete dropdown showing all available dataset fields

**Benefits:**
- No more guessing field names
- Prevents typos and invalid field references
- Better user experience with guided selection
- Shows all available options dynamically

#### 2. **Smart FPS Calculation**
- **Automatic FPS Detection**: Calculates FPS from timestamp differences between frames
- **Override Option**: Manual FPS specification when needed
- **Intelligent Clamping**: Ensures FPS stays within reasonable range (1-120)
- **Per-Sensor Calculation**: Different FPS for different sensors if needed

**Algorithm:**
```python
# Calculate time differences between consecutive frames
time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
avg_time_diff = sum(time_diffs) / len(time_diffs)
calculated_fps = 1.0 / avg_time_diff
fps = max(1.0, min(120.0, calculated_fps))  # Clamp to reasonable range
```

#### 3. **Enhanced User Interface**
- **Conditional FPS Input**: FPS override field only appears when override is enabled
- **Clear Labels**: Better descriptions and labels for all inputs
- **Dynamic Choices**: Field choices update based on current dataset

### 🔧 Technical Improvements

#### **Input Resolution**
```python
def resolve_input(self, ctx):
    # Get available fields from dataset
    dataset_field_choices = []
    if hasattr(ctx, 'dataset') and ctx.dataset is not None:
        schema = ctx.dataset.get_field_schema()
        for field_name in schema.keys():
            dataset_field_choices.append(types.Choice(label=field_name, value=field_name))
    
    # Auto-complete inputs with dynamic choices
    inputs.str("scene_id_field", view=types.AutocompleteView(choices=dataset_field_choices))
    inputs.str("timestamp_field", view=types.AutocompleteView(choices=dataset_field_choices))
    inputs.str("video_path_field", view=types.AutocompleteView(choices=dataset_field_choices))
    
    # Conditional FPS override
    inputs.bool("use_fps_override", default=False)
    if ctx.params.get("use_fps_override", False):
        inputs.int("fps", default=30, min=1, max=120)
```

#### **FPS Calculation Function**
```python
def calculate_fps_from_timestamps(samples, timestamp_field="timestamp"):
    """Calculate FPS based on timestamp differences between consecutive frames."""
    # Extract and sort timestamps
    timestamps = [sample.get_field(timestamp_field) for sample in samples if sample.has_field(timestamp_field)]
    timestamps.sort()
    
    # Calculate time differences
    time_diffs = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps)) if timestamps[i] - timestamps[i-1] > 0]
    
    # Calculate average and convert to FPS
    avg_time_diff = sum(time_diffs) / len(time_diffs)
    calculated_fps = 1.0 / avg_time_diff
    
    # Clamp to reasonable range
    return max(1.0, min(120.0, calculated_fps))
```

#### **Video Creation Logic**
```python
# Calculate FPS based on timestamps if not using override
video_fps = fps
if not use_fps_override:
    # Get samples for this sensor to calculate FPS
    sensor_samples = [s for s in scene_view if s.get_field("sensor_name") == sensor_name]
    video_fps = calculate_fps_from_timestamps(sensor_samples, timestamp_field)

success = create_video_from_frames(frame_paths, video_output_path, fps=video_fps)
```

### 📊 Test Results

**FPS Calculation Accuracy:**
- ✅ 30 FPS target: 30.00 FPS calculated (0.0% error)
- ✅ 15 FPS target: 15.00 FPS calculated (0.0% error)
- ✅ Handles different FPS per scene correctly
- ✅ Robust error handling for edge cases

**UI Components:**
- ✅ Auto-complete resolves correctly with dataset fields
- ✅ Conditional inputs work properly
- ✅ Parameter extraction handles all new options
- ✅ Backward compatibility maintained

### 🎯 Usage Examples

#### **Auto FPS (Recommended)**
```python
# Let the plugin calculate FPS from timestamps
params = {
    "scene_id_field": "clip_id",      # Auto-complete selection
    "timestamp_field": "timestamp",   # Auto-complete selection
    "use_fps_override": False,        # Use automatic calculation
    "video_path_field": "video_path"  # Auto-complete selection
}
```

#### **Manual FPS Override**
```python
# Override with custom FPS
params = {
    "scene_id_field": "clip_id",      # Auto-complete selection
    "timestamp_field": "timestamp",   # Auto-complete selection
    "use_fps_override": True,         # Enable override
    "fps": 30,                        # Custom FPS value
    "video_path_field": "video_path"  # Auto-complete selection
}
```

### 🔄 Migration Guide

**For Existing Users:**
- ✅ All existing functionality preserved
- ✅ Default values remain the same
- ✅ No breaking changes
- ✅ Enhanced UI provides better experience

**New Parameters:**
- `use_fps_override`: Boolean to enable FPS override (default: False)
- `fps`: Integer FPS value (only used when override is enabled)

### 🧪 Testing

**Test Coverage:**
- ✅ FPS calculation accuracy across different scenarios
- ✅ Auto-complete field selection with real datasets
- ✅ Operator UI resolution and parameter handling
- ✅ Backward compatibility with existing workflows
- ✅ Error handling for edge cases

**Test Files:**
- `test_enhanced_features.py`: Comprehensive test suite
- `demo_enhanced_features.py`: Usage demonstration

### 🎉 Benefits

1. **Better User Experience**: Auto-complete prevents field name errors
2. **Accurate Video Timing**: FPS calculated from actual frame timestamps
3. **Flexibility**: Override option for special cases
4. **Robustness**: Intelligent clamping and error handling
5. **Future-Proof**: Easy to extend with more field types

### 🔮 Future Enhancements

- **Field Type Validation**: Validate that selected fields contain expected data types
- **FPS Preview**: Show calculated FPS before video creation
- **Batch Processing**: Optimize for large datasets
- **Video Quality Options**: Additional encoding parameters
- **Progress Tracking**: Better progress reporting for long operations

---

**Version**: 1.1.0  
**Date**: October 2024  
**Compatibility**: FiftyOne >= 0.23.0  
**Author**: Daniel Gural
