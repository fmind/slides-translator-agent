# https://just.systems/man/en/

# REQUIRES

gcloud := require("gcloud")
git := require("git")
uv := require("uv")

# SETTINGS

set dotenv-load := true
set unstable := true

# ENVIRONS

export UV_ENV_FILE := ".env"

# VARIABLES

AGENT := "slides_translator_agent"

# DEFAULTS

# display help information
default:
    @just --list

# IMPORTS

import 'tasks/agent.just'
import 'tasks/check.just'
import 'tasks/clean.just'
import 'tasks/cloud.just'
import 'tasks/format.just'
import 'tasks/install.just'
