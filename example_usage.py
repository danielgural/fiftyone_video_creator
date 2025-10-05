#!/usr/bin/env python3
"""
Example usage of the FiftyOne Video Creator Plugin.

This script demonstrates how to use the plugin programmatically.
"""

import fiftyone as fo
from reset_videos import reset_dataset_videos


def example_usage():
    """Example of how to use the video creator plugin."""
    
    print("=== FiftyOne Video Creator Plugin - Example Usage ===")
    
    # Example dataset name
    dataset_name = "cosmos_search_test"
    
    print(f"\n1. Loading dataset: {dataset_name}")
    try:
        dataset = fo.load_dataset(dataset_name)
        print(f"✅ Dataset loaded: {len(dataset)} samples")
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        return
    
    print(f"\n2. Running video creation operator")
    try:
        # Execute the video creator operator
        results = fo.execute_operator(
            "@danielgural/fiftyone_video_creator/create_video_assets_per_scene",
            params={
                "scene_id_field": "clip_id",
                "timestamp_field": "timestamp",
                "fps": 30,
                "use_generated": False,
                "target_sensors": ["front"],  # Just front camera for demo
                "video_path_field": "video_path"
            }
        )
        
        print(f"✅ Video creation completed!")
        print(f"- Processed {results['total_scenes_processed']} scenes")
        print(f"- Created {results['total_videos_created']} videos")
        print(f"- Updated {results['total_samples_updated']} samples")
        
    except Exception as e:
        print(f"❌ Error creating videos: {e}")
        return
    
    print(f"\n3. Checking results")
    # Count samples with video_path
    samples_with_videos = dataset.count("video_path")
    print(f"- Samples with video_path: {samples_with_videos}")
    
    print(f"\n4. Example: Reset videos (dry run)")
    # Show what reset would do
    reset_results = reset_dataset_videos(
        dataset_name=dataset_name,
        video_field_name="video_path",
        delete_videos=True,
        dry_run=True  # Just show what would happen
    )
    
    if not reset_results.get("error"):
        print(f"- Would delete {reset_results['video_files_found']} video files")
        print(f"- Would remove field from {reset_results['samples_with_videos']} samples")
    
    print(f"\n5. To actually reset videos, run:")
    print(f"   python reset_videos.py {dataset_name}")
    print(f"   # or with custom options:")
    print(f"   python reset_videos.py {dataset_name} --field video_path --keep-videos")
    print(f"   python reset_videos.py {dataset_name} --dry-run")


def example_direct_function_usage():
    """Example of using the plugin functions directly."""
    
    print(f"\n=== Direct Function Usage Example ===")
    
    try:
        # Import the plugin functions
        from __init__ import get_frame_paths, create_video_from_frames
        
        # Load dataset
        dataset = fo.load_dataset("cosmos_search_test")
        
        # Group by scene
        scene_group_view = dataset.group_by("clip_id", order_by="timestamp")
        
        # Get first scene
        first_scene = next(scene_group_view.iter_dynamic_groups())
        
        print(f"Processing first scene: {first_scene.first()['clip_id']}")
        
        # Extract frame paths
        frames_dict = get_frame_paths(first_scene, use_generated=False, target_sensors=["front"])
        
        if frames_dict:
            sensor_name = list(frames_dict.keys())[0]
            frame_paths = frames_dict[sensor_name]
            
            print(f"Found {len(frame_paths)} frames for {sensor_name}")
            
            # Create video
            output_path = "/tmp/example_video.mp4"
            success = create_video_from_frames(frame_paths, output_path, fps=30)
            
            if success:
                print(f"✅ Created video: {output_path}")
                # Clean up
                import os
                if os.path.exists(output_path):
                    os.remove(output_path)
                    print(f"Cleaned up temporary video")
            else:
                print(f"❌ Failed to create video")
        else:
            print(f"❌ No frames found")
            
    except Exception as e:
        print(f"❌ Error in direct usage example: {e}")


if __name__ == "__main__":
    example_usage()
    example_direct_function_usage()
