from crewai import Agent, Task, Crew, LLM
from crewai_tools import SerperDevTool
from dotenv import load_dotenv
import litellm

load_dotenv()

litellm.drop_params = True

_original_completion = litellm.completion
def _patched_completion(*args, **kwargs):
    messages = kwargs.get("messages", [])
    for msg in messages:
        msg.pop("cache_breakpoint", None)
        msg.pop("cache_control", None)
    return _original_completion(*args, **kwargs)
litellm.completion = _patched_completion

topic = "Medical Industry using Generative AI"

llm = LLM(
    model="groq/llama-3.3-70b-versatile"
)

search_tool = SerperDevTool(n=10)

senior_research_analyst = Agent(
    role="Senior Research Analyst",
    goal=f"Research, analyze, and synthesize comprehensive information on {topic} from reliable web sources",
    backstory=(
        "You're an expert research analyst with advanced web research skills. "
        "You excel at finding, analyzing, and synthesizing information from "
        "across the internet using search tools. You're skilled at "
        "distinguishing reliable sources from unreliable ones, "
        "fact-checking, cross-referencing information, and "
        "identifying key patterns and insights. You provide "
        "well-organized research briefs with proper citations "
        "and source verification. Your analysis includes both "
        "raw data and interpreted insights, making complex "
        "information accessible and actionable."
    ),
    tools=[search_tool],
    allow_delegation=False,
    verbose=True,
    llm=llm,
    use_system_prompt=True
)

content_writer = Agent(
    role="Content Writer",
    goal="Transform research findings into engaging, informative, and well-structured content pieces",
    backstory=(
        "You're a skilled content writer with expertise in translating complex research "
        "findings into compelling narratives. You understand how to structure "
        "information for maximum engagement and clarity. Your writing is "
        "well-researched, accurate, and tailored to the intended audience. "
        "You excel at creating content that is not only informative but also "
        "engaging, whether it's for blogs, reports, social media, or presentations. "
        "You ensure that your content maintains a consistent voice and style "
        "while accurately representing the research findings."
    ),
    tools=[search_tool],
    allow_delegation=False,
    verbose=True,
    llm=llm
)

research_task = Task(
    description=f"""
    1. Conduct comprehensive research on {topic} including:
       - Recent developments and news
       - Key industry trends and innovations
       - Expert opinions and analyses
       - Statistical data and market insights

    2. Evaluate source credibility and fact-check all information

    3. Organize findings into a structured research brief

    4. Include all relevant citations and sources
    """,
    expected_output="""
    A detailed research report containing:
    - Executive summary of key findings
    - Comprehensive analysis of current trends and developments
    - List of verified facts and statistics
    - All citations and links to original sources
    - Clear categorization of main themes and patterns
    """,
    agent=senior_research_analyst
)

writing_task = Task(
    description="""
    Using the research brief provided, create an engaging blog post that:
    1. Transforms technical information into accessible content
    2. Maintains all factual accuracy and citations from the research
    3. Includes:
       - Attention-grabbing introduction
       - Well-structured body sections with clear headings
       - Compelling conclusion
    4. Preserves all source citations in [Source: URL] format
    5. Includes a References section at the end
    """,
    expected_output="""
    A polished blog post in markdown format with:
    - Title
    - Introduction
    - Main sections
    - Conclusion
    - References section
    """,
    agent=content_writer
)

crew = Crew(
    agents=[senior_research_analyst, content_writer],
    tasks=[research_task, writing_task],
    verbose=True,
    planning=False
)

result = crew.kickoff(inputs={"topic": topic})

print(result)
