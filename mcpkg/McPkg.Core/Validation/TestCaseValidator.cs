using System.Text.Json;
using Json.Schema;
using mostlylucid.mcpregistry.Core.Models;

namespace mostlylucid.mcpregistry.Core.Validation;

/// <summary>
/// Validates test case files
/// </summary>
public class TestCaseValidator
{
    /// <summary>
    /// Validates a test case
    /// </summary>
    public ValidationResult Validate(TestCase testCase)
    {
        var errors = new List<string>();

        // Validate name
        if (string.IsNullOrWhiteSpace(testCase.Name))
        {
            errors.Add("test name is required");
        }

        // Validate description
        if (string.IsNullOrWhiteSpace(testCase.Description))
        {
            errors.Add("test description is required");
        }

        // Validate input
        if (testCase.Input == null)
        {
            errors.Add("test input is required");
        }

        // Validate assertions
        if (testCase.Assertions == null || testCase.Assertions.Count == 0)
        {
            errors.Add("test must have at least one assertion");
        }
        else
        {
            for (int i = 0; i < testCase.Assertions.Count; i++)
            {
                errors.AddRange(ValidateAssertion(testCase.Assertions[i], i));
            }
        }

        // Validate timeout
        if (testCase.TimeoutMs.HasValue && testCase.TimeoutMs.Value <= 0)
        {
            errors.Add("test timeoutMs must be positive if specified");
        }

        return new ValidationResult
        {
            IsValid = errors.Count == 0,
            Errors = errors
        };
    }

    private static List<string> ValidateAssertion(Assertion assertion, int index)
    {
        var errors = new List<string>();

        // Validate path
        if (string.IsNullOrWhiteSpace(assertion.Path))
        {
            errors.Add($"assertion[{index}]: path is required");
        }

        // Count how many assertion types are specified
        int assertionTypeCount = 0;
        if (assertion.Equals != null) assertionTypeCount++;
        if (assertion.NotEquals != null) assertionTypeCount++;
        if (assertion.Exists.HasValue) assertionTypeCount++;
        if (assertion.NotExists.HasValue) assertionTypeCount++;

        if (assertionTypeCount == 0)
        {
            errors.Add($"assertion[{index}]: must specify one of: equals, notEquals, exists, notExists");
        }
        else if (assertionTypeCount > 1)
        {
            errors.Add($"assertion[{index}]: can only specify one assertion type");
        }

        return errors;
    }

    /// <summary>
    /// Validates test input against the manifest's input schema
    /// </summary>
    public ValidationResult ValidateAgainstSchema(TestCase testCase, System.Text.Json.Nodes.JsonNode inputSchema)
    {
        var errors = new List<string>();

        try
        {
            var schema = JsonSchema.FromText(inputSchema.ToJsonString());
            var instance = JsonDocument.Parse(testCase.Input.ToJsonString()).RootElement;

            var result = schema.Evaluate(instance);

            if (!result.IsValid)
            {
                errors.Add($"Test '{testCase.Name}' input does not match input_schema:");
                if (result.HasErrors)
                {
                    foreach (var error in result.Errors!)
                    {
                        errors.Add($"  - {error.Key}: {error.Value}");
                    }
                }
            }
        }
        catch (Exception ex)
        {
            errors.Add($"Failed to validate test input: {ex.Message}");
        }

        return new ValidationResult
        {
            IsValid = errors.Count == 0,
            Errors = errors
        };
    }

    /// <summary>
    /// Validates a test case from JSON string
    /// </summary>
    public ValidationResult ValidateJson(string json)
    {
        try
        {
            var testCase = JsonSerializer.Deserialize(json, McpkgJsonContext.Default.TestCase);
            if (testCase == null)
            {
                return ValidationResult.Failure("Failed to parse test case JSON");
            }

            return Validate(testCase);
        }
        catch (JsonException ex)
        {
            return ValidationResult.Failure($"Invalid JSON: {ex.Message}");
        }
    }
}
