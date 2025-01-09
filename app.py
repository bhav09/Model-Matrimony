import streamlit as st
import pandas as pd
import os
import time
import google.generativeai as genai
from google.cloud import storage
import io
from dotenv import load_dotenv
import ast

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_KEY"))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "service-account-key.json"

# Create the model
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 50,
    "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
)

# Set page config
st.set_page_config(
    page_title="Model Matrimony",
    page_icon="❤️",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #DA70D6;
    }
    .element-container:has(div.stSuccessMessage) div[data-testid="stMarkdownContainer"] p {
        color: #953553 !important;
    }
    .element-container:has(div.stSuccessMessage) {
        background-color: rgba(149, 53, 83, 0.1) !important;
    }
    .element-container:has(div.stSuccessMessage) svg {
        fill: #953553 !important;
    }
    .model-table {
        margin-top: 1rem;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title with emoji
st.title("Model Matrimony ❤️")

@st.cache_data
def load_data():
    """Load data from Google Cloud Storage"""
    try:
        # Initialize GCS client
        storage_client = storage.Client()
        
        # Get bucket and blob
        bucket = storage_client.get_bucket(os.getenv("BUCKET_NAME"))
        blob = bucket.blob("llm_leaderboard.csv")
        
        # Download the content to a string buffer
        content = blob.download_as_string()
        
        # Convert to pandas DataFrame
        df = pd.read_csv(io.BytesIO(content))
        return df
    except Exception as e:
        st.error(f"Error loading data from GCS: {str(e)}")
        return None


def read_file(filename):
    with open(filename, 'r') as file:
        return file.read()

def create_model_dataframe(model_data, benchmarks):
    """Create a DataFrame for model display"""
    # Extract model name without path
    model_name = model_data['fullname'].split('/')[-1] if '/' in model_data['fullname'] else model_data['fullname']
    
    # Create base data
    base_data = {
        'Metric': ['Model Name', 'Size (B)', 'Average Score', 'Architecture', 'License'],
        'Value': [
            model_name,
            f"{model_data['#Params (B)']:.2f}",
            f"{model_data['Average ⬆️']:.2f}",
            model_data['Architecture'],
            model_data['Hub License']
        ]
    }
    
    # Add benchmark scores
    for benchmark in benchmarks:
        if benchmark in model_data and benchmark != "Average ⬆️":
            base_data['Metric'].append(f"{benchmark} Score")
            base_data['Value'].append(f"{model_data[benchmark]:.2f}")
    
    return pd.DataFrame(base_data)

def process_task(task, model_size):
    # Initialize progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Step 1: Load data (20%)
    status_text.text("Loading benchmark data...")
    data = load_data()
    data = data[(data['Official Providers'])&(data['Available on the hub'])&(~data['Flagged'])]
    data = data.sort_values("Average ⬆️", ascending=False)
    progress_bar.progress(20)
    time.sleep(0.5)
    
    # Step 2: Initialize Gemini (40%)
    status_text.text("Initializing Gemini...")
    progress_bar.progress(40)
    time.sleep(0.5)
    
    # Step 3: Get benchmark selection prompt (60%)
    status_text.text("Processing your task requirements...")
    benchmark_select = read_file("prompts/benchmark_select.txt")
    benchmark_list = read_file("prompts/benchmark_list.txt")
    benchmark_select = benchmark_select.format(benchmarks=benchmark_list, input=task)
    
    # Get benchmark recommendations
    response = model.generate_content(benchmark_select).text.replace("\n", "")
    print(response)
    
    # Parse the response and extract benchmarks
    try:
        recommended_benchmarks = ast.literal_eval(response)
        
        # Remove any empty strings or whitespace
        recommended_benchmarks = [b.strip() for b in recommended_benchmarks if b.strip()]
        
        # If no valid benchmarks found, use default
        if not recommended_benchmarks:
            recommended_benchmarks = ["Average ⬆️"]
    
    except Exception as e:
        recommended_benchmarks = ["Average ⬆️"]

    progress_bar.progress(60)
    time.sleep(0.5)
    
    # Step 4: Filter models (80%)
    status_text.text("Finding your perfect model matches...")
    
    available_models = data.sort_values(by=recommended_benchmarks, ascending=False).reset_index(drop=True)
    overall_best_model = available_models.iloc[0]
    
    # Get best model within size constraint
    size_filtered_models = available_models[
        available_models['#Params (B)'] <= model_size
    ]
    best_sized_model = size_filtered_models.iloc[0]
    
    progress_bar.progress(80)
    time.sleep(0.5)
    
    # Step 5: Prepare results (100%)
    status_text.text("Preparing results...")
    progress_bar.progress(100)
    # status_text.text("Complete!")
    time.sleep(0.5)
    
    return overall_best_model, best_sized_model, recommended_benchmarks

# Main app interface
with st.container():
    # User input section
    st.markdown("#### Describe Your Task")
    user_task = st.text_area(
        "",
        height=100,
        placeholder="E.g., Chatbot that answers medical questions...",
        label_visibility='hidden'
    )
    
    # Model size slider
    st.markdown("#### Small Model Preference")
    model_size = st.slider(
        "Maximum model size (in billion parameters)",
        min_value=1,
        max_value=50,
        value=15,
        help="Larger models are more capable but require more computational resources"
    )
    
    # Process button
    if st.button("Find My Perfect Match! 💘", type="primary"):
        if user_task:
            try:
                overall_best_model, best_sized_model, recommended_benchmarks = process_task(user_task, model_size)
                
                # Display results in table format
                st.success("Found your perfect matches! 🎉")
                with st.expander("Results"):
                    
                    # Overall Best Model
                    st.markdown("### 🏆 Overall Best Model")
                    overall_df = create_model_dataframe(overall_best_model, recommended_benchmarks)
                    st.table(overall_df)
                    
                    st.markdown("---")
                    
                    # Best Model Within Size Constraint
                    st.markdown(f"### 🎯 Best Model Under {model_size}B Parameters")
                    sized_df = create_model_dataframe(best_sized_model, recommended_benchmarks)
                    st.table(sized_df)
                    
                    # Display Relevant Benchmarks
                    st.markdown("### 📊 Relevant Benchmarks")
                    benchmark_df = pd.DataFrame({
                        'Benchmark': [bench.strip() for bench in recommended_benchmarks if bench.strip()]
                    })
                    st.table(benchmark_df)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
        else:
            st.warning("Please describe your task first! 🙏")

# Footer
st.markdown(
    "<div style='text-align: center;'>"
    "Built with ❤️ using Streamlit | Don't marry blindly!"
    "</div>",
    unsafe_allow_html=True
)