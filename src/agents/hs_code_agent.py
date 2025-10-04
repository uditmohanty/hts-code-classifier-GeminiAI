from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from src.tools.search_tools import SearchTools, create_langchain_tools
from src.agents.gemini_classifier import GeminiClassifier
from config.settings import Config
import json

class HSCodeAgent:
    def __init__(self):
        self.search_tools = SearchTools()
        self.gemini_classifier = GeminiClassifier()
        self.llm = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            google_api_key=Config.GOOGLE_API_KEY,
            temperature=0.1
        )
        self.tools = create_langchain_tools(self.search_tools)
        self.agent = self._create_agent()
    
    def _create_agent(self):
        """Create ReAct agent"""
        template = """You are an AI assistant helping classify products for customs using HS codes.

You have access to the following tools:
{tools}

Tool Names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
    
    def classify_product(self, product_info: dict) -> dict:
        """Main classification workflow"""
        
        # Step 1: Validate inputs
        if not self._validate_inputs(product_info):
            return self._request_clarification(product_info)
        
        # Step 2: Search HTS database
        search_query = self._build_search_query(product_info)
        hts_candidates = self.search_tools.search_hts_database(search_query, top_k=5)
        
        # Step 3: Search CROSS rulings
        cross_rulings = self.search_tools.search_cross_rulings(search_query, top_k=3)
        
        # Step 4: Use Gemini to apply GRI rules and make final classification
        classification_result = self.gemini_classifier.classify_product(
            product_info,
            hts_candidates,
            cross_rulings
        )
        
        # Step 5: Enhance with duty rate lookup
        if classification_result.get('recommended_code'):
            duty_info = self.search_tools.lookup_duty_rate(
                classification_result['recommended_code']
            )
            if duty_info['duty_rate'] != 'Not found':
                classification_result['duty_rate'] = duty_info['duty_rate']
        
        # Step 6: Add metadata
        classification_result['hts_candidates'] = hts_candidates
        classification_result['cross_rulings'] = cross_rulings
        classification_result['product_info'] = product_info
        
        # Step 7: Flag for review if low confidence
        confidence_value = float(classification_result.get('confidence', '0%').replace('%', ''))
        classification_result['needs_review'] = confidence_value < (Config.CONFIDENCE_THRESHOLD * 100)
        
        return classification_result
    
    def _validate_inputs(self, product_info: dict) -> bool:
        """Check if we have minimum required information"""
        required_fields = ['product_name', 'description']
        return all(product_info.get(field) for field in required_fields)
    
    def _build_search_query(self, product_info: dict) -> str:
        """Build optimized search query"""
        parts = []
        
        if product_info.get('product_name'):
            parts.append(product_info['product_name'])
        if product_info.get('description'):
            parts.append(product_info['description'])
        if product_info.get('material'):
            parts.append(f"made of {product_info['material']}")
        if product_info.get('use'):
            parts.append(f"used for {product_info['use']}")
        
        return " ".join(parts)
    
    def _request_clarification(self, product_info: dict) -> dict:
        """Return clarification questions"""
        missing_fields = []
        
        if not product_info.get('product_name'):
            missing_fields.append("product name")
        if not product_info.get('description'):
            missing_fields.append("detailed description")
        if not product_info.get('material'):
            missing_fields.append("material composition")
        if not product_info.get('use'):
            missing_fields.append("intended use")
        
        return {
            'status': 'needs_clarification',
            'message': f"Please provide: {', '.join(missing_fields)}",
            'missing_fields': missing_fields
        }