#!/usr/bin/env python3
"""
Demo script showing the enhanced features of fiftyone_video_creator:
- Auto-complete field selection
- FPS calculation from timestamps
- FPS override functionality
"""

import fiftyone as fo
import fiftyone.operators as foo


def demo_enhanced_video_creator():
    """Demonstrate the enhanced video creator features"""
    print("🎬 Enhanced FiftyOne Video Creator Demo")
    print("=" * 50)
    
    # Check if the operator is available
    operators = foo.list_operators()
    video_creator_ops = [op for op in operators if 'create_video_assets_per_scene' in op.name]
    
    if not video_creator_ops:
        print("❌ Video creator operator not found. Make sure the plugin is installed.")
        return
    
    print(f"✅ Found operator: {video_creator_ops[0].name}")
    
    # Check if we have a test dataset
    if "cosmos_search_test" in fo.list_datasets():
        dataset = fo.load_dataset("cosmos_search_test")
        print(f"✅ Using existing dataset: {dataset.name}")
        print(f"   - Samples: {len(dataset)}")
        print(f"   - Media type: {dataset.media_type}")
        
        # Show available fields for auto-complete
        schema = dataset.get_field_schema()
        print(f"   - Available fields: {list(schema.keys())}")
        
        print("\n🔧 Enhanced Features:")
        print("1. Auto-complete field selection:")
        print("   - Scene ID Field: Choose from available fields")
        print("   - Timestamp Field: Choose from available fields") 
        print("   - Video Path Field: Choose from available fields")
        
        print("\n2. Smart FPS calculation:")
        print("   - Automatically calculates FPS from timestamp differences")
        print("   - Override option available for manual FPS specification")
        print("   - Clamps to reasonable range (1-120 FPS)")
        
        print("\n3. Usage examples:")
        print("   - Auto FPS: Let the plugin calculate from timestamps")
        print("   - Override FPS: Set custom FPS (e.g., 30, 60)")
        
        print(f"\n💡 To use the operator:")
        print(f"   - Open FiftyOne app: fo.launch_app(dataset)")
        print(f"   - Look for 'Create Video Assets Per Scene' in the operators panel")
        print(f"   - Use auto-complete to select fields from: {list(schema.keys())}")
        
    else:
        print("⚠️ No test dataset found. Create a grouped dataset to see the features.")
        print("   Try: fo.load_dataset('cosmos_search_test') or create a test dataset")
    
    print("\n🎯 Key Benefits:")
    print("✅ No more guessing field names - auto-complete shows available options")
    print("✅ Accurate video timing based on actual frame timestamps")
    print("✅ Flexibility to override FPS when needed")
    print("✅ Better user experience with guided field selection")


def show_operator_details():
    """Show detailed information about the operator"""
    print("\n📋 Operator Details:")
    print("-" * 30)
    
    operators = foo.list_operators()
    video_creator_ops = [op for op in operators if 'create_video_assets_per_scene' in op.name]
    
    if video_creator_ops:
        op = video_creator_ops[0]
        print(f"Name: {op.name}")
        print(f"Class: {op.__class__.__name__}")
        print(f"Module: {op.__class__.__module__}")
        
        try:
            config = op.config
            print(f"Label: {config.label}")
            print(f"Description: {config.description}")
        except:
            print("Config details not available")


if __name__ == "__main__":
    demo_enhanced_video_creator()
    show_operator_details()
