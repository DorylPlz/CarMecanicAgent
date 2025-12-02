"""
Main ADK agent for mechanical vehicle queries.
Integrates PDF manual search and internet search.
"""
import os
import asyncio
from typing import Optional, Any
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from config import Config
from agent_tools import setup_tools, get_tools, TOOL_FUNCTIONS


class MechanicalAgent:
    """Mechanical agent using ADK with Gemini."""
    
    def __init__(self, model: str = None):
        """
        Initializes the mechanical agent.
        
        Args:
            model: Gemini model to use (defaults to Config.LLM_MODEL if not provided)
        """
        # Use configured model if not provided
        if model is None:
            model = Config.LLM_MODEL
        # Verify API key
        if not Config.GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY not found. "
                "Configure it as an environment variable."
            )
        
        # Verify vehicle configuration
        if Config.vehicle is None:
            raise ValueError(
                "Vehicle not configured. "
                "Use Config.set_vehicle() before initializing the agent."
            )
        
        # Configure API key
        os.environ["GOOGLE_API_KEY"] = Config.GOOGLE_API_KEY
        
        # Initialize tools
        setup_tools()
        
        # Create ADK agent
        self.agent = Agent(
            name="MechanicalAgent",
            model=model,
            description=(
                f"Agent specialized in vehicle diagnosis and repair. "
                f"Expert on vehicle: {Config.get_vehicle_info()}. "
                "Uses the service manual as the primary source of information."
            ),
            tools=get_tools(),
            instruction=self._get_instruction()
        )
        
        # Create runner with session
        self.session_service = InMemorySessionService()
        self.app_name = "mechanical_agent"
        self.default_user_id = "user"
        self.runner = Runner(
            agent=self.agent,
            app_name=self.app_name,
            session_service=self.session_service
        )
        
        # Save reference to tool functions for later use
        self.tool_functions = TOOL_FUNCTIONS
        
        print(f"✅ Mechanical agent initialized for {Config.get_vehicle_info()}")
    
    def _ensure_session(self, session_id: str, user_id: str = None):
        """Ensures the session exists, creating it if necessary."""
        user_id = user_id or self.default_user_id
        import asyncio
        
        async def create_session_async():
            try:
                await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
            except Exception:
                # Session already exists or other error, continue
                pass
        
        # Create session if it doesn't exist
        try:
            asyncio.run(create_session_async())
        except Exception:
            pass
    
    def _get_instruction(self) -> str:
        """Generates agent instructions."""
        vehicle_info = Config.get_vehicle_info()
        
        return f"""
You are a mechanical expert specialized in vehicle diagnosis and repair. You provide precise and direct technical information from the service manual.

VEHICLE INFORMATION:
{vehicle_info}

OPERATING INSTRUCTIONS:

1. **Manual Search (MANDATORY AND PRIORITY)**
   - ALWAYS use the search_manual tool FIRST for any query
   - The manual is in English and contains vehicle-specific information
   - Search using terms in English and other languages to maximize results
   - The manual has over 7000 pages, search exhaustively
   - If you find information, provide ALL technical details without restrictions
   - ALWAYS include the exact page number where the information is found

2. **Internet Search (ONLY IF NO RESULTS IN MANUAL)**
   - Only use search_internet if search_manual returns no results
   - If the manual has the information, use it exclusively
   - When you use internet search, ALWAYS follow this format:
     
     a) **Opening Statement** (MANDATORY):
        - Start your response by clearly stating that you searched the internet
        - Examples:
          * Spanish: "No encontré información sobre esto en el manual de servicio. Realicé una búsqueda en internet y encontré lo siguiente:"
          * English: "I did not find information about this in the service manual. I performed an internet search and found the following:"
          * Adapt to the user's language
        
     b) **Provide the Information**:
        - Present the information clearly and comprehensively
        - Translate to the user's language if needed
        
     c) **Sources Section** (MANDATORY):
        - ALWAYS include a sources section at the very end of your response
        - Format: "📚 FUENTES / SOURCES:" followed by numbered list
        - Include ALL URLs provided in the search results
        - Ensure each source is on a separate line with a number

3. **Technical Response Format**
   When responding, provide complete technical information:
   
   a) **Manual Page** (MANDATORY if found)
      - Indicate the exact page number
      - If the page contains diagrams or images, MENTION that there are reference diagrams available
   
   b) **Technical Content from Manual**
      - Provide complete technical information from the manual
      - Translate to the user's language if necessary, but maintain technical precision
      - Include all steps, specifications and procedures
      - If diagrams/images are mentioned, describe what they show according to the text context
   
   c) **Procedure Steps**
      - Numbered and detailed list of steps according to the manual
      - Include torque specifications, tools and parts needed
      - If there are diagrams, reference them (e.g., "See diagram on page X")
   
   d) **Reference Diagrams and Images**
      - When diagrams or images are mentioned in search results:
        * Clearly indicate that there are diagrams/images available on the mentioned page(s)
        * Describe what the diagrams show according to the context of the found text
        * Mention that diagrams complement the textual information
   
   e) **Technical Warnings (Only if critical)**
      - Only mention critical technical warnings from the manual
      - DO NOT add generic safety warnings
      - DO NOT recommend seeking professional help unless the manual indicates it

4. **Direct Technical Behavior**
   - Provide direct and complete technical information from the manual
   - DO NOT be excessively cautious or add unnecessary warnings
   - DO NOT recommend seeking professional help unless absolutely necessary
   - The user is a technician who needs precise information, not generic warnings
   - If the information is in the manual, provide ALL available technical information
   - Translate the manual content to the user's language while maintaining technical precision

5. **Language Response**
   - ALWAYS respond in the SAME LANGUAGE that the user used in their query
   - If the user asks in Spanish, respond in Spanish
   - If the user asks in English, respond in English
   - If the user asks in French, respond in French
   - Maintain this language throughout the conversation
   - Translate technical terms appropriately while preserving accuracy

6. **Exhaustive Search**
   - The manual has over 7000 pages, search with multiple terms
   - If you don't find it in the first search, try synonyms and related terms
   - Use technical terms in English (brake pads, caliper, etc.) in addition to other languages
"""
    
    def query(self, query: str, session_id: str = "default", user_id: str = None) -> str:
        """
        Processes a user query.
        
        Args:
            query: User question about the vehicle
            session_id: Session ID to maintain context
            user_id: User ID (optional, uses default if not provided)
            
        Returns:
            Agent response
        """
        user_id = user_id or self.default_user_id
        
        try:
            # Ensure session exists
            self._ensure_session(session_id, user_id)
            
            # Prepare message in ADK format
            content = types.Content(
                role='user',
                parts=[types.Part(text=query)]
            )
            
            # Execute query using run_async synchronously
            final_response = "No response received from agent."
            
            # Use run_async in event loop
            import asyncio
            
            async def run_query():
                text_parts = []
                async for event in self.runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=content
                ):
                    # Handle function calls if they exist
                    if hasattr(event, 'content') and event.content:
                        if hasattr(event.content, 'parts') and event.content.parts:
                            for part in event.content.parts:
                                # If there's a function_call, execute it manually
                                if hasattr(part, 'function_call') and part.function_call:
                                    func_name = part.function_call.name
                                    # Extract arguments
                                    func_args = {}
                                    if hasattr(part.function_call, 'args'):
                                        args_obj = part.function_call.args
                                        if isinstance(args_obj, dict):
                                            func_args = args_obj
                                        elif hasattr(args_obj, '__dict__'):
                                            func_args = args_obj.__dict__
                                        # Try to extract 'query' if it exists
                                        if 'query' not in func_args and hasattr(args_obj, 'query'):
                                            func_args['query'] = args_obj.query
                                    
                                    # Execute function if it exists
                                    if func_name in self.tool_functions:
                                        try:
                                            # Execute the function
                                            result = self.tool_functions[func_name](**func_args)
                                            # Result will be handled in the next iteration
                                            # ADK should include the result in the final response
                                        except Exception as e:
                                            print(f"⚠️ Error executing function {func_name}: {e}")
                    
                    # Get final response
                    if hasattr(event, 'is_final_response') and event.is_final_response():
                        if hasattr(event, 'content') and event.content:
                            if hasattr(event.content, 'parts') and event.content.parts:
                                # Collect all text parts
                                for part in event.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        text_parts.append(part.text)
                            elif hasattr(event.content, 'text'):
                                text_parts.append(event.content.text)
                
                # Return all text parts concatenated
                if text_parts:
                    return "\n".join(text_parts)
                return final_response
            
            # Execute async function
            final_response = asyncio.run(run_query())
            
            return final_response
                
        except Exception as e:
            return f"Error processing query: {str(e)}"
    
    def chat(self, session_id: str = "default"):
        """
        Starts an interactive chat with the agent.
        
        Args:
            session_id: Session ID to maintain context
        """
        print("\n" + "="*60)
        print("🔧 Mechanical Agent - Interactive Chat")
        print(f"Vehicle: {Config.get_vehicle_info()}")
        print("="*60)
        print("Type 'exit' or 'quit' to finish\n")
        
        while True:
            try:
                query = input("👤 You: ").strip()
                
                if query.lower() in ['exit', 'quit', 'salir']:
                    print("\n👋 Goodbye!")
                    break
                
                if not query:
                    continue
                
                print("\n🤖 Agent: ", end="", flush=True)
                response = self.query(query, session_id)
                print(response)
                print()
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}\n")
