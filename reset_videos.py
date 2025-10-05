#!/usr/bin/env python3
"""
Reset script for the FiftyOne Video Creator Plugin.

This script removes video fields from datasets and deletes the corresponding video files.
"""

import sys
import os
import fiftyone as fo
from pathlib import Path


def reset_dataset_videos(dataset_name, video_field_name="video_path", delete_videos=True, dry_run=False):
    """
    Reset video fields and files for a dataset.
    
    Args:
        dataset_name: Name of the FiftyOne dataset
        video_field_name: Name of the video path field to remove (default: "video_path")
        delete_videos: Whether to delete the actual video files (default: True)
        dry_run: If True, only show what would be done without making changes (default: False)
    
    Returns:
        dict: Summary of operations performed
    """
    print(f"=== Resetting Videos for Dataset: {dataset_name} ===")
    
    try:
        # Load the dataset
        dataset = fo.load_dataset(dataset_name)
        print(f"✅ Successfully loaded dataset: {dataset.name}")
        print(f"Dataset info:")
        print(f"- Samples: {len(dataset)}")
        print(f"- Media type: {dataset.media_type}")
        
        # Check if the video field exists
        if video_field_name not in dataset.get_field_schema():
            print(f"❌ Field '{video_field_name}' not found in dataset schema")
            print(f"Available fields: {list(dataset.get_field_schema().keys())}")
            return {"error": f"Field '{video_field_name}' not found"}
        
        print(f"- Video field '{video_field_name}' found in schema")
        
        # Collect video paths and files to delete
        video_files_to_delete = set()
        samples_with_videos = 0
        
        print(f"\n📋 Scanning dataset for video files...")
        
        if dataset.media_type == "group":
            # For grouped datasets, iterate through all samples
            for sample in dataset:
                if sample.has_field(video_field_name):
                    video_path = sample.get_field(video_field_name)
                    if video_path and isinstance(video_path, str) and os.path.exists(video_path):
                        video_files_to_delete.add(video_path)
                        samples_with_videos += 1
                        if not dry_run:
                            print(f"  Found video: {os.path.basename(video_path)}")
        else:
            # For regular datasets
            for sample in dataset:
                if sample.has_field(video_field_name):
                    video_path = sample.get_field(video_field_name)
                    if video_path and isinstance(video_path, str) and os.path.exists(video_path):
                        video_files_to_delete.add(video_path)
                        samples_with_videos += 1
                        if not dry_run:
                            print(f"  Found video: {os.path.basename(video_path)}")
        
        print(f"\n📊 Summary:")
        print(f"- Samples with videos: {samples_with_videos}")
        print(f"- Unique video files: {len(video_files_to_delete)}")
        
        if dry_run:
            print(f"\n🔍 DRY RUN - No changes will be made")
            print(f"Would delete {len(video_files_to_delete)} video files:")
            for video_path in sorted(video_files_to_delete):
                print(f"  - {video_path}")
            print(f"Would remove field '{video_field_name}' from {samples_with_videos} samples")
            return {
                "dry_run": True,
                "samples_with_videos": samples_with_videos,
                "video_files_found": len(video_files_to_delete),
                "videos_to_delete": sorted(video_files_to_delete)
            }
        
        # Delete video files
        deleted_files = 0
        failed_deletions = []
        
        if delete_videos and video_files_to_delete:
            print(f"\n🗑️  Deleting video files...")
            
            for video_path in video_files_to_delete:
                try:
                    if os.path.exists(video_path):
                        os.remove(video_path)
                        deleted_files += 1
                        print(f"  ✅ Deleted: {os.path.basename(video_path)}")
                    else:
                        print(f"  ⚠️  File not found: {video_path}")
                except Exception as e:
                    failed_deletions.append((video_path, str(e)))
                    print(f"  ❌ Failed to delete {os.path.basename(video_path)}: {e}")
        
        # Remove video field from samples
        print(f"\n🧹 Removing video field from dataset...")
        
        samples_updated = 0
        for sample in dataset:
            if sample.has_field(video_field_name):
                sample.clear_field(video_field_name)
                sample.save()
                samples_updated += 1
        
        # Remove field from schema
        dataset.delete_sample_field(video_field_name)
        
        print(f"✅ Removed field '{video_field_name}' from {samples_updated} samples")
        print(f"✅ Removed field '{video_field_name}' from dataset schema")
        
        # Final summary
        print(f"\n🎉 Reset completed successfully!")
        print(f"- Deleted {deleted_files} video files")
        print(f"- Removed field from {samples_updated} samples")
        print(f"- Removed field from dataset schema")
        
        if failed_deletions:
            print(f"\n⚠️  Failed to delete {len(failed_deletions)} files:")
            for video_path, error in failed_deletions:
                print(f"  - {video_path}: {error}")
        
        return {
            "success": True,
            "samples_updated": samples_updated,
            "videos_deleted": deleted_files,
            "failed_deletions": failed_deletions,
            "video_field_removed": True
        }
        
    except Exception as e:
        print(f"❌ Error resetting dataset: {e}")
        return {"error": str(e)}


def main():
    """Main function for command-line usage."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reset video fields and files from FiftyOne datasets")
    parser.add_argument("dataset_name", help="Name of the FiftyOne dataset")
    parser.add_argument("--field", default="video_path", help="Video field name to remove (default: video_path)")
    parser.add_argument("--keep-videos", action="store_true", help="Keep video files, only remove field from dataset")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    # Run the reset
    result = reset_dataset_videos(
        dataset_name=args.dataset_name,
        video_field_name=args.field,
        delete_videos=not args.keep_videos,
        dry_run=args.dry_run
    )
    
    if result.get("error"):
        sys.exit(1)
    elif not result.get("dry_run") and result.get("success"):
        print(f"\n✅ Reset completed successfully!")
        sys.exit(0)
    elif result.get("dry_run"):
        print(f"\n🔍 Dry run completed - no changes made")
        sys.exit(0)
    else:
        print(f"\n❌ Reset failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
