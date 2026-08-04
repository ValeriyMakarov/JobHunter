# JobHunter

CLI application for collecting and analyzing vacancies from Linkedin (and more in the future).

## Overview

JobHunter is a Python CLI application that automates the job search.

The application is designed to:
- collect vacancy information;
- analyze vacancy data;
- store information about vacancies;
- manage application-related data.

## Features

- Vacancies collecting
- Vacancy data parsing
- Vacancy data analysis
- Local data storage
- Configuration management
- CLI interface

## Technologies

- Python
- Pytest
- Pydantic
- Playwright
- SQLite
- Git

## Installation

```
git clone https://github.com/ValeriyMakarov/JobHunter.git

cd JobHunter

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```
Usage

Run application:

python -m jobhunter
Configuration

Application stores user-specific configuration and application data separately from source code.

Example:

JobHunter/
├── settings/
├── saves/
└── other user data
Testing

Run tests:

pytest
Architecture

The project uses a package-based architecture with separated responsibilities:

CLI layer handles user interaction.
Parser layer handles data collection.
Storage layer manages data persistence.
Configuration layer manages application settings.
Development

The project follows src layout:

project/
├── src/
│   └── jobhunter/
├── tests/
├── README.md
└── pyproject.toml
Future Improvements
Desktop application interface
Additional data sources
Extended vacancy analysis
License

MIT


Я специально убрал:
- CI/CD;
- Docker;
- badges;
- "production-ready";
- AI;
- сложную архитектуру;
- то, чего пока нет.