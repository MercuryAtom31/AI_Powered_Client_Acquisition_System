# AI-Powered Client Acquisition System

An intelligent system for discovering, analyzing, and engaging potential clients through automated web scraping, SEO analysis, and personalized outreach.

## Features

- **Website Discovery & Categorization**
  - Automated web crawling
  - Platform identification (WordPress, Shopify, etc.)
  - Business website filtering

- **SEO Analysis**
  - On-page SEO element analysis
  - Keyword extraction
  - Performance metrics

- **Contact Information Extraction**
  - Email address discovery
  - Phone number extraction
  - Social media link identification

- **AI-Powered Personalization**
  - GPT-powered email generation
  - Context-aware pitch customization
  - Multi-channel outreach

- **Tracking & Analytics**
  - Outreach status monitoring
  - Conversion tracking
  - Performance reporting

## Project Structure

```
ai_client_acquisition/
├── discovery/           # Website discovery and crawling
├── analysis/           # SEO and content analysis
├── extraction/         # Contact information extraction
├── personalization/    # AI-powered content generation
├── outreach/          # Email sending and tracking
├── database/          # Database models and migrations
├── api/               # REST API endpoints
└── utils/             # Shared utilities
```

## Setup

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd ai-client-acquisition
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

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/client_acquisition

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# SendGrid
SENDGRID_API_KEY=your_sendgrid_api_key
SENDER_EMAIL=your_verified_sender_email

# Scraping
MAX_CONCURRENT_REQUESTS=5
REQUEST_DELAY=2
```

## Usage

1. Start the discovery process:
   ```bash
   python scripts/discover.py --seed-urls urls.txt
   ```

2. Run SEO analysis:
   ```bash
   python scripts/analyze.py --batch-size 100
   ```

3. Generate and send personalized outreach:
   ```bash
   python scripts/outreach.py --template templates/pitch.txt
   ```

4. View analytics dashboard:
   ```bash
   python scripts/dashboard.py
   ```

## Development

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation for API changes
- Use type hints for better code maintainability

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details 