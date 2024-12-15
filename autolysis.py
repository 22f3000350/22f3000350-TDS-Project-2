# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pandas",
#     "seaborn",
#     "matplotlib",
#     "requests",
#     "chardet" 
# ]
# ///

import os
import sys
import subprocess
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import chardet
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# Function to ensure all dependencies are installed
def install_dependencies():
    required_packages = ["pandas", "seaborn", "matplotlib", "requests", "chardet"]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions" 
MODEL = "gpt-4o-mini"
AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")

if not AIPROXY_TOKEN:
    raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")

def send_to_openai(prompt, detail="default"):
    """Send a prompt to the OpenAI API and return the response."""
    response = requests.post(
        API_URL,
        headers={"Authorization": f"Bearer {AIPROXY_TOKEN}"},
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "Summarize the data analysis."},
                {"role": "user", "content": prompt}
            ]
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

def execute_with_timeout(func, timeout, *args, **kwargs):
    """Execute a function with a timeout."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print(f"Function '{func.__name__}' exceeded the timeout of {timeout} seconds.")
            return ""  # Return empty string if timeout occurs

def summarize_data_overview(df):
    info = df.info(buf=None)
    description = df.describe().to_string()
    nulls = df.isnull().sum().to_string()
    summary = f"Info:\n{info}\n\nDescription:\n{description}\n\nNulls:\n{nulls}"
    return send_to_openai(summary)

def clean_missing_data(df):
    threshold = 0.5
    df_cleaned = df.dropna(axis=1, thresh=len(df) * (1 - threshold))
    df_cleaned = df_cleaned.dropna()
    return df_cleaned

def detect_outliers_and_anomalies(df):
    results = []
    for column in df.select_dtypes(include=['number']):
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        min_val = q1 - 1.5 * iqr
        max_val = q3 + 1.5 * iqr
        results.append(f"{column}: Q1={q1}, Q3={q3}, IQR={iqr}, Min={min_val}, Max={max_val}")
    return send_to_openai("\n".join(results))

def compute_correlation_summary(df):
    try:
        numerical_df = df.select_dtypes(include=["number"])
        correlation = numerical_df.corr()
        correlation_str = correlation.to_string()
        prompt = f"Here is the correlation matrix:\n{correlation_str}\nSummarize the key insights."
        summary = send_to_openai(prompt)
        return summary
    except Exception as e:
        return f"Error in computing correlation: {e}"

def visualize_numerical_columns(df):
    """Visualize numerical columns using pair plots (up to the last 6 columns)."""
    numerical_cols = df.select_dtypes(include=['number'])
    if not numerical_cols.empty:
        # Ensure to select up to the last 6 numerical columns
        limited_numerical_cols = numerical_cols.iloc[:, -6:]
        if not limited_numerical_cols.empty:
            plt.figure(figsize=(10, 10), dpi=100)
            sns.pairplot(limited_numerical_cols)
            img_path = "numerical_plot.png"
            plt.savefig(img_path)
            plt.close()
            return img_path
        else:
            print("No valid numerical columns found for plotting.")
    else:
        print("No numerical columns found in the dataset.")
    return ""



def visualize_categorical_columns(df):
    """Visualize categorical columns using bar plots."""
    categorical_cols = df.select_dtypes(include=['object', 'category'])
    if not categorical_cols.empty:
        for col in categorical_cols.columns:
            unique_values_count = df[col].nunique()
            if unique_values_count > 30:
                continue
            plt.figure(figsize=(8, 8), dpi=100)
            sns.countplot(y=col, data=df, order=df[col].value_counts().index)
            img_path = f"{col}_plot.png"
            plt.savefig(img_path)
            plt.close()
            return img_path
    return ""

def main(csv_file):
    with open(csv_file, 'rb') as f:
        result = chardet.detect(f.read())
        encoding = result['encoding']

    df = pd.read_csv(csv_file, encoding=encoding)
    all_summaries = []

    with open("README.md", "w") as readme:
        readme.write("# Automated Data Analysis\n\n")

        # Data Overview
        summary_1 = execute_with_timeout(summarize_data_overview, 60, df)
        all_summaries.append(f"## Data Overview\n{summary_1}")
        readme.write(f"## Data Overview\n{summary_1}\n\n")

        # Clean Data
        df = execute_with_timeout(clean_missing_data, 60, df)

        # Outlier Detection
        summary_3 = execute_with_timeout(detect_outliers_and_anomalies, 60, df)
        all_summaries.append(f"## Outlier Detection\n{summary_3}")
        readme.write(f"## Outlier Detection\n{summary_3}\n\n")

        # Correlation Analysis
        summary_4 = execute_with_timeout(compute_correlation_summary, 60, df)
        all_summaries.append(f"## Correlation Matrix\n{summary_4}")
        readme.write(f"## Correlation Matrix\n{summary_4}\n\n")

        # Numerical Visualization
        img_path_5 = execute_with_timeout(visualize_numerical_columns, 30, df)
        if img_path_5:
            readme.write(f"## Numerical Visualization\n![Numerical Plot]({img_path_5})\n\n")

        # Categorical Visualization
        img_path_6 = execute_with_timeout(visualize_categorical_columns, 30, df)
        if img_path_6:
            readme.write(f"## Categorical Visualization\n![Categorical Plot]({img_path_6})\n\n")

        # Final Story Generation
        full_context = "\n\n".join(all_summaries)
        final_story = execute_with_timeout(send_to_openai, 60, f"Here is the complete analysis:\n\n{full_context}")
        readme.write(f"## Final Story\n{final_story}\n\n")

if __name__ == "__main__":
    install_dependencies()
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <csv_file>")
        sys.exit(1)
    main(sys.argv[1])
