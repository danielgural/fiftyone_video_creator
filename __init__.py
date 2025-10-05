"""
FiftyOne Video Creator Plugin.

This plugin provides functionality to create video assets from grouped datasets
by stitching together frame sequences per scene and sensor.

| Copyright 2025, Daniel Gural
|
"""

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types
import os
import subprocess
import tempfile
from pathlib import Path


def get_frame_paths(scene, use_generated=False, target_sensors=None):
    """
    Extract frame paths from a scene for specified camera sensors.
    
    Args:
        scene: FiftyOne scene group containing sensor samples
        use_generated (bool): Whether to use generated images (default: False)
        target_sensors (list): List of sensor names to process (default: None = all camera sensors)
    
    Returns:
        dict: Dictionary mapping sensor names to lists of frame file paths
    """
    # Get all sensors in the scene and filter for camera sensors only
    scene_sensors = scene.group_media_types
    camera_sensors = [sensor_name for sensor_name, sensor_type in scene_sensors.items() if "image" == sensor_type]
    
    # Filter to target sensors if specified
    if target_sensors is not None:
        camera_sensors = [sensor for sensor in camera_sensors if sensor in target_sensors]
        print(f"  - Filtering to target sensors: {camera_sensors}")
    
    frames_dict = {}
    for sensor_name in camera_sensors:
        print(f"  - Processing sensor: {sensor_name}")
        
        # Set the group slice to the current sensor
        scene.group_slice = sensor_name
        frame_paths = []
        
        # Get the first sample to check metadata
        sample = scene.first()
        
        # Check if we should use generated images
        if "generated" in sample.field_names and sample["generated"] == True and use_generated:
            print(f"    Using generated images for {sensor_name}")
            frame_paths = scene.values("filepath")
        elif "generated" not in sample.field_names or sample["generated"] == False:
            print(f"    Using original images for {sensor_name}")
            frame_paths = scene.values("filepath")
        else:
            print(f"    Skipping sensor: {sensor_name} - generated: {sample['generated']}")
            continue
        
        if len(frame_paths) > 0:
            frames_dict[sensor_name] = frame_paths
            print(f"    Found {len(frame_paths)} frames for {sensor_name}")
        else:
            print(f"    No frames found for {sensor_name}")
        
    return frames_dict


