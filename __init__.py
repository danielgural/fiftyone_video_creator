"""
FiftyOne Video Creator Plugin.

This plugin provides functionality to create video assets from grouped datasets
by stitching together frame sequences per scene and sensor.

| Copyright 2025, Daniel Gural
|
"""

import os
import subprocess
import tempfile
from pathlib import Path
import math
from statistics import median
from datetime import datetime

import fiftyone as fo
import fiftyone.operators as foo
import fiftyone.operators.types as types


# ------------------------------
# Frame extraction
# ------------------------------
def get_frame_paths(scene_view, use_generated=False, target_sensors=None, dataset=None):
    """
    Extract frame paths from a scene for specified camera sensors without
    mutating global state (no group_slice changes).

    Args:
        scene_view: FiftyOne view for a single scene (dynamic group)
        use_generated (bool): Whether to prefer generated images if flagged
        target_sensors (list[str] | None): Subset of sensors to include
        dataset: Original dataset to get group_media_types from

    Returns:
        dict[str, list[str]]: {sensor_name: [frame_filepaths]}
    """
    # Discover sensors in this scene; keep camera slices only
    # Use dataset group_media_types if scene_view doesn't have it
    if dataset is not None:
        scene_sensors = dataset.group_media_types
    else:
        scene_sensors = getattr(scene_view, "group_media_types", {})
        if scene_sensors is None:
            scene_sensors = {}
    
    camera_sensors = [n for n, t in scene_sensors.items() if t == "image"]

    if target_sensors:
        camera_sensors = [s for s in camera_sensors if s in target_sensors]
        print(f"  - Filtering to target sensors: {camera_sensors}")

    frames_dict = {}

    for sensor_name in camera_sensors:
        print(f"  - Processing sensor: {sensor_name}")
        # Filter samples by group name directly since scene_view doesn't have groups
        sensor_samples = [s for s in scene_view if hasattr(s, 'group') and s.group and s.group.name == sensor_name]

        if not sensor_samples:
            print(f"    No samples found for {sensor_name}")
            continue
            
        first = sensor_samples[0]
        # If you actually store generated frames in a different field,
        # switch `fp_field` here (e.g., "generated_filepath")
        use_gen_flag = ("generated" in first.field_names) and bool(first["generated"])
        using_generated = use_generated and use_gen_flag
        fp_field = "filepath"  # change here if you keep generated in a different field

        frame_paths = [s[fp_field] for s in sensor_samples]

        if frame_paths:
            frames_dict[sensor_name] = frame_paths
            print(
                f"    Found {len(frame_paths)} frames for {sensor_name} "
                f"({'generated' if using_generated else 'original'})"
            )
        else:
            print(f"    No frames found for {sensor_name}")

    return frames_dict


