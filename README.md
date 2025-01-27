# Web Scraper: Product URL Crawler

A high-performance web crawler designed to extract product URLs from e-commerce websites. Built with Python,
asynchronous I/O, and PostgreSQL for scalable data storage.

---

## Table of Contents

1. [Description](#1-description)
2. [Features](#2-features)
3. [Architecture](#3-architecture)
    - [Detailed System Architecture](#detailed-system-architecture)
    - [Coding Architecture (LLD)](#coding-architecture-lld)
    - [System Flow (HLD)](#system-flow-hld)
4. [Installation](#4-installation)
    - [Local Setup](#local-setup)
    - [Docker Setup](#docker-setup)
5. [Usage](#5-usage)
6. [API Endpoints](#6-api-endpoints)
7. [Future Steps](#7-future-steps)

---

## 1. Description

This crawler efficiently scrapes product URLs from websites using:

- **Hybrid Fetching**: Static pages (HTTP) + dynamic pages (Playwright browser automation).
- **Priority Queue**: Prioritizes URLs matching product page patterns (e.g., `/p/`, `/dp/`, `p-`, `/buy`).
- **Bloom Filter**: Tracks visited URLs to avoid redundant requests.
- **Rate Limiting**: Respects domain crawl delays (configurable per domain).
- **PostgreSQL**: Stores extracted URLs with domain metadata.

---

## 2. Features

- 🚀 **Asynchronous Crawling**: Leverages `asyncio` for concurrent requests.
- 🕸️ **JavaScript Rendering**: Uses Playwright for Single-Page Applications (SPAs).
- 📊 **Metrics Tracking**: Monitors URLs crawled, errors, and product URLs found.
- 🛠️ **Resilient Retries**: Auto-retry failed requests with exponential backoff.
- 🐳 **Dockerized**: Preconfigured PostgreSQL and app containers.

---

## 3. Architecture

### System Flow (HLD)

```mermaid
graph TD
    A[User Request] --> B[FastAPI]
    B --> C{New Crawl?}
    C -->|Yes| D[WebScraper]
    D --> E[PriorityFrontier]
    E --> F[DomainRateLimiter]
    F --> G{Browser Required?}
    G -->|Yes| H[BrowserPool]
    G -->|No| I[aioHTTP]
    H --> J[Playwright]
    I & J --> K[Content Parser]
    K --> L[VisitedURLTracker]
    L --> M[Product Detection]
    M -->|Yes| N[AsyncPostgres]
    M -->|No| O[Link Extractor]
    O --> E
    N --> P[(PostgreSQL)]
    P --> Q[Metrics]
```

### Coding Architecture (LLD)

| Component           | Description                                                           |
|---------------------|-----------------------------------------------------------------------|
| `WebScraper`        | Orchestrates crawling, URL processing, and database batch inserts.    |
| `PriorityFrontier`  | Manages URL queues (high/medium/low priority) for efficient crawling. |
| `BrowserPool`       | Pool of Chromium instances for parallel headless browsing.            |
| `VisitedURLTracker` | Uses a Bloom filter + in-memory set to track visited URLs.            |
| `DomainRateLimiter` | Enforces per-domain crawl delays to avoid IP bans.                    |
| `AsyncPostgres`     | Async PostgreSQL client for bulk inserts and connection pooling.      |
| `ETL`               | Initializes database tables and manages schema migrations.            |
| `HybridFetcher`     | Decides between static (aioHTTP) and dynamic (Playwright) <br/>fetching strategies.|
| `CrawlerMetrics`    | Tracks and reports key performance indicators (URLs crawled, <br/>errors, product URLs detected).|
| `ProductURLsManagement`    | Manages PostgreSQL table operations for storing product URLs and domain metadata.|

### Detailed System Architecture
```mermaid
graph TD
    subgraph User["User Interface"]
        API[FastAPI Endpoints]
        Health[Health Check]
        MetricsAPI[Metrics Dashboard]
    end

    subgraph Core["Core Components"]
        WS[WebScraper]
        PQ[PriorityFrontier]
        BF[VisitedURLTracker]
        RL[DomainRateLimiter]
        HM[HybridFetcher]
        MET[CrawlerMetrics]
    end

    subgraph Browsers["Browser Management"]
        BP[BrowserPool]
        PW[Playwright]
        subgraph Fetch["Fetch Strategies"]
            Static[Static HTTP]
            Dynamic[Dynamic JS]
        end
    end

    subgraph Storage["Data Storage"]
        PG[(PostgreSQL)]
        subgraph Tables
            URLs[product_urls]
            Domains[domain_metadata]
        end
    end

    subgraph Processing["Data Processing"]
        Parser[HTML Parser]
        Extractor[Link Extractor]
        Validator[URL Validator]
        ProdDetect[Product Detector]
    end

    %% Data Flow
    API -->|POST /crawl| WS
    Health -->|GET /| WS
    
    WS -->|URL management| PQ
    WS -->|Rate limiting| RL
    WS -->|Fetch strategy| HM
    
    HM -->|Static| Static
    HM -->|Dynamic| BP
    BP --> PW
    PW --> Dynamic
    
    Static --> Parser
    Dynamic --> Parser
    
    Parser --> ProdDetect
    ProdDetect -->|Yes| URLs
    ProdDetect -->|No| Extractor
    
    Extractor --> Validator
    Validator -->|New URLs| PQ
    Validator -->|URL check| BF
    
    WS -->|Store metrics| MET
    MET --> Domains
    WS -->|Batch insert| URLs
    
    %% Error Handling
    WS -.->|Error logging| EL[(Error Logs)]
    BP -.->|Crash recovery| EL

    %% Styles
    classDef primary fill:#2563eb,stroke:#1e40af,color:white
    classDef secondary fill:#4b5563,stroke:#374151,color:white
    classDef storage fill:#065f46,stroke:#064e3b,color:white
    classDef browser fill:#7c3aed,stroke:#6d28d9,color:white
    classDef processing fill:#d97706,stroke:#b45309,color:white
    
    class API,WS,MET primary
    class PQ,BF,RL,HM,Parser,Extractor,Validator,ProdDetect secondary
    class PG,URLs,Domains,EL storage
    class BP,PW,Static,Dynamic browser
    class Processing processing
```

## 4. Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 13+
- Playwright browsers

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/makkarss929/WEB_CRAWLER.git
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

5. Create a `.env` file with database configuration:
   ```
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   DATABASE_USER=admin
   DATABASE_PASSWORD=your_password
   DATABASE_NAME=crawler_db
   ```

6. Start the app:
   ```
   python -u app.py
   ```

### Docker Setup

1. Make sure Docker and Docker Compose are installed.

2. Create a `.env` file as described above.

3. Build and start the containers:
   ```bash
   docker compose up -d
   ```

## 5. Usage

### Making API Requests

```python
import requests

# Start a crawl
response = requests.post(
    "http://localhost:5001/crawl",
    json={
        "domains": [
            "https://www.flipkart.com/"
        ]
    }
)

# Check health
health = requests.get("http://localhost:5001/")
```

## 6. API Endpoints

- `GET /` - Health check endpoint
    - Returns: `{"status": "ok", "active_scrapers": <count>}`

- `POST /crawl` - Start crawling specified domains
    - Body: `{"domains": ["domain1.com", "domain2.com"]}`
    - Returns: `{"metrics": {
            'urls_crawled': 0,
            'product_urls': 0,
            'avg_response_time': 0,
            'error_rate': 0
        }`

## 7. Future Steps

### Planned Architecture Upgrades

#### 1. RabbitMQ & Celery Integration

- **Distributed Task Queue**: Use RabbitMQ for message brokering and Celery workers for parallel task processing.

#### 2. Redis for Distributed State

- **Visited URL Tracking**: Currently uses in-memory set. Planned upgrade to RedisBloom

#### 3. Monitoring & Metrics

- **Flower Dashboard**: Real-time monitoring of Celery tasks.

### 4. Horizontal Scaling

- **Kubernetes Deployment**: Auto scaling

## License

This project is licensed under the MIT License - see the LICENSE file for details.