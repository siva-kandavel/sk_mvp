import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    organization=os.getenv("OPENAI_ORG_ID")
)

api_key = os.getenv("OPENAI_API_KEY")
print("API Key Loaded:", api_key[:5] + "..." if api_key else "Not Found")

def generate_test_case(requirement_prompt: str, style="gherkin"):
    """
    Generate a test case using GPT-4 from a given requirement.

    :param requirement_prompt: The natural language description of the requirement.
    :param style: 'gherkin' or 'unittest' or 'pytest' etc.
    :return: Generated test case as a string.
    """

    user_prompt = f"Generate a {style} test case for the following requirement:\n\n\"\"\"\n{requirement_prompt}\n\"\"\""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a software testing expert skilled in generating test cases."},
                {"role": "user", "content": user_prompt}
            ]
        )
        test_case = response.choices[0].message.content
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