# ------------------------------
# FPS calculation
# ------------------------------
def calculate_fps_from_timestamps(
    samples,
    timestamp_field="timestamp",
    timestamps_in_seconds=None,  # None=auto-detect, True=seconds, False=microseconds
    default_fps=30.0,
    trim_percent=0.10,           # trim 10% of extremes
):
    """
    Calculate FPS from per-frame timestamps.

    Args:
        samples: Iterable of FiftyOne samples (frames)
        timestamp_field: Field name (guaranteed to exist on each sample)
        timestamps_in_seconds: None=auto, True=seconds, False=microseconds
        default_fps: Fallback FPS
        trim_percent: Fraction (0..0.49) to trim from each tail

    Returns:
        float: Estimated FPS
    """
    try:
        ts = []
        for s in samples:
            v = s[timestamp_field]  # direct access; field guaranteed
            if isinstance(v, datetime):
                v = v.timestamp()  # seconds
            v = float(v)
            ts.append(v)

        if len(ts) < 2:
            return default_fps

        ts.sort()
        diffs = [b - a for a, b in zip(ts, ts[1:]) if (b - a) > 0]
        if not diffs:
            return default_fps

        # Unit detection if unspecified
        # - seconds: median diff < 1
        # - milliseconds: 1 <= median diff < 1000
        # - microseconds: median diff >= 1000
        if timestamps_in_seconds is None:
            med = median(diffs)
            if med < 1.0:
                units = "seconds"
                diffs_sec = diffs
            elif med < 1000.0:
                units = "milliseconds"
                diffs_sec = [d / 1_000.0 for d in diffs]
            else:
                units = "microseconds"
                diffs_sec = [d / 1_000_000.0 for d in diffs]
        else:
            if timestamps_in_seconds:
                units = "seconds"
                diffs_sec = diffs
            else:
                units = "microseconds"
                diffs_sec = [d / 1_000_000.0 for d in diffs]

        diffs_sec.sort()
        if 0.0 < trim_percent < 0.49 and len(diffs_sec) > 10:
            k = int(len(diffs_sec) * trim_percent)
            diffs_sec = diffs_sec[k: len(diffs_sec) - k] or diffs_sec

        gap = median(diffs_sec)
        if gap <= 0 or math.isinf(gap) or math.isnan(gap):
            return default_fps

        fps = 1.0 / gap
        fps = max(1.0, min(240.0, fps))

        print(f"📊 Calculated FPS: {fps:.3f} (median Δ={gap:.6f}s, units={units}, n={len(diffs_sec)})")
        return fps

    except Exception as e:
        print(f"⚠️ Failed to calculate FPS from timestamps: {e}")
        return default_fps


# ------------------------------
# Video creation via ffmpeg
# ------------------------------
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
        frame_paths = list(frame_paths)
        if not frame_paths:
            print("FFmpeg: no frame paths")
            return False

        out_dir = os.path.dirname(output_path) or "."
        os.makedirs(out_dir, exist_ok=True)

        # Concat demuxer list; escape single quotes
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for frame_path in frame_paths:
                sp = str(frame_path).replace("'", r"'\''")
                f.write(f"file '{sp}'\n")
            filelist_path = f.name

        # -r before -i controls input frame rate for image sequences when using concat list
        cmd = [
            "ffmpeg",
            "-hide_banner", "-loglevel", "error",
            "-r", str(fps),
            "-f", "concat",
            "-safe", "0",
            "-i", filelist_path,
            "-vsync", "vfr",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-y",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        os.unlink(filelist_path)

        if result.returncode != 0:
            print("FFmpeg error:", (result.stderr or "").strip())
            return False

        return True

    except Exception as e:
        print(f"Error creating video from frames: {e}")
        return False


# ------------------------------
# Operator
# ------------------------------
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
                allow_immediate_execution=True,      # Enable immediate execution for testing
                allow_delegated_execution=True,      # Enable delegated execution
                allow_distributed_execution=True,    # Enable distributed execution
                default_choice_to_delegated=True,    # Default to delegated execution
            ),
        )

    def resolve_delegation(self, ctx):
        # Allow immediate execution for testing
        return False

    def resolve_input(self, ctx):
        inputs = types.Object()

        # Build simple field choices for autocomplete (schema keys only)
        dataset_field_choices = []
        if getattr(ctx, "dataset", None) is not None:
            schema = ctx.dataset.get_field_schema()
            dataset_field_choices = [types.Choice(label=field_name, value=field_name) for field_name in schema.keys()]

        # Scene ID field
        inputs.str(
            "scene_id_field",
            label="Scene ID Field",
            description="Field name containing scene IDs (default: 'scene_id')",
            default="scene_id",
            view=types.AutocompleteView(choices=dataset_field_choices),
        )

        # Timestamp field
        inputs.str(
            "timestamp_field",
            label="Timestamp Field",
            description="Field name containing timestamps (default: 'timestamp')",
            default="timestamp",
            view=types.AutocompleteView(choices=dataset_field_choices),
        )

        # FPS override option + value (always show for simplicity)
        inputs.bool(
            "use_fps_override",
            label="Override FPS",
            description="Override automatic FPS calculation based on timestamps",
            default=False,
        )
        inputs.int(
            "fps",
            label="Video FPS (Override)",
            description="Used only if Override FPS is enabled",
            default=30,
            min=1,
            max=240,
        )

        # Timestamp units option
        inputs.bool(
            "timestamps_in_seconds",
            label="Timestamps in Seconds",
            description="Check if timestamps are in seconds (default assumes microseconds)",
            default=False,
        )

        # Use generated images option
        inputs.bool(
            "use_generated",
            label="Use Generated Images",
            description="Whether to prefer generated images if available",
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
            view=types.AutocompleteView(choices=dataset_field_choices),
        )

        return types.Property(inputs)

    def execute(self, ctx):
        """Execute the video creation process."""
        # Params
        scene_id_field = ctx.params.get("scene_id_field", "scene_id")
        timestamp_field = ctx.params.get("timestamp_field", "timestamp")
        use_fps_override = ctx.params.get("use_fps_override", False)
        fps = ctx.params.get("fps", 30)
        timestamps_in_seconds = ctx.params.get("timestamps_in_seconds", False)
        use_generated = ctx.params.get("use_generated", False)
        target_sensors = ctx.params.get("target_sensors", []) or None
        video_path_field = ctx.params.get("video_path_field", "video_path")

        dataset = ctx.dataset
        if dataset is None:
            raise ValueError("No dataset found in context")

        print(f"Processing dataset: {dataset.name}")
        print(f"Scene ID field: {scene_id_field}")
        print(f"Timestamp field: {timestamp_field}")
        print(f"FPS override: {use_fps_override} ({fps} if True)")
        print(f"Timestamps units: {'seconds' if timestamps_in_seconds else 'microseconds'}")
        print(f"Use generated: {use_generated}")
        print(f"Target sensors: {target_sensors}")
        print(f"Video path field: {video_path_field}")

        results = _process_grouped_dataset(
            dataset=dataset,
            scene_id_field=scene_id_field,
            timestamp_field=timestamp_field,
            fps=fps if use_fps_override else None,
            use_fps_override=use_fps_override,
            timestamps_in_seconds=timestamps_in_seconds,
            use_generated=use_generated,
            target_sensors=target_sensors,
            video_path_field=video_path_field,
        )

        return results


# ------------------------------
# Core processing
# ------------------------------
def _process_grouped_dataset(
    dataset,
    scene_id_field="scene_id",
    timestamp_field="timestamp",
    fps=None,
    use_fps_override=False,
    timestamps_in_seconds=False,
    use_generated=False,
    target_sensors=None,
    video_path_field="video_path",
):
    """
    Process a grouped dataset by scene_id, creating videos for each sensor/camera.

    Returns:
        dict: Results summary
    """
    # Dynamic groups by scene with ordering
    # First select all image sensor slices to ensure all sensors are included
    if dataset.media_type == "group":
        available_media_types = dataset.group_media_types
        image_sensors = [sensor for sensor, media_type in available_media_types.items() if media_type == "image"]
        if image_sensors:
            # Create a view that includes all image sensor slices before grouping
            all_sensors_view = dataset.select_group_slices(image_sensors)
            grouped_view = all_sensors_view.group_by(scene_id_field, order_by=timestamp_field)
        else:
            grouped_view = dataset.group_by(scene_id_field, order_by=timestamp_field)
    else:
        grouped_view = dataset.group_by(scene_id_field, order_by=timestamp_field)

    # Public way to confirm dynamic groups (older FO may not have this; default True)
    is_dyn = getattr(grouped_view, "outputs_dynamic_groups", lambda: True)()
    if not is_dyn:
        raise RuntimeError("Expected a dynamic-groups view from group_by()")

    # Count scene groups for logging
    n_scenes = sum(1 for _ in grouped_view.iter_dynamic_groups())
    print(f"Found {n_scenes} scene groups")

    total_scenes = 0
    total_videos = 0
    total_samples_updated = 0

    for scene_view in grouped_view.iter_dynamic_groups():
        total_scenes += 1

        first = scene_view.first()
        scene_id = first[scene_id_field]
        print(f"\nProcessing scene group: {scene_id}")

        # Extract per-sensor frame sequences
        print("  - Extracting frame paths:")
        frame_sequences = get_frame_paths(
            scene_view, use_generated=use_generated, target_sensors=target_sensors, dataset=dataset
        )
        if not frame_sequences:
            print(f"  - No frame sequences found for scene {scene_id}; skipping")
            continue

        sensor_video_paths = {}

        # Per-sensor processing
        for sensor_name, frame_paths in frame_sequences.items():
            if not frame_paths:
                continue

            # Filter samples by group name directly since scene_view doesn't have groups
            sensor_samples = [s for s in scene_view if hasattr(s, 'group') and s.group and s.group.name == sensor_name]
            
            if not sensor_samples:
                continue

            # (a) Field-level: already annotated with a video path?
            samples_with_videos = [s for s in sensor_samples if s.has_field(video_path_field) and s[video_path_field]]
            if len(samples_with_videos) == len(sensor_samples):
                existing_paths = [s[video_path_field] for s in samples_with_videos]
                if existing_paths:
                    # Use the first path (assume uniform)
                    existing = existing_paths[0]
                    print(f"  - {sensor_name}: video already set in fields → {existing}")
                    sensor_video_paths[sensor_name] = existing
                    continue

            # (b) On-disk check (derive dir from first frame)
            first_frame_dir = os.path.dirname(frame_paths[0])
            video_output_path = os.path.join(
                first_frame_dir, f"scene_{scene_id}_{sensor_name}_generated.mp4"
            )
            if os.path.exists(video_output_path):
                print(f"  - {sensor_name}: found existing on disk → {video_output_path}")
                sensor_video_paths[sensor_name] = video_output_path
                continue

            # FPS
            if use_fps_override and fps is not None:
                video_fps = fps
            else:
                video_fps = calculate_fps_from_timestamps(
                    sensor_samples, timestamp_field, timestamps_in_seconds
                )

            print(f"  - {sensor_name}: creating video @ {video_fps:.3f} fps → {video_output_path}")
            ok = create_video_from_frames(frame_paths, video_output_path, fps=video_fps)
            if ok:
                sensor_video_paths[sensor_name] = video_output_path
                total_videos += 1
                print(f"    ✓ Created {video_output_path}")
            else:
                print(f"    ✗ Failed to create video for {sensor_name}")

        # Write field back per sample for produced sensors
        updated = 0
        for s in scene_view:
            sname = s.group.name  # NOTE: using .name per your environment/version
            if sname in sensor_video_paths:
                s.set_field(video_path_field, sensor_video_paths[sname])
                s.save()
                updated += 1

        total_samples_updated += updated
        print(f"  - Updated {video_path_field} for {updated} samples in scene {scene_id}")

    results = {
        "total_scenes_processed": total_scenes,
        "total_videos_created": total_videos,
        "total_samples_updated": total_samples_updated,
        "scene_id_field": scene_id_field,
        "timestamp_field": timestamp_field,
        "fps": fps,
        "use_fps_override": use_fps_override,
        "use_generated": use_generated,
        "target_sensors": target_sensors,
        "video_path_field": video_path_field,
    }

    print("\n🎉 Video creation completed!")
    print(f"  - Processed {total_scenes} scenes")
    print(f"  - Created {total_videos} videos")
    print(f"  - Updated {total_samples_updated} samples")

    return results


def register(p):
    """Register the plugin operators."""
    p.register(CreateVideoAssetsPerScene)