def create_video_from_frames(frame_paths, output_path, fps=30):
    """
    Create a video from a sequence of frame images using ffmpeg.
    
    Args:
        frame_paths: List of paths to frame images (sorted)
        output_path: Path where the output video will be saved
        fps: Frames per second for the output video
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create a temporary file list for ffmpeg
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            for frame_path in frame_paths:
                f.write(f"file '{frame_path}'\n")
            filelist_path = f.name
        
        # Use ffmpeg to create video from image sequence
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', filelist_path,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-r', str(fps),
            '-y',  # Overwrite output file
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Clean up temporary file
        os.unlink(filelist_path)
        
        if result.returncode == 0:
            return True
        else:
            print(f"FFmpeg error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error creating video from frames: {e}")
        return False


class CreateVideoAssetsPerScene(foo.Operator):
    """
    Create video assets from grouped datasets by stitching together frame sequences per scene and sensor.
    """
    
    @property
    def config(self):
        return foo.OperatorConfig(
            name="create_video_assets_per_scene",
            label="Create Video Assets Per Scene",
            description="Create video files from frame sequences in grouped datasets",
            dynamic=True,
            execution_options=foo.ExecutionOptions(
                allow_immediate_execution=False,     # Disable immediate execution
                allow_delegated_execution=True,      # Enable delegated execution
                allow_distributed_execution=True,    # Enable distributed execution
                default_choice_to_delegated=True,    # Default to delegated execution
            ),
        )
    
    def resolve_delegation(self, ctx):
        return True

    def resolve_input(self, ctx):
        inputs = types.Object()
        
        # Scene ID field input
        inputs.str(
            "scene_id_field",
            label="Scene ID Field",
            description="Field name containing scene IDs (default: 'scene_id')",
            default="scene_id",
        )
        
        # Timestamp field input
        inputs.str(
            "timestamp_field", 
            label="Timestamp Field",
            description="Field name containing timestamps (default: 'timestamp')",
            default="timestamp",
        )
        
        # FPS input
        inputs.int(
            "fps",
            label="Video FPS",
            description="Frames per second for output videos",
            default=30,
            min=1,
            max=120,
        )
        
        # Use generated images option
        inputs.bool(
            "use_generated",
            label="Use Generated Images",
            description="Whether to use generated images if available",
            default=False,
        )
        
        # Target sensors input
        inputs.list(
            "target_sensors",
            element_type=types.String(),
            label="Target Sensors",
            description="List of sensor names to process (leave empty for all camera sensors)",
            default=[],
        )
        
        # Video path field name
        inputs.str(
            "video_path_field",
            label="Video Path Field Name",
            description="Field name to store video paths (default: 'video_path')",
            default="video_path",
        )
        
        return types.Property(inputs)

    def execute(self, ctx):
        """Execute the video creation process."""
        # Get parameters
        scene_id_field = ctx.params.get("scene_id_field", "scene_id")
        timestamp_field = ctx.params.get("timestamp_field", "timestamp")
        fps = ctx.params.get("fps", 30)
        use_generated = ctx.params.get("use_generated", False)
        target_sensors = ctx.params.get("target_sensors", [])
        video_path_field = ctx.params.get("video_path_field", "video_path")
        
        # Convert empty list to None for target_sensors
        if not target_sensors:
            target_sensors = None
        
        # Get the dataset view
        dataset = ctx.dataset
        if dataset is None:
            raise ValueError("No dataset found in context")
        
        print(f"Processing dataset: {dataset.name}")
        print(f"Scene ID field: {scene_id_field}")
        print(f"Timestamp field: {timestamp_field}")
        print(f"FPS: {fps}")
        print(f"Use generated: {use_generated}")
        print(f"Target sensors: {target_sensors}")
        print(f"Video path field: {video_path_field}")
        
        # Process the dataset
        results = _process_grouped_dataset(
            dataset,
            scene_id_field=scene_id_field,
            timestamp_field=timestamp_field,
            fps=fps,
            use_generated=use_generated,
            target_sensors=target_sensors,
            video_path_field=video_path_field
        )
        
        return results


def _process_grouped_dataset(dataset, scene_id_field="scene_id", timestamp_field="timestamp", 
                           fps=30, use_generated=False, target_sensors=None, video_path_field="video_path"):
    """
    Process a grouped dataset by scene_id, creating videos for each sensor/camera.
    
    Args:
        dataset: FiftyOne dataset
        scene_id_field: Field name containing scene IDs
        timestamp_field: Field name containing timestamps
        fps: Frames per second for output videos
        use_generated: Whether to use generated images
        target_sensors: List of target sensor names (None for all)
        video_path_field: Field name to store video paths
    
    Returns:
        dict: Results summary
    """
    # Create grouped view by scene_id, ordered by timestamp
    grouped_view = dataset.group_by(scene_id_field, order_by=timestamp_field)
    
    print(f"Found {len(grouped_view)} scene groups")
    print(f"Group view type: {type(grouped_view)}")
    print(f"Is dynamic groups: {grouped_view._is_dynamic_groups}")
    
    # Use the correct iteration method based on group type
    if grouped_view._is_dynamic_groups:
        print("Using iter_dynamic_groups() for dynamic group view")
        group_iterator = grouped_view.iter_dynamic_groups()
    else:
        print("Using iter_groups() for normal group view")
        group_iterator = grouped_view.iter_groups()
    
    total_scenes = 0
    total_videos = 0
    total_samples_updated = 0
    
    for scene_view in group_iterator:
        total_scenes += 1
        
        # Get the scene ID from the first sample
        scene_id = scene_view.first()[scene_id_field]
        print(f"\nProcessing scene group: {scene_id}")
        
        # First, check if videos already exist for this scene before extracting frame paths
        print(f"  - Checking for existing videos...")
        
        # Check if samples already have video_path field set
        samples_with_video = scene_view.exists(video_path_field)
        if len(samples_with_video) > 0:
            print(f"  - Found {len(samples_with_video)} samples with existing video_path field")
            # Get all unique video paths for this scene
            existing_video_paths = set()
            for sample in samples_with_video:
                if sample.has_field(video_path_field) and sample.get_field(video_path_field):
                    existing_video_paths.add(sample.get_field(video_path_field))
            
            if existing_video_paths:
                print(f"  - Scene {scene_id} already has videos: {list(existing_video_paths)}")
                print(f"  - Skipping scene {scene_id} (videos already exist)")
                total_videos += len(existing_video_paths)
                continue
        
        # Check for existing video files on disk
        first_sample = list(scene_view)[0]
        sample_dir = os.path.dirname(first_sample.filepath)
        
        # Get all sensors that might have videos
        all_sensors = set()
        for sample in scene_view:
            if sample.has_field("sensor_name"):
                all_sensors.add(sample.get_field("sensor_name"))
        
        existing_videos_on_disk = []
        for sensor_name in all_sensors:
            video_output_path = os.path.join(sample_dir, f"scene_{scene_id}_{sensor_name}_generated.mp4")
            if os.path.exists(video_output_path):
                existing_videos_on_disk.append((sensor_name, video_output_path))
        
        if existing_videos_on_disk:
            print(f"  - Found {len(existing_videos_on_disk)} existing video files on disk for scene {scene_id}")
            for sensor_name, video_path in existing_videos_on_disk:
                print(f"    * {sensor_name}: {video_path}")
            print(f"  - Skipping scene {scene_id} (videos already exist on disk)")
            total_videos += len(existing_videos_on_disk)
            continue
        
        # If we get here, no videos exist - proceed with frame extraction and video creation
        print(f"  - No existing videos found, proceeding with video creation...")
        
        # Use the get_frame_paths function to extract frame sequences for all camera sensors
        print(f"  - Extracting frame paths using get_frame_paths:")
        frame_sequences = get_frame_paths(scene_view, use_generated=use_generated, target_sensors=target_sensors)
        
        if not frame_sequences:
            print(f"No frame sequences found for scene {scene_id}, skipping...")
            continue
        
        # Create videos for each sensor that has frames
        sensor_video_paths = {}
        for sensor_name, frame_paths in frame_sequences.items():
            if not frame_paths:
                continue
                
            # Generate output path for this sensor's video
            video_output_path = os.path.join(sample_dir, f"scene_{scene_id}_{sensor_name}_generated.mp4")
            
            # Double-check if video was created between our check and now
            if os.path.exists(video_output_path):
                print(f"Video already exists for scene {scene_id}, sensor {sensor_name}: {video_output_path}")
                sensor_video_paths[sensor_name] = video_output_path
                total_videos += 1
                continue
            
            print(f"Creating video from {len(frame_paths)} frames for scene {scene_id}, sensor {sensor_name}")
            success = create_video_from_frames(frame_paths, video_output_path, fps=fps)
            
            if success:
                sensor_video_paths[sensor_name] = video_output_path
                total_videos += 1
                print(f"Successfully created video: {video_output_path}")
            else:
                print(f"Failed to create video for scene {scene_id}, sensor {sensor_name}")
        
        # Update video_path field for all samples in this scene group
        samples_updated = 0
        for sample in scene_view:
            sensor_name = sample.get_field("sensor_name") if sample.has_field("sensor_name") else "unknown"
            if sensor_name in sensor_video_paths:
                sample.set_field(video_path_field, sensor_video_paths[sensor_name])
                sample.save()
                samples_updated += 1
        
        total_samples_updated += samples_updated
        print(f"Updated {video_path_field} field for {samples_updated} samples in scene {scene_id}")
    
    results = {
        "total_scenes_processed": total_scenes,
        "total_videos_created": total_videos,
        "total_samples_updated": total_samples_updated,
        "scene_id_field": scene_id_field,
        "timestamp_field": timestamp_field,
        "fps": fps,
        "use_generated": use_generated,
        "target_sensors": target_sensors,
        "video_path_field": video_path_field,
    }
    
    print(f"\n🎉 Video creation completed!")
    print(f"  - Processed {total_scenes} scenes")
    print(f"  - Created {total_videos} videos")
    print(f"  - Updated {total_samples_updated} samples")
    
    return results


def register(p):
    """Register the plugin operators."""
    p.register(CreateVideoAssetsPerScene)
