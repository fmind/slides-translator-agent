# %% IMPORTS

from vertexai.agent_engines import AdkApp

from slides_translator_agent.agent import root_agent

# %% APP

adk_app = AdkApp(
    agent=root_agent,
    enable_tracing=True,
)
