import sys
import os

# Insert the 'Equipment' directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import config
import stages.stage1_manufacturers as stage1

print("config in main:", id(config))
print("config in stage1:", id(stage1.config))
print("Are they same?", config is stage1.config)
