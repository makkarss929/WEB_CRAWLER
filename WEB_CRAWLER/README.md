# RAPPO Project

## System and Coding Architecture


## Tools and Frameworks used:

1. Python - Programming Language
2. Requests-html and BeautifulSoup - for webscraling and webscrapping
3. Postgres and Pgvector - as database and vectordb
4. FastAPI - for backend
5. Docker - for containerisation and deployment


## Input Schema `/ingestion`


```bash
{
  "url": "https://www.datadoghq.com/case-studies"
}
```

## Input Schema `/query`


```bash
{
  "query": "List champions that are working in Security Space"
}
```
## Output Schema


```json
[
  {
    "name": "Roman Garber",
    "role": "Principal Application Security Engineer",
    "company": "Arc XP",
    "location": "Chicago, IL",
    "aspiration": "Startup Advisory Roles",
    "source_page": "https://www.datadoghq.com/case-studies/arcxp-2023",
    "technical_expertise": "Application Security, Cloud Security"
  },
  {
    "name": "Eloi Barti",
    "role": "Head of Platform Security",
    "company": "Glovo",
    "location": "Barcelona, Spain",
    "aspiration": "Startup Advisory Roles",
    "source_page": "https://www.datadoghq.com/case-studies/glovo",
    "technical_expertise": "Cloud Security Management, Security Integration, AWS"
  },
  {
    "name": "Christian Kornacker",
    "role": "DevOps Lead",
    "company": "Marketplacer",
    "location": "Australia",
    "aspiration": "Interested in compliance and security solutions",
    "source_page": "https://www.datadoghq.com/case-studies/marketplacer",
    "technical_expertise": "Cloud Security, AWS, Infrastructure as Code"
  },
  {
    "name": "Kelly Bettendorf",
    "role": "Security Engineer",
    "company": "Stavvy",
    "location": "Boston, MA",
    "aspiration": "Startup Advisory Roles",
    "source_page": "https://www.datadoghq.com/case-studies/stavvy",
    "technical_expertise": "Cloud Security, Incident Detection, Security Posture Evaluation"
  },
  {
    "name": "Joel Henning",
    "role": "Security Engineer",
    "company": "The Browser Company",
    "location": "New York City, NY",
    "aspiration": "Angel Investing",
    "source_page": "https://www.datadoghq.com/case-studies/the-browser-company",
    "technical_expertise": "CI/CD, Security Engineering"
  }
]
```

## Deployment Instructions

1. clone the `repo`.
2. Place `.env` in root of folder.

### Execute API using Docker

```bash
docker build -t rag .
docker run -p 5001:5001 rag
```

### Execute API using virtual environments


```bash
cd RAG/
python3 -m venv venv
# Linux
source venv/bin/activate
# windows
.\venv\Scripts\activate.bat

pip install -r requirements.txt

python app.py
```