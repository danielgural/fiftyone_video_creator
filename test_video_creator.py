#!/usr/bin/env python3
"""
Comprehensive test suite for fiftyone_video_creator plugin.

This test suite verifies that the video creator properly:
1. Creates videos for all sensors in each scene
2. Propagates video_path fields to all samples in each sensor slice
3. Handles existing videos correctly
4. Works with grouped datasets properly
"""

import fiftyone as fo
import fiftyone.operators as foo
import os
import sys
from typing import Dict, List, Set

# Add the plugin directory to the path
sys.path.insert(0, os.path.dirname(__file__))

class VideoCreatorTestSuite:
    def __init__(self, dataset_name: str = "cosmos_search_test"):
        """Initialize the test suite with a dataset."""
        self.dataset_name = dataset_name
        self.dataset = fo.load_dataset(dataset_name)
        self.image_sensors = ['front', 'front_left', 'side_left', 'front_right', 'side_right']
        self.test_results = {}
        
    def print_header(self, title: str):
        """Print a formatted test header."""
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}")
        
    def print_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Print formatted test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        self.test_results[test_name] = passed
        
    def test_dataset_structure(self) -> bool:
        """Test that the dataset has the expected structure."""
        self.print_header("Testing Dataset Structure")
        
        try:
            # Check media type
            is_grouped = self.dataset.media_type == "group"
            self.print_test_result(
                "Dataset is grouped", 
                is_grouped,
                f"Media type: {self.dataset.media_type}"
            )
            
            if not is_grouped:
                return False
                
            # Check group media types
            group_media_types = self.dataset.group_media_types
            expected_sensors = set(self.image_sensors + ['3D'])
            actual_sensors = set(group_media_types.keys())
            
            has_all_sensors = expected_sensors.issubset(actual_sensors)
            self.print_test_result(
                "Has all expected sensor types",
                has_all_sensors,
                f"Expected: {sorted(expected_sensors)}, Got: {sorted(actual_sensors)}"
            )
            
            # Check image sensors
            image_sensors_found = [s for s, t in group_media_types.items() if t == "image"]
            has_image_sensors = len(image_sensors_found) >= 5
            
            self.print_test_result(
                "Has image sensor slices",
                has_image_sensors,
                f"Found image sensors: {sorted(image_sensors_found)}"
            )
            
            # Check total samples
            total_samples = len(self.dataset)
            has_samples = total_samples > 0
            
            self.print_test_result(
                "Has samples",
                has_samples,
                f"Total samples: {total_samples}"
            )
            
            return is_grouped and has_all_sensors and has_image_sensors and has_samples
            
        except Exception as e:
            self.print_test_result("Dataset structure test", False, f"Error: {e}")
            return False
    
    def test_scene_grouping(self) -> bool:
        """Test that scenes are properly grouped."""
        self.print_header("Testing Scene Grouping")
        
        try:
            # Test grouping by clip_id
            grouped_view = self.dataset.group_by('clip_id')
            
            # Count scenes
            scene_count = sum(1 for _ in grouped_view.iter_dynamic_groups())
            has_scenes = scene_count > 0
            
            self.print_test_result(
                "Can group by scene_id",
                has_scenes,
                f"Found {scene_count} scenes"
            )
            
            # Test first scene
            if has_scenes:
                first_scene = next(grouped_view.iter_dynamic_groups())
                scene_id = first_scene.first()['clip_id']
                
                self.print_test_result(
                    "Scene has ID",
                    bool(scene_id),
                    f"Scene ID: {scene_id}"
                )
                
                # Check scene has samples from multiple sensors
                scene_sensors = set()
                for sample in first_scene:
                    if hasattr(sample, 'group') and sample.group:
                        scene_sensors.add(sample.group.name)
                
                has_multiple_sensors = len(scene_sensors) > 1
                self.print_test_result(
                    "Scene contains multiple sensors",
                    has_multiple_sensors,
                    f"Sensors in scene: {sorted(scene_sensors)}"
                )
                
                return has_scenes and bool(scene_id) and has_multiple_sensors
            
            return has_scenes
            
        except Exception as e:
            self.print_test_result("Scene grouping test", False, f"Error: {e}")
            return False
    
    def test_video_path_field_reset(self) -> bool:
        """Test that video_path fields are properly reset."""
        self.print_header("Testing Video Path Field Reset")
        
        try:
            # Check that all video_path fields are empty
            all_empty = True
            
            for sensor in self.image_sensors:
                sensor_view = self.dataset.select_group_slices([sensor])
                samples_with_videos = sensor_view.exists('video_path')
                count = len(samples_with_videos)
                
                self.print_test_result(
                    f"{sensor} sensor has no video paths",
                    count == 0,
                    f"{count}/{len(sensor_view)} samples have video_path"
                )
                
                if count > 0:
                    all_empty = False
            
            return all_empty
            
        except Exception as e:
            self.print_test_result("Video path field reset test", False, f"Error: {e}")
            return False
    
    def test_video_creator_execution(self) -> bool:
        """Test that the video creator can execute successfully."""
        self.print_header("Testing Video Creator Execution")
        
        try:
            # Run the video creator
            result = foo.execute_operator(
                '@fiftyone_video_creator/fiftyone_video_creator/create_video_assets_per_scene',
                dataset=self.dataset,
                params={
                    'scene_id_field': 'clip_id',
                    'timestamp_field': 'timestamp',
                    'fps': 10,
                    'use_generated': False,
                    'target_sensors': [],
                    'video_path_field': 'video_path',
                },
                request_delegation=False  # Run immediately for testing
            )
            
            execution_success = result is not None
            self.print_test_result(
                "Video creator executes successfully",
                execution_success,
                f"Result type: {type(result)}"
            )
            
            return execution_success
            
        except Exception as e:
            self.print_test_result("Video creator execution test", False, f"Error: {e}")
            return False
    
    def test_video_path_propagation(self) -> bool:
        """Test that video paths are propagated to all sensors."""
        self.print_header("Testing Video Path Propagation")
        
        try:
            all_sensors_have_paths = True
            
            for sensor in self.image_sensors:
                sensor_view = self.dataset.select_group_slices([sensor])
                samples_with_videos = sensor_view.exists('video_path')
                count = len(samples_with_videos)
                total = len(sensor_view)
                
                sensor_has_paths = count == total
                all_sensors_have_paths = all_sensors_have_paths and sensor_has_paths
                
                self.print_test_result(
                    f"{sensor} sensor has video paths",
                    sensor_has_paths,
                    f"{count}/{total} samples have video_path"
                )
                
                # Check that paths are valid
                if count > 0:
                    sample = samples_with_videos.first()
                    video_path = sample['video_path']
                    path_exists = os.path.exists(video_path)
                    
                    self.print_test_result(
                        f"{sensor} sensor video files exist",
                        path_exists,
                        f"Path: {video_path}"
                    )
            
            return all_sensors_have_paths
            
        except Exception as e:
            self.print_test_result("Video path propagation test", False, f"Error: {e}")
            return False
    
    def test_scene_coverage(self) -> bool:
        """Test that all scenes have video paths for all sensors."""
        self.print_header("Testing Scene Coverage")
        
        try:
            # Group by scenes
            grouped_view = self.dataset.group_by('clip_id')
            
            all_scenes_covered = True
            scene_results = {}
            
            for scene_view in grouped_view.iter_dynamic_groups():
                scene_id = scene_view.first()['clip_id']
                
                # Check which sensors have video paths in this scene
                scene_sensors = {}
                for sample in scene_view:
                    if hasattr(sample, 'group') and sample.group:
                        sensor_name = sample.group.name
                        if sensor_name not in scene_sensors:
                            scene_sensors[sensor_name] = {'total': 0, 'with_videos': 0}
                        
                        scene_sensors[sensor_name]['total'] += 1
                        if sample.has_field('video_path') and sample['video_path']:
                            scene_sensors[sensor_name]['with_videos'] += 1
                
                # Check if all image sensors have complete coverage
                scene_covered = True
                for sensor in self.image_sensors:
                    if sensor in scene_sensors:
                        sensor_data = scene_sensors[sensor]
                        complete = sensor_data['with_videos'] == sensor_data['total']
                        scene_covered = scene_covered and complete
                        
                        if not complete:
                            print(f"    ❌ {sensor}: {sensor_data['with_videos']}/{sensor_data['total']} samples have video_path")
                
                scene_results[scene_id] = scene_covered
                all_scenes_covered = all_scenes_covered and scene_covered
                
                self.print_test_result(
                    f"Scene {scene_id} has complete coverage",
                    scene_covered,
                    f"Sensors: {list(scene_sensors.keys())}"
                )
            
            return all_scenes_covered
            
        except Exception as e:
            self.print_test_result("Scene coverage test", False, f"Error: {e}")
            return False
    
    def test_video_file_existence(self) -> bool:
        """Test that all video files actually exist on disk."""
        self.print_header("Testing Video File Existence")
        
        try:
            all_files_exist = True
            missing_files = []
            
            for sensor in self.image_sensors:
                sensor_view = self.dataset.select_group_slices([sensor])
                samples_with_videos = sensor_view.exists('video_path')
                
                for sample in samples_with_videos:
                    video_path = sample['video_path']
                    if not os.path.exists(video_path):
                        missing_files.append(video_path)
                        all_files_exist = False
            
            self.print_test_result(
                "All video files exist on disk",
                all_files_exist,
                f"Missing files: {len(missing_files)}"
            )
            
            if missing_files:
                print("    Missing files:")
                for file_path in missing_files[:5]:  # Show first 5
                    print(f"      {file_path}")
                if len(missing_files) > 5:
                    print(f"      ... and {len(missing_files) - 5} more")
            
            return all_files_exist
            
        except Exception as e:
            self.print_test_result("Video file existence test", False, f"Error: {e}")
            return False
    
    def run_all_tests(self) -> Dict[str, bool]:
        """Run all tests and return results."""
        self.print_header("FiftyOne Video Creator Test Suite")
        print(f"Dataset: {self.dataset_name}")
        print(f"Total samples: {len(self.dataset)}")
        print(f"Image sensors: {self.image_sensors}")
        
        # Run tests in order
        tests = [
            self.test_dataset_structure,
            self.test_scene_grouping,
            self.test_video_path_field_reset,
            self.test_video_creator_execution,
            self.test_video_path_propagation,
            self.test_scene_coverage,
            self.test_video_file_existence,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"❌ Test {test.__name__} failed with exception: {e}")
                self.test_results[test.__name__] = False
        
        # Print summary
        self.print_header("Test Results Summary")
        passed = sum(1 for result in self.test_results.values() if result)
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("⚠️  Some tests failed. Check the output above for details.")
        
        return self.test_results


def main():
    """Main test runner."""
    print("🚀 Starting FiftyOne Video Creator Test Suite")
    
    # Initialize test suite
    test_suite = VideoCreatorTestSuite("cosmos_search_test")
    
    # Run all tests
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()