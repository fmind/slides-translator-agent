# run agent tasks
[group('agent')]
agent: agent-web

# deploy the agents
[parallel]
[group('agent')]
agent-deploy: agent-deploy-on-agent-engine agent-deploy-on-cloud-run

# deploy the agent on agent engine
[group('agent')]
agent-deploy-on-agent-engine: agent-requirements
    uv run adk deploy agent_engine {{env('AGENT_ENGINE_ID', '') && "--agent_engine_id=" + env('AGENT_ENGINE_ID')}} \
        --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_LOCATION --staging_bucket=$STAGING_BUCKET \
        --trace_to_cloud --env_file=.env --requirements_file={{AGENT}}/requirements.txt {{AGENT}}

# deploy the agent on cloud run
[group('agent')]
agent-deploy-on-cloud-run: agent-requirements
    adk deploy cloud_run --trace_to_cloud --with_ui --a2a \
    --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_LOCATION  \
    --service_name={{replace(AGENT, '_', '-')}} --app_name={{AGENT}} {{AGENT}}

# export agent requirements
[group('agent')]
agent-requirements:
    uv export --no-hashes --no-annotate --no-emit-project --output-file={{AGENT}}/requirements.txt

# serve the agent web
[group('agent')]
agent-web log_level="INFO":
    uv run adk web --a2a --reload --reload_agents --log_level={{log_level}}
