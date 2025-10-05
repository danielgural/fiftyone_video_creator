#!/usr/bin/env python3
"""
Test script to execute the create_video_assets_per_scene operator via FiftyOne SDK.

This script demonstrates how to use the operator programmatically following the
FiftyOne plugin SDK patterns from:
https://docs.voxel51.com/plugins/using_plugins.html#executing-operators-via-sdk
"""

import fiftyone as fo
import fiftyone.operators as foo
import sys
import os
import asyncio

# Add the plugin directory to Python path so we can import our operator
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_operator_via_sdk():
    """Test the create_video_assets_per_scene operator via FiftyOne SDK with delegation."""
    
    print("=== Testing FiftyOne Video Creator Operator via SDK (Delegated) ===\n")
    
    # Load the dataset
    print("1. Loading dataset...")
    try:
        dataset = fo.load_dataset("cosmos_search_test")
        print(f"✅ Successfully loaded dataset: {dataset.name}")
        print(f"   - Samples: {len(dataset)}")
        print(f"   - Media type: {dataset.media_type}")
        print(f"   - Fields: {list(dataset.get_field_schema().keys())}")
    except Exception as e:
        print(f"❌ Failed to load dataset: {e}")
        return False
    
    # Use the full dataset for delegated execution
    test_view = dataset  # Use full dataset since we're delegating
    print(f"\n2. Using full dataset with {len(test_view)} samples for delegated execution")
    
    # Prepare the context for the operator
    print("\n3. Preparing operator context...")
    ctx = {
        "dataset": dataset,  # Pass the dataset, not the view
        "view": test_view,
        "params": dict(
            scene_id_field="clip_id",
            timestamp_field="timestamp", 
            fps=10,
            use_generated=False,
            target_sensors=None,  # None means use all camera sensors
            video_path_field="video_path"
        )
    }
    
    print("   Context parameters:")
    for key, value in ctx["params"].items():
        print(f"   - {key}: {value}")
    
    # Execute the operator with delegation
    print("\n4. Executing operator via SDK with delegation...")
    try:
        # Execute with delegation (this submits to queue but doesn't wait)
        result = await foo.execute_operator(
            "@fiftyone_video_creator/fiftyone_video_creator/create_video_assets_per_scene", 
            ctx,
            request_delegation=True
        )
        print("✅ Delegated operation submitted successfully!")
        
        # Get operation ID for polling
        operation_id = None
        if hasattr(result, 'id'):
            operation_id = result.id
            print(f"   Operation ID: {operation_id}")
        elif hasattr(result, 'result') and result.result and 'id' in result.result:
            operation_id = result.result['id']
            print(f"   Operation ID: {operation_id}")
        
        if operation_id:
            # Wait for the operation to complete
            success = wait_for_delegated_operation(operation_id)
            if success:
                print("\n5. Operation completed successfully!")
                return True
            else:
                print("\n❌ Operation failed or timed out")
                return False
        else:
            print("❌ Could not get operation ID for polling")
            return False
            
    except Exception as e:
        print(f"❌ Failed to submit delegated operation: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_operator_with_delegation():
    """Test the operator with delegation (background execution)."""
    
    print("\n=== Testing Operator with Delegation ===\n")
    
    # Load dataset
    dataset = fo.load_dataset("cosmos_search_test")
    test_view = dataset.take(20)  # Even smaller subset for delegation test
    
    # Prepare context
    ctx = {
        "view": test_view,
        "params": dict(
            scene_id_field="clip_id",
            timestamp_field="timestamp",
            fps=10,
            use_generated=False,
            target_sensors=None,
            video_path_field="video_path"
        )
    }
    
    print("Executing operator with delegation...")
    try:
        result = foo.execute_operator(
            "@fiftyone_video_creator/fiftyone_video_creator/create_video_assets_per_scene", 
            ctx,
            request_delegation=True
        )
        print("✅ Delegated operation submitted successfully!")
        print(f"   Operation ID: {result.id if hasattr(result, 'id') else 'N/A'}")
        return True
    except Exception as e:
        print(f"❌ Failed to submit delegated operation: {e}")
        import traceback
        traceback.print_exc()
        return False

def wait_for_delegated_operation(operation_id, check_interval=10, max_wait_time=1800):
    """Wait for a delegated operation to complete."""
    import time
    import subprocess
    
    print(f"\n=== Waiting for Operation {operation_id} to Complete ===")
    print(f"Checking every {check_interval} seconds, max wait time: {max_wait_time} seconds")
    
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            # Check operation status
            result = subprocess.run(
                ["fiftyone", "delegated", "info", operation_id],
                capture_output=True,
                text=True,
                cwd="/home/dangural/development/av_dataset_checklist"
            )
            
            if result.returncode == 0:
                output = result.stdout
                if "State: COMPLETED" in output:
                    print(f"✅ Operation {operation_id} completed successfully!")
                    return True
                elif "State: FAILED" in output:
                    print(f"❌ Operation {operation_id} failed!")
                    print("Error details:")
                    print(output)
                    return False
                else:
                    elapsed = int(time.time() - start_time)
                    print(f"⏳ Operation {operation_id} still running... (elapsed: {elapsed}s)")
                    time.sleep(check_interval)
            else:
                print(f"Error checking operation status: {result.stderr}")
                time.sleep(check_interval)
                
        except Exception as e:
            print(f"Exception while checking operation: {e}")
            time.sleep(check_interval)
    
    print(f"⏰ Timeout: Operation {operation_id} did not complete within {max_wait_time} seconds")
    return False

def check_delegated_operations():
    """Check the status of delegated operations."""
    print("\n=== Checking Delegated Operations Status ===\n")
    
    try:
        # Use subprocess to run fiftyone delegated list
        import subprocess
        result = subprocess.run(
            ["fiftyone", "delegated", "list", "--limit", "5"],
            capture_output=True,
            text=True,
            cwd="/home/dangural/development/av_dataset_checklist"
        )
        
        if result.returncode == 0:
            print("Recent delegated operations:")
            print(result.stdout)
        else:
            print(f"Error checking operations: {result.stderr}")
            
    except Exception as e:
        print(f"Failed to check operations: {e}")

def verify_results():
    """Verify that videos were created and samples updated."""
    print("\n=== Verifying Results ===\n")
    
    try:
        dataset = fo.load_dataset("cosmos_search_test")
        
        # Check how many samples now have video_path field
        samples_with_videos = dataset.exists("video_path")
        print(f"Samples with video_path field: {len(samples_with_videos)}")
        
        if len(samples_with_videos) > 0:
            print("\nSample video paths:")
            for i, sample in enumerate(samples_with_videos.head(5)):
                video_path = sample.get_field("video_path")
                print(f"  {i+1}. {video_path}")
                # Check if file exists
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path)
                    print(f"     ✅ File exists ({file_size} bytes)")
                else:
                    print(f"     ❌ File not found")
            
            print(f"\n🎉 Verification successful!")
            print(f"   - {len(samples_with_videos)} samples have video_path field")
            return True
        else:
            print("❌ No samples have video_path field - operation may still be running")
            return False
            
    except Exception as e:
        print(f"❌ Failed to verify results: {e}")
        return False

async def main():
    """Main test function."""
    print("FiftyOne Video Creator Operator SDK Test")
    print("=" * 50)
    
    # Test 1: Delegated execution with await
    success1 = await test_operator_via_sdk()
    
    if success1:
        print("\n" + "=" * 50)
        verify_results()
    else:
        print("\n❌ Delegated execution failed")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
