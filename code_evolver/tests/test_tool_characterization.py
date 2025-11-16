#!/usr/bin/env python3
"""
Tool Characterization Tests
Tests that characterize tools using both Locust and Behave
"""
import pytest
import json
import os
import subprocess
import tempfile
from pathlib import Path


class TestToolCharacterization:
    """Test tool characterization with Locust and Behave"""

    @pytest.fixture
    def test_tool_spec(self):
        """Create a test tool specification"""
        return {
            "name": "Test Tool",
            "type": "executable",
            "description": "A test tool for characterization",
            "input_schema": {
                "test_param": {
                    "type": "string",
                    "description": "Test parameter",
                    "required": True
                }
            },
            "output_schema": {
                "success": {"type": "boolean"},
                "data": {"type": "object"}
            }
        }

    @pytest.fixture
    def test_api_spec(self):
        """Create a test OpenAPI specification"""
        return {
            "openapi": "3.0.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0"
            },
            "paths": {
                "/health": {
                    "get": {
                        "operationId": "health_check",
                        "summary": "Health check endpoint",
                        "responses": {
                            "200": {
                                "description": "Healthy"
                            }
                        }
                    }
                },
                "/api/test": {
                    "post": {
                        "operationId": "create_test",
                        "summary": "Create test resource",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "value": {"type": "integer"}
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {
                            "201": {
                                "description": "Created"
                            }
                        }
                    }
                }
            }
        }

    def test_create_locust_spec(self):
        """Test creating a Locust specification"""
        input_data = {
            "tool_name": "test_tool",
            "base_url": "http://localhost:8000",
            "endpoints": [
                {
                    "path": "/test",
                    "method": "GET",
                    "weight": 10
                }
            ]
        }

        # Run create_locust_spec tool
        result = subprocess.run(
            ["python", "tools/executable/create_locust_spec.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd="/home/user/mostlylucid.dse/code_evolver"
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        output = json.loads(result.stdout)
        assert output['success'] is True
        assert 'spec_path' in output
        assert os.path.exists(output['spec_path'])

    def test_create_behave_spec(self):
        """Test creating a Behave specification"""
        input_data = {
            "tool_name": "test_tool",
            "description": "Test tool for BDD characterization",
            "scenarios": [
                {
                    "name": "Basic test",
                    "steps": [
                        {"keyword": "Given", "text": "the tool is ready"},
                        {"keyword": "When", "text": "I run the tool"},
                        {"keyword": "Then", "text": "it should succeed"}
                    ]
                }
            ]
        }

        # Run create_behave_spec tool
        result = subprocess.run(
            ["python", "tools/executable/create_behave_spec.py"],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            cwd="/home/user/mostlylucid.dse/code_evolver"
        )

        assert result.returncode == 0, f"Failed: {result.stderr}"
        output = json.loads(result.stdout)
        assert output['success'] is True
        assert 'spec_path' in output
        assert 'feature_path' in output
        assert os.path.exists(output['spec_path'])
        assert os.path.exists(output['feature_path'])

    def test_locust_load_tester_generation(self, test_api_spec):
        """Test Locust load test generation"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_api_spec, f)
            spec_file = f.name

        try:
            input_data = {
                "spec_file": spec_file,
                "mode": "generate",
                "output_path": "/tmp/locustfiles_test",
                "host": "http://localhost:8000"
            }

            result = subprocess.run(
                ["python", "tools/executable/locust_load_tester.py"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd="/home/user/mostlylucid.dse/code_evolver"
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"
            output = json.loads(result.stdout)
            assert output['success'] is True
            assert 'locustfile_path' in output
            assert os.path.exists(output['locustfile_path'])

            # Verify locustfile content
            with open(output['locustfile_path'], 'r') as f:
                content = f.read()
                assert 'HttpUser' in content
                assert 'health_check' in content

        finally:
            os.unlink(spec_file)

    def test_behave_test_generator_from_tool_spec(self, test_tool_spec):
        """Test Behave test generation from tool spec"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(test_tool_spec, f)
            spec_file = f.name

        try:
            input_data = {
                "tool_spec": spec_file,
                "mode": "generate",
                "output_path": "/tmp/behave_steps_test",
                "feature_output_path": "/tmp/behave_features_test"
            }

            result = subprocess.run(
                ["python", "tools/executable/behave_test_generator.py"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd="/home/user/mostlylucid.dse/code_evolver"
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"
            output = json.loads(result.stdout)
            assert output['success'] is True
            assert 'steps_file_path' in output
            assert 'feature_file_path' in output
            assert os.path.exists(output['steps_file_path'])
            assert os.path.exists(output['feature_file_path'])

            # Verify step definitions
            with open(output['steps_file_path'], 'r') as f:
                content = f.read()
                assert 'from behave import' in content
                assert 'def step_' in content

        finally:
            os.unlink(spec_file)

    def test_parse_static_analysis(self):
        """Test parsing static analysis results"""
        # Create a mock static analysis file
        mock_analysis = {
            "validators": {
                "syntax": {
                    "valid": True,
                    "functions": ["test_function"]
                },
                "json_output": {
                    "valid": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "success": {"type": "boolean"}
                        }
                    }
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(mock_analysis, f)
            analysis_file = f.name

        try:
            input_data = {
                "analysis_file": analysis_file,
                "extract_schemas": True,
                "extract_patterns": True
            }

            result = subprocess.run(
                ["python", "tools/executable/parse_static_analysis.py"],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                cwd="/home/user/mostlylucid.dse/code_evolver"
            )

            assert result.returncode == 0, f"Failed: {result.stderr}"
            output = json.loads(result.stdout)
            assert output['success'] is True
            assert 'schemas' in output
            assert 'patterns' in output
            assert 'test_hints' in output
            assert 'quality_metrics' in output

        finally:
            os.unlink(analysis_file)

    def test_full_characterization_workflow(self, test_tool_spec, test_api_spec):
        """Test full tool characterization workflow with both Locust and Behave"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Create Locust spec
            locust_input = {
                "tool_name": "full_test_tool",
                "base_url": "http://localhost:8000",
                "output_path": os.path.join(tmpdir, "locust_specs")
            }

            locust_spec_result = subprocess.run(
                ["python", "tools/executable/create_locust_spec.py"],
                input=json.dumps(locust_input),
                capture_output=True,
                text=True,
                cwd="/home/user/mostlylucid.dse/code_evolver"
            )

            assert locust_spec_result.returncode == 0
            locust_output = json.loads(locust_spec_result.stdout)
            assert locust_output['success']

            # Step 2: Create Behave spec
            behave_input = {
                "tool_name": "full_test_tool",
                "description": "Full characterization test",
                "output_path": os.path.join(tmpdir, "behave_specs")
            }

            behave_spec_result = subprocess.run(
                ["python", "tools/executable/create_behave_spec.py"],
                input=json.dumps(behave_input),
                capture_output=True,
                text=True,
                cwd="/home/user/mostlylucid.dse/code_evolver"
            )

            assert behave_spec_result.returncode == 0
            behave_output = json.loads(behave_spec_result.stdout)
            assert behave_output['success']

            # Step 3: Verify both specs exist and are valid
            assert os.path.exists(locust_output['spec_path'])
            assert os.path.exists(behave_output['spec_path'])
            assert os.path.exists(behave_output['feature_path'])

            # Step 4: Verify specs contain expected content
            with open(locust_output['spec_path'], 'r') as f:
                import yaml
                locust_spec = yaml.safe_load(f)
                assert locust_spec['tool_name'] == 'full_test_tool'
                assert 'test_config' in locust_spec
                assert 'metadata' in locust_spec

            with open(behave_output['feature_path'], 'r') as f:
                feature_content = f.read()
                assert 'Feature:' in feature_content
                assert 'Scenario:' in feature_content
                assert 'Given' in feature_content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
