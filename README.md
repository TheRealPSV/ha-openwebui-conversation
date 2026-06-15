[![GitHub Release](https://img.shields.io/github/release/TheRealPSV/ha-openwebui-conversation.svg?style=flat-square)](https://github.com/TheRealPSV/ha-openwebui-conversation/releases)
[![Downloads](https://img.shields.io/github/downloads/TheRealPSV/ha-openwebui-conversation/total?style=flat-square)](https://github.com/TheRealPSV/ha-openwebui-conversation/releases)
[![Build Status](https://img.shields.io/github/actions/workflow/status/TheRealPSV/ha-openwebui-conversation/validate.yml?style=flat-square)](https://github.com/TheRealPSV/ha-openwebui-conversation/actions/workflows/validate.yml)
[![License](https://img.shields.io/github/license/TheRealPSV/ha-openwebui-conversation.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-default-blue.svg?style=flat-square)](https://hacs.xyz)

# OpenWebUI Conversation

The OpenWebUI integration adds a conversation agent powered by [OpenWebUI][openwebui] in Home Assistant.

This conversation agent is unable to control your house. The OpenWebUI conversation agent can be used in automations, but not as a [sentence trigger][sentence-trigger]. If you'd like house control and sentence triggers, Home Assistant's "Prefer handling commands locally" option is recommended: Set the standard Assist engine as your main Assistant, and in the Assistant configuration, under the Conversation Agent, just make sure the "Prefer handling commands locally" option is enabled. This will use Home Assistant triggers by default, and fall back to this integration if a trigger isn't matched.

This conversation agent can search the internet for you, using sentence triggers you can configure, if Web Search is set up in OpenWebUI. For more details, see the relevant Options section below.

You can also take advantage of OpenWebUI's ability to "clone" models; once you create a clone model in OpenWebUI, it will automatically be available to select in the integration's options.

## Installation

To install the **OpenWebUI Conversation** integration to your Home Assistant instance, use this My button:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=therealpsv&repository=ha-openwebui-conversation&category=integration)

#### Manual Installation
If the above button doesn’t work, you can also perform the following steps manually:

* Browse to your Home Assistant instance.
* Go to HACS > Integrations > Custom Repositories.
* Add custom repository.
  * Repository is `TheRealPSV/ha-openwebui-conversation`.
  * Category is `Integration`.
* Click ***Explore & Download Repositories***.
* From the list, select OpenWebUI Conversation.
* In the bottom right corner, click the ***Download*** button.
* Follow the instructions on screen to complete the installation.

#### Note:
HACS does not "configure" the integration for you, You must add OpenWebUI Conversation after installing via HACS.

* Browse to your Home Assistant instance.
* Go to Settings > Devices & Services.
* In the bottom right corner, select the ***Add Integration*** button.
* From the list, select OpenWebUI Conversation.
* Follow the instructions on screen to complete the setup.
  * **Service Name** is required, but you can name it whatever you like.
  * **Base Url** is the URL for the OpenWebUI service.
  * **API Key** is the API key for your user, which you can find in your OpenWebUI Settings, under Account.
  * **API Timeout** is described below under General Settings.
  * **Verify SSL** is if requests should verify SSL certificates for HTTPS. Disable verification if you are using self signed certificates.
* Once you have added the integration, make sure you set your preferred model as described below.

## Options
Options for OpenWebUI Conversation can be set via the user interface, by taking the following steps:

* Browse to your Home Assistant instance.
* Go to Settings > Devices & Services.
* If multiple instances of OpenWebUI Conversation are configured, choose the instance you want to configure.
* Select the integration, then select ***Configure***.

#### General Settings
Settings relating to the integration itself.

| Option        | Description                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| API Timeout   | The maximum amount of time (in seconds) to wait for a response from the API                                                      |
| Language Code | The code for your preferred language. This is set to English (`en`) by default. A list of codes can be found [here][lang-codes]. |
| Verify SSL    | Verify SSL certificates for HTTPS. Disable verification if you are using self signed certificates.                               |

#### Model Configuration
The language model you want to use.

| Option         | Description                                                                                                                                                                                                                                                                                |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Model          | The model used to generate responses. This list should automatically populate based on the models you have created in OpenWebUI.                                                                                                                                                           |
| Strip Markdown | Whether or not to strip Markdown formatting from the model's output. This can be useful for models that tend to generate responses with Markdown formatting, as HomeAssistant doesn't render Markdown text, and TTS engines will often read out individual Markdown formatting characters. |

NOTE: Model properties should be specified on the model itself in your workspace in OpenWebUI itself.

#### Search Configuration
Options related to performing a web search with OpenWebUI. The agent will perform a web search through OpenWebUI and have the model summarize the results.

| Option                        | Description                                                                                                                                                                                                                                                                           |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Search Enabled                | Whether or not the conversation agent should perform web searches when the given sentences are triggered.                                                                                                                                                                             |
| Search Trigger Sentences      | Sentence triggers that tell the conversation agent to search the web for something. One sentence per line. These sentences use the same syntax as Home Assistant's standard trigger sentences, but must contain `{query}` once in each sentence. Some default sentences are provided. |
| Search Results Message Prefix | Text prepended to the search response that indicates a search was performed. A default prefix is provided.                                                                                                                                                                            |

To enable web search in OpenWebUI, see [OpenWebUI's documentation on Web Search][openwebui-search].

## Attributions:
This integration is based on the [hass-ollama-conversation][hass-ollama-conversation] repo.

***

[openwebui]: https://openwebui.com/
[sentence-trigger]: https://www.home-assistant.io/docs/automation/trigger/#sentence-trigger
[hass-ollama-conversation]: https://github.com/ej52/hass-ollama-conversation/
[fallback-conversation-agent]: https://github.com/m50/ha-fallback-conversation
[lang-codes]: https://developers.home-assistant.io/docs/voice/intent-recognition/supported-languages/
[openwebui-search]: https://docs.openwebui.com/features/web_search
