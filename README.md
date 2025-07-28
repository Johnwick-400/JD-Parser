# JD Parser: AI-Powered Job Description Extractor 🚀

A powerful and efficient Streamlit web application that uses the Mistral AI API to parse job descriptions from files (PDF, DOCX) or raw text and extract structured data in JSON format.

---

## ✨ Features

-   **Dual Input Modes**: Upload multiple PDF/DOCX files or paste raw text.
-   **AI-Powered Parsing**: Leverages the `mistral-small-latest` model for high-accuracy data extraction.
-   **Structured JSON Output**: Converts unstructured job descriptions into a clean, predictable JSON schema.
-   **Concurrent Processing**: Uses a thread pool to process multiple files simultaneously, ensuring high speed and efficiency.
-   **Error Handling**: Robust error handling for file extraction, API calls, and JSON parsing.
-   **User-Friendly Interface**: A clean and intuitive UI built with Streamlit.
-   **Data Download**: Download the extracted JSON data for each file with a single click.
-   **Performance Metrics**: Displays processing time for each file and provides an overall summary for batch jobs.

---

## 🔧 Tech Stack

-   **Backend**: Python
-   **Web Framework**: Streamlit
-   **AI/NLP**: Mistral AI API
-   **File Parsing**: PyMuPDF (`fitz`), `docx2txt`
-   **API Communication**: `requests`
-   **Concurrency**: `concurrent.futures.ThreadPoolExecutor`

---

## ⚙️ Setup and Installation

Follow these steps to set up and run the project locally.

### 1. Clone the Repository

```bash
git clone https://github.com/Johnwick-400/JD-Parser
```

### 2. Change the Directory

```bash
cd JD_Parser
```
### 3. Install Dependencies 
```bash
pip install -r requirements.txt
```
### 4. Config your mistral api into .env file 
```bash
Add your mistral API in .env
```
### 5. Run this Command to run streamlit App 

```bash
Streamlit run app.py
```

