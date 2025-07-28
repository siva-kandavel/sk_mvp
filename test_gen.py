import openai
import os
from dotenv import load_dotenv

openai.api_key_path = "/Users/sivakeerthi/PyCharmMiscProject/.env"
# Load API key from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
openai.organization = os.getenv("OPENAI_ORG_ID")


from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    project=os.getenv("OPENAI_ORG_ID"),  # your actual project ID
     )

print("API Key Loaded:", openai.api_key[:5] + "..." if openai.api_key else "Not Found")

def generate_test_case(requirement_prompt: str, style="gherkin"):
    """
    Generate a test case using GPT-4 from a given requirement.

    :param requirement_prompt: The natural language description of the requirement.
    :param style: 'gherkin' or 'unittest' or 'pytest' etc.
    :return: Generated test case as a string.
    """

    system_prompt = "You are a software testing expert skilled in generating test cases."
    user_prompt = f"Generate a {style} test case for the following requirement:\n\n\"\"\"\n{requirement_prompt}\n\"\"\""

    try:
        models = client.models.list()

        for model in models.data:
            print(model.id)

        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "user", "content": "Give me a Gherkin test for user login failure"}
            ]
        )
        test_case = response['choices'][0]['message']['content']
        return test_case

    except Exception as e:
        return f"Error: {str(e)}"


# Example usage
if __name__ == "__main__":
    prompt = input("Enter your requirement: ")
    style = input("Test case format (gherkin/unittest/pytest): ").strip().lower() or "gherkin"
    test = generate_test_case(prompt, style)
    print("\nGenerated Test Case:\n")
    print(test)