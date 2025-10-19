# Slides Translator Agent

[![Build Status](https://github.com/fmind/slides-translator-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/fmind/slides-translator-agent/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/fmind/slides-translator-agent)](https://github.com/fmind/slides-translator-agent/blob/main/LICENSE.txt)
[![Release](https://img.shields.io/github/v/release/fmind/slides-translator-agent)](https://github.com/fmind/slides-translator-agent/releases)

**Slides Translator** is an AI-powered agent designed to automatically translate the content of a Google Slides presentation into a specified language.

It leverages Large Language Models (LLMs) through the Google AI platform and uses the Google Drive and Google Slides APIs to read the original presentation and create a translated copy.

## ✨ Features

*   **Google Slides & Drive Integration:** Securely authenticates with Google services using OAuth2 to access presentations.
*   **Automated Presentation Copying:** Creates a new, translated version of the presentation in your Google Drive, preserving the original.
*   **Content Translation:** Extracts and translates all text elements within the slides.
*   **Context-Awareness:** Allows users to provide additional context (e.g., "this is a technical presentation") to improve translation quality.
*   **Agent-based Architecture:** Built using the `google-adk` framework for a modular and robust design.
*   **Configurable:** Allows setting the underlying LLM models for the agent and translation tasks via environment variables.

## ⚙️ Setup & Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/fmind/slides-translator-agent
    cd slides-translator-agent
    ```

2.  **Install dependencies:**
    This project uses `uv` for package management.

    ```bash
    uv sync --all-groups
    ```

3.  **Create an environment file:**
    Copy the example environment file and fill in the required values.

    ```bash
    cp .env.example .env
    ```
    You will need to populate `GOOGLE_CLOUD_PROJECT`, `AUTHENTICATION_CLIENT_ID`, and `AUTHENTICATION_CLIENT_SECRET` in the `.env` file.

## 🔑 Authentication

This project requires two layers of authentication:

1.  **Google Cloud (for Generative AI):**
    Ensure you have authenticated your environment for Google Cloud access. This typically involves:
    *   Installing the Google Cloud CLI (`gcloud`).
    *   Running `gcloud auth application-default login`.
    *   Ensuring the **AI Platform API** is enabled in your Google Cloud project.

2.  **Google Workspace (for Slides & Drive):**
    The agent needs to act on your behalf to read and create presentations. This is done via OAuth 2.0.
    *   You must create an **OAuth 2.0 Client ID** in your Google Cloud project.
    *   When creating the credential, configure a redirect URI for the web UI, e.g., `http://localhost:8000/dev-ui`.
    *   Once created, copy the **Client ID** and **Client Secret** into the `AUTHENTICATION_CLIENT_ID` and `AUTHENTICATION_CLIENT_SECRET` variables in your `.env` file.
    *   Make sure the **Google Drive API** and **Google Slides API** are enabled for your project.

## 🔧 Configuration

The application uses environment variables for configuration (defined in `.env`):

*   `GOOGLE_CLOUD_PROJECT`: Your Google Cloud project ID.
*   `AUTHENTICATION_CLIENT_ID`: Your OAuth 2.0 Client ID.
*   `AUTHENTICATION_CLIENT_SECRET`: Your OAuth 2.0 Client Secret.
*   `MODEL_NAME_AGENT`: The agent's LLM model (defaults to `gemini-2.5-flash`).
*   `MODEL_NAME_TRANSLATION`: The translation task's LLM model (defaults to `gemini-2.5-flash`).
*   `LOGGING_LEVEL`: Sets the logging level (e.g., `INFO`, `DEBUG`).
*   `GOOGLE_CLOUD_LOCATION`: The GCP region for the agent (defaults to `global`).

## 🚀 Usage

This project uses `just` as a command runner.

*   **`just agent-web`**: Run the agent's web UI locally.
*   **`just agent-deploy`**: Deploy the agent to Google Cloud Run and Agent Engine.

When you first run the web UI and use the tool, you will be prompted to complete the OAuth flow in your browser to grant the agent permission to access your Google Drive and Slides.

## 🧪 Testing

The project includes a set of checks for code quality, formatting, and types. To run them:

```bash
just check
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE.txt file for details.
