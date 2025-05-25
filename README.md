# AI-Powered Client Acquisition System

A desktop application that performs AI-powered SEO analysis on websites and integrates with HubSpot CRM.

## Features

- URL input and analysis
- Local AI-powered SEO analysis using Gemma via Ollama
- Contact information extraction
- Detailed SEO recommendations
- HubSpot CRM integration
- Local SQLite storage
- Export results to CSV

## Prerequisites

1. Python 3.8 or higher
2. Ollama installed on your system
3. HubSpot account (optional)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd AI_Powered_Client_Acquisition_System
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Ollama:
   - Windows: Download from https://ollama.ai/download
   - Mac: `brew install ollama`
   - Linux: Follow instructions at https://ollama.ai/download

5. Pull the Gemma model:
```bash
ollama pull gemma:2b
```

6. Create a `.env` file in the project root:
```
HUBSPOT_API_KEY=your_hubspot_api_key_here
```

## Usage

1. Start the application:
```bash
streamlit run dashboard_app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Enter URLs to analyze (one per line) in the text area

4. Click "Analyze URLs" to start the analysis

5. View results in the dashboard:
   - Summary statistics
   - Detailed analysis per URL
   - SEO recommendations
   - Contact information

6. Optional: Push results to HubSpot using the "Push to HubSpot" button

## Database

The application uses SQLite for local storage. The database file (`client_acquisition.db`) is created automatically when you first run the application.

## Exporting Results

You can export the analysis results to CSV using the "Download Analysis Results" button in the dashboard.

## Troubleshooting

1. If Ollama is not working:
   - Ensure Ollama is running: `ollama serve`
   - Check if the model is downloaded: `ollama list`

2. If HubSpot integration fails:
   - Verify your API key in the `.env` file
   - Check your HubSpot account permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 