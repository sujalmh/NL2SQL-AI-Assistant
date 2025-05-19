import google.generativeai as genai
import pandas as pd
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def visualise(df: pd.DataFrame, output_path, model_name="gemini-2.0-flash", max_retries=5) -> None:
    """
    Generate a high-quality, interactive data visualization using Google Gemini and Python libraries.

    Args:
        df (pd.DataFrame): The input dataframe containing the data.
        output_path (str): File path to save the generated visualization.
        model_name (str): Gemini model to use (default: gemini-2.0-flash)
        max_retries (int): Max attempts to retry visualization generation upon error.

    Returns:
        None
    """
    try:
        data_description = df.to_string(index=False)
    except Exception as e:
        print("Error while describing data:", e)
        return

    base_prompt = f"""
    You are a professional data visualization expert skilled in **creating advanced, high-quality, and visually appealing charts**.

    ### **Task:**
    Analyze the given dataset and determine the most **effective and aesthetically refined way to visualize it** while ensuring:
    - **Accuracy:** Proper representation of the data without altering its meaning.
    - **Professional Design:** Use **modern, aesthetic layouts**, color schemes, and clean labels.
    - **Advanced Visualization Libraries:** Use **Seaborn, or Bokeh**.
    - **High Readability & Engagement:** Include **smooth animations, interactivity, tooltips, gradients**.
    - **Scalability:** Handle large datasets gracefully.

    ### **Dataset Description:**
    {data_description}

    ### **Output Format:**
    - **Strictly return only executable Python code** inside triple backticks (```python) and nothing else.
    - The code should:
      - Import all necessary libraries.
      - Generate the most **aesthetic and professional** visualization.
      - Use **interactive elements**, **gradient color scales**, and **modern styling**.
      - Maintain proper axis labels, legends, and a refined **layout for readability**.
      - Save the graph to **{output_path}**.
      - Do not use `tkinter`, `plt.show()`, or any GUI preview calls.

    ### Hard Requirements:
      - DO NOT use `tkinter`, `matplotlib.pyplot.show()`, `GUI`, or any windowed visual interface.
      - ONLY generate code that **saves the plot** to '{output_path}' without any UI.

    """

    model_instance = genai.GenerativeModel(model_name)

    for attempt in range(1, max_retries + 1):
        try:
            print(f"\n🌀 Attempt {attempt}: Generating visualization prompt...")
            response = model_instance.generate_content(base_prompt)
            code_match = re.search(r"```python\n(.*?)```", response.text, re.DOTALL)

            if not code_match:
                print("❌ No valid Python code block found in model response.")
                continue

            extracted_code = code_match.group(1).strip()
            print("⚙️ Running generated code...\n")
            exec(extracted_code)
            print("✅ Visualization generated successfully.")
            return output_path # Exit loop if execution succeeds

        except Exception as e:
            print(f"🚨 Error during execution: {e}")
            error_feedback = f"\n\n⚠️ The previous code caused the following error:\n{e}\n\nFix it and regenerate the full corrected code.Saving graph to image is important with {output_path}"
            base_prompt += error_feedback
            if attempt == max_retries:
                print("❌ Max retries reached. Unable to generate a working visualization.")
                return None
