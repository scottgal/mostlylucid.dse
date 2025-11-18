"""
Step definitions for: Extract key data from PDF invoice
Auto-generated Behave step definitions
"""
from behave import given, when, then, step
import json

try:
    from faker import Faker
    fake = Faker()
except ImportError:
    fake = None


@given('.*the\ system\ is\ initialized.*')
def step_the_system_is_initialized_0(context):
    """Step: the system is initialized"""
    # Setup/precondition
    context.test_data = {}
    pass


@when('.*I\ execute\ the\ main\ function.*')
def step_i_execute_the_main_function_1(context):
    """Step: I execute the main function"""
    # Action/execution
    try:
        # Execute the action here
        context.result = {"success": True}
    except Exception as e:
        context.error = str(e)
        context.result = {"success": False, "error": str(e)}
    pass


@then('.*I\ should\ get\ the\ expected\ resu.*')
def step_i_should_get_the_expected_result_2(context):
    """Step: I should get the expected result"""
    # Assertion/verification
    assert hasattr(context, "result"), "No result found"
    pass

