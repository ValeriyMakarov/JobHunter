# JobHunter

CLI application for collecting and analyzing vacancies from Linkedin.

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
- Vacancy data analysis with "AI"
- Local data storage
- Configuration management
- CLI interface

## Technologies

- Python
- Pydantic
- Playwright
- Google-genai
- Openpyxl

## Installation

```
git clone https://github.com/ValeriyMakarov/JobHunter.git

cd jobhunter

python -m venv venv

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```
## Usage

### Run application:

1. From IDE:
```
python -m jobhunter
```

2. From command line:
```
cd /d "{path_to_the_project_folder}src"

"{path_to_the_project_folder}\venv\Scripts\python.exe" -m jobhunter
```
or
```
cd /d "{path_to_the_project_folder}"

run.bat
```

3. Or create a desktop shortcut to "{path_to_the_project_folder}\run.bat"

### Configuration

Application stores user-specific configuration and application data separately from source code in "C:...\AppData\Local\JobHunter". 

### Example:

1. Start program
2. Fill required settings and data about yourself
3. Enter "process"
4. Enter "exit"

## Future Improvements
 - Desktop application interface
 - Additional data sources
 - Extended vacancy analysis
 - Data autofill during application submission
