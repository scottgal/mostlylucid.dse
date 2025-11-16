# Tool Compile Command

You are helping the user compile a tool or workflow into a standalone package.

## User Request Format

The user may request this in various ways:
- `/tool-compile <tool_id> <output_path> [format]`
- "make an executable of this workflow"
- "compile <tool_name> to an exe"
- "dockerize this tool"

## Your Task

1. **Parse the request** to extract:
   - `tool_id`: The tool or workflow to compile
   - `output_path`: Where to save the package (default: ./output)
   - `format`: Package format - "docker", "exe", "both" (default: docker)

2. **Execute the appropriate workflow**:

   ### For Docker packaging:
   - Use the `docker_packaging_workflow` workflow
   - Parameters:
     ```json
     {
       "tool_id": "<tool_id>",
       "service_name": "<tool_id>-api",
       "output_path": "<output_path>",
       "port": 8080,
       "base_image": "python:3.11-slim",
       "enable_cors": true,
       "auto_build": false
     }
     ```

   ### For standalone executable:
   - Use the `standalone_exe_compiler` tool
   - Parameters:
     ```json
     {
       "tool_id": "<tool_id>",
       "output_name": "<tool_id>_standalone",
       "mode": "cli",
       "port": 8080
     }
     ```

3. **Save generated files**:
   - Create the output directory structure
   - Write all generated files (Dockerfile, docker-compose.yml, .env, etc.)
   - Make scripts executable (chmod +x)

4. **Provide instructions**:
   - Tell the user where files were saved
   - Provide next steps for building and running
   - Include any relevant commands

## Example Interaction

User: "/tool-compile basic_calculator ./my-calc-api docker"

You should:
1. Run the docker_packaging_workflow with tool_id="basic_calculator", output_path="./my-calc-api"
2. Create the directory structure and save all files
3. Respond with:
   ```
   Successfully compiled basic_calculator to Docker package!

   Files created in ./my-calc-api/:
   - Dockerfile
   - docker-compose.yml
   - api_server.py
   - .env
   - .env.example
   - build.sh
   - run.sh
   - test.sh
   - README.md

   To build and run:
   cd ./my-calc-api
   chmod +x *.sh
   ./build.sh
   ./run.sh

   API will be available at http://localhost:8080
   ```

## Error Handling

If the tool doesn't exist, inform the user and suggest:
- List available tools
- Check tool spelling
- Provide similar tool names

## Additional Features

If the user wants to customize:
- Port number: Ask or use default 8080
- Base image: Ask or use python:3.11-slim
- Service name: Derive from tool_id or ask

Always be helpful and provide clear, actionable instructions!
