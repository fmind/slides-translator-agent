# https://docs.cloud.google.com/agent-builder/agent-engine/deploy

# %% IMPORTS

import os

import vertexai

from .agent import root_agent

# %% ENVIRONS

# folders
AGENT_FOLDER = os.path.dirname(os.path.abspath(__file__))

# optional
AGENT_ENGINE_ID = os.getenv("AGENT_ENGINE_ID")
AUTHENTICATION_CLIENT_ID = os.getenv("AUTHENTICATION_CLIENT_ID")
AUTHENTICATION_CLIENT_SECRET = os.getenv("AUTHENTICATION_CLIENT_SECRET")
LOGGING_LEVEL = os.getenv("LOGGING_LEVEL", "INFO")

# required
LOCATION = os.environ["GOOGLE_CLOUD_LOCATION"]
PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
STAGING_BUCKET = os.environ["STAGING_BUCKET"]

# derived
if AGENT_ENGINE_ID:
    RESOURCE_NAME = f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{AGENT_ENGINE_ID}"
else:
    RESOURCE_NAME = None

print("# Environment Variables\n")
for key, value in globals().copy().items():
    if key.isupper():
        print(f"- {key}: {value}")
print()

# %% CONFIGS

config = {
    "display_name": "Slides Translator Agent",
    "description": "Translate Google Slides automatically with Generative AI.",
    "requirements": os.path.join(AGENT_FOLDER, "requirements.txt"),
    "extra_packages": [os.path.basename(AGENT_FOLDER)],
    "staging_bucket": STAGING_BUCKET,
    "env_vars": {
        "AUTHENTICATION_CLIENT_ID": AUTHENTICATION_CLIENT_ID,
        "AUTHENTICATION_CLIENT_SECRET": AUTHENTICATION_CLIENT_SECRET,
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
    },
}

print("# Configuration Variables\n")
for key, value in config.items():
    print(f"- {key}: {value}")
print()

# %% CLIENTS

client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

# %% EXECUTIONS

if RESOURCE_NAME:
    print(f"# Updating Agent Engine: {RESOURCE_NAME}\n")
    remote_agent = client.agent_engines.update(
        name=RESOURCE_NAME,
        agent=root_agent,
        config=config,
    )
else:
    print("# Creating Agent Engine: ...\n")
    remote_agent = client.agent_engines.create(
        agent=root_agent,
        config=config,
    )
print(f"# Remote Agent: {remote_agent.api_resource.name}")
