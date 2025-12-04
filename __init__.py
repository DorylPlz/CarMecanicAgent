"""
CarMecanicAgent - Mechanical diagnostic agent using ADK and Gemini.
"""
import sys
from pathlib import Path

# Add the package directory to sys.path when imported as a module
# This allows absolute imports to work when the package is loaded from parent directory
_package_dir = Path(__file__).parent
if str(_package_dir) not in sys.path:
    sys.path.insert(0, str(_package_dir))

# Import agent module
from . import agent

# Expose root_agent for ADK
# ADK looks for root_agent in CarMecanicAgent.root_agent or CarMecanicAgent.agent.root_agent
# Initialize root_agent - this will raise an error if configuration is missing
root_agent = agent._initialize_root_agent()

# Also expose in agent module for CarMecanicAgent.agent.root_agent
agent.root_agent = root_agent
