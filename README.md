# FiftyOne Video Creator Plugin

This plugin provides functionality to create video assets from grouped datasets by stitching together frame sequences per scene and sensor.

## Features

- **Scene-based processing**: Processes entire scenes at once, following the correct FiftyOne grouped dataset pattern
- **Sensor filtering**: Can specify exactly which sensors to process (e.g., `["front", "front_left"]`)
- **Generated image support**: Can handle both original and generated images
- **Flexible field mapping**: Configurable scene ID and timestamp field names
- **Video path storage**: Automatically updates samples with video path information

## Installation

### Prerequisites

1. Install FiftyOne (if you haven't already):
   ```shell
   pip install fiftyone
   ```

2. Ensure `ffmpeg` is installed on your system:
   ```shell
   # Ubuntu/Debian
   sudo apt-get install ffmpeg

   # macOS
   brew install ffmpeg

   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

### Install the Plugin

Install the plugin directly from GitHub:

```shell
fiftyone plugins download https://github.com/danielgural/fiftyone_video_creator
```

The plugin will be automatically loaded by FiftyOne.

## Usage

### Using the Operator

The plugin provides a `create_video_assets_per_scene` operator that can be used in the FiftyOne App or programmatically.

#### Parameters

- **Scene ID Field**: Field name containing scene IDs (default: "scene_id")
- **Timestamp Field**: Field name containing timestamps (default: "timestamp") 
- **Video FPS**: Frames per second for output videos (default: 30)
- **Use Generated Images**: Whether to use generated images if available (default: False)
- **Target Sensors**: List of sensor names to process (leave empty for all camera sensors)
- **Video Path Field Name**: Field name to store video paths (default: "video_path")

#### Example Usage

```python
import fiftyone as fo

# Load your dataset
dataset = fo.load_dataset("your_grouped_dataset")

# Run the operator
results = fo.execute_operator(
    "@danielgural/fiftyone_video_creator/create_video_assets_per_scene",
    params={
        "scene_id_field": "scene_id",
        "timestamp_field": "timestamp", 
        "fps": 30,
        "use_generated": False,
        "target_sensors": ["front", "front_left"],
        "video_path_field": "video_path"
    }
)

print(f"Created {results['total_videos_created']} videos")
```

### Using the Functions Directly

You can also use the core functions directly in your code:

```python
from fiftyone_video_creator import get_frame_paths, create_video_from_frames

# Get frame paths for a scene
frames_dict = get_frame_paths(scene, use_generated=False, target_sensors=["front"])

# Create a video from frame paths
success = create_video_from_frames(frame_paths, output_path, fps=30)
```

## Video Storage

Videos are stored in the same directory as the original frame images with the naming pattern:
```
{sample_directory}/scene_{scene_id}_{sensor_name}_generated.mp4
```

## Requirements

- FiftyOne
- ffmpeg (must be installed and available in PATH)
- Python 3.7+

## Reset Videos

The plugin includes a reset script to clean up video fields and files:

```bash
# Reset videos (removes field and deletes files)
python reset_videos.py your_dataset_name

# Dry run (see what would be done without making changes)
python reset_videos.py your_dataset_name --dry-run

# Keep video files, only remove field from dataset
python reset_videos.py your_dataset_name --keep-videos

# Use custom field name
python reset_videos.py your_dataset_name --field custom_video_path
```

### Reset Script Options

- `dataset_name`: Name of the FiftyOne dataset (required)
- `--field`: Video field name to remove (default: "video_path")
- `--keep-videos`: Keep video files, only remove field from dataset
- `--dry-run`: Show what would be done without making changes

### Programmatic Reset

```python
from reset_videos import reset_dataset_videos

# Reset with file deletion
results = reset_dataset_videos("your_dataset", delete_videos=True)

# Reset keeping files
results = reset_dataset_videos("your_dataset", delete_videos=False)

# Dry run
results = reset_dataset_videos("your_dataset", dry_run=True)
```

## License

Apache 2.0