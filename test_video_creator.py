#!/usr/bin/env python3
"""
Test script for the FiftyOne Video Creator Plugin.

This script tests the video creation functionality with the cosmos_search_test dataset.
"""

import sys
import os
import fiftyone as fo

# Add the plugin directory to the path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)

# Import the plugin functions
from __init__ import get_frame_paths, create_video_from_frames, _process_grouped_dataset


def test_with_cosmos_search_test():
    """Test the video creation functionality with the cosmos_search_test dataset."""
    
    print("=== Testing FiftyOne Video Creator Plugin ===")
    
    # Load the dataset
    dataset_name = "cosmos_search_test"
    print(f"Loading dataset: {dataset_name}")
    
    try:
        dataset = fo.load_dataset(dataset_name)
        print(f"✅ Successfully loaded dataset: {dataset.name}")
        print(f"Dataset info:")
        print(f"- Samples: {len(dataset)}")
        print(f"- Media type: {dataset.media_type}")
        print(f"- Group field: {dataset.group_field}")
        print(f"- Fields: {list(dataset.get_field_schema().keys())}")
        
        if dataset.media_type == "group":
            print(f"- Group media types: {dataset.group_media_types}")
            print(f"- Available sensors: {list(dataset.group_media_types.keys())}")
        
    except Exception as e:
        print(f"❌ Error loading dataset: {e}")
        print("Please make sure the dataset 'cosmos_search_test' exists in FiftyOne")
        return False
    
    # Test the core functions
    print(f"\n=== Testing Core Functions ===")
    
    # Test scene grouping - use clip_id as the scene identifier
    scene_group_view = dataset.group_by("clip_id", order_by="timestamp")
    print(f"Created scene grouped view with {len(scene_group_view)} scenes")
    print(f"Is dynamic groups: {scene_group_view._is_dynamic_groups}")
    
    if scene_group_view._is_dynamic_groups:
        print("Using iter_dynamic_groups() for dynamic group view:")
        scene_count = 0
        for scene in scene_group_view.iter_dynamic_groups():
            scene_count += 1
            if scene_count > 1:  # Just test first scene
                break
                
            scene_id = scene.first()["clip_id"]
            print(f"\n📹 Testing scene: {scene_id}")
            print(f"  - Frames in scene: {len(scene)}")
            
            # Check sensors in this scene
            sensors = scene.group_media_types
            print(f"  - Available sensors: {sensors}")
            
            # Test get_frame_paths function
            print(f"  - Testing get_frame_paths function:")
            frames_dict = get_frame_paths(scene, use_generated=False)
            print(f"  - Found frame sequences for {len(frames_dict)} sensors")
            
            for sensor_name, frame_paths in frames_dict.items():
                print(f"    ✅ {sensor_name}: {len(frame_paths)} frames")
                if len(frame_paths) > 0:
                    print(f"      First frame: {os.path.basename(frame_paths[0])}")
                    print(f"      Last frame: {os.path.basename(frame_paths[-1])}")
            
            # Test video creation for first sensor
            if frames_dict:
                sensor_name = list(frames_dict.keys())[0]
                frame_paths = frames_dict[sensor_name]
                
                print(f"\n  🎬 Testing video creation for sensor: {sensor_name}")
                
                # Create output video path
                scene.group_slice = sensor_name
                sample = scene.first()
                sample_dir = os.path.dirname(sample.filepath)
                output_video = os.path.join(sample_dir, f"test_scene_{scene_id}_{sensor_name}_generated.mp4")
                
                print(f"    Creating video: {os.path.basename(output_video)}")
                
                # Test video creation
                success = create_video_from_frames(frame_paths, output_video, fps=30)
                
                if success:
                    print(f"    ✅ Video created successfully!")
                    print(f"       File size: {os.path.getsize(output_video)} bytes")
                    print(f"       File exists: {os.path.exists(output_video)}")
                else:
                    print(f"    ❌ Video creation failed!")
    
    # Test the full processing function
    print(f"\n=== Testing Full Processing Function ===")
    
    try:
        results = _process_grouped_dataset(
            dataset,
            scene_id_field="clip_id",
            timestamp_field="timestamp",
            fps=30,
            use_generated=False,
            target_sensors=["front"],  # Just test front camera
            video_path_field="video_path"
        )
        
        print(f"✅ Full processing completed successfully!")
        print(f"Results: {results}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in full processing: {e}")
        return False


def test_operator_execution():
    """Test the operator execution directly."""
    
    print(f"\n=== Testing Operator Execution ===")
    
    try:
        # Load the dataset
        dataset = fo.load_dataset("cosmos_search_test")
        
        # Import the operator
        from __init__ import CreateVideoAssetsPerScene
        
        # Create operator instance
        operator = CreateVideoAssetsPerScene()
        
        # Create a mock context
        class MockContext:
            def __init__(self, dataset):
                self.dataset = dataset
                self.params = {
                    "scene_id_field": "scene_id",
                    "timestamp_field": "timestamp",
                    "fps": 30,
                    "use_generated": False,
                    "target_sensors": ["front"],
                    "video_path_field": "video_path"
                }
        
        ctx = MockContext(dataset)
        
        # Update parameters to use correct field names
        ctx.params.update({
            "scene_id_field": "clip_id",
            "timestamp_field": "timestamp",
            "fps": 30,
            "use_generated": False,
            "target_sensors": ["front"],
            "video_path_field": "video_path"
        })
        
        # Execute the operator
        print("Executing operator...")
        results = operator.execute(ctx)
        
        print(f"✅ Operator execution completed successfully!")
        print(f"Results: {results}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in operator execution: {e}")
        return False


if __name__ == "__main__":
    print("Starting FiftyOne Video Creator Plugin Tests...")
    
    # Test core functionality
    core_success = test_with_cosmos_search_test()
    
    # Test operator execution
    operator_success = test_operator_execution()
    
    print(f"\n=== Test Results ===")
    print(f"Core functionality: {'✅ PASSED' if core_success else '❌ FAILED'}")
    print(f"Operator execution: {'✅ PASSED' if operator_success else '❌ FAILED'}")
    
    if core_success and operator_success:
        print(f"\n🎉 All tests passed! The plugin is working correctly.")
        sys.exit(0)
    else:
        print(f"\n❌ Some tests failed. Check the output above.")
        sys.exit(1)
