# Basic Usage: Echo Tool

This tool demonstrates the MCPKG format by echoing back whatever input it receives.

It uses the Postman Echo API to demonstrate HTTP endpoint integration.

## Example Call

```json
{
  "message": "Hello, World!"
}
```

## Expected Behavior

* The tool will send a POST request to https://postman-echo.com/post
* The message will be echoed back in the response
* The response will have the structure: `{ "data": { "message": "..." } }`

## Use Cases

* Testing MCPKG package creation and installation
* Validating the test runner functionality
* Demonstrating tool manifest structure
* Example for building your own MCP tools
