# Steps

## 1 Setup an API key for Google Maps in Argolis

## 2 Clone the gitlab repo

## 3 Setup the virtual env
1. `cd talk-building-your-own-mcp-server`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`

## 4 Create a .env file within each of the agent subdirectories
The .env file should have the following entries - 
```
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=<Your Project Name>
GOOGLE_CLOUD_LOCATION=us-central1
```

## 5 Create a .env file within each of the mcp subdirectories
The .env file should have the following entries -
```
GOOGLE_MAPS_API_KEY=<Your API Key>
```

## 4 Running the agent
1. Make sure to auth with `gcloud auth application-default login`
2. Run `cd agent`
2. Run `adk web`

## 5 Running the MCP Server
1. Change path `cd mcpserver`
2. Run `python google_maps_server.py`

## 6 Run the MCP Inspector
1. Make sure you have node installed - [https://nodejs.org/en/download/]
2. Run `npx @modelcontextprotocol/inspector`
3. Connect to your MCP Server over 'HTTP' using the MCP Serer URL - which is usually <url>:<port>/mcp
