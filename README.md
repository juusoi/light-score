# NFL Scores and Standings

This project aims to provide real-time NFL scores and standings through a user-friendly interface. It utilizes a Python-centric technology stack, featuring a Django frontend, FastAPI backend, and Firestore database, all hosted on Google Cloud Platform.

## Technology Stack

- **Frontend**: Django
- **Backend**: FastAPI
- **Database**: Firestore (Google Cloud Firestore)
- **Serverless Function**: Google Cloud Functions
- **CI/CD**: GitHub Actions
- **Cloud Services**: Google Cloud Platform (GCP) - including Compute Engine, Cloud Run, App Engine, and Stackdriver

## Architecture Overview

The project consists of a Django application for the frontend, communicating with a FastAPI backend. Firestore serves as the database, storing NFL scores and standings. Google Cloud Functions are used to fetch data from an external NFL API. The architecture is designed for scalability and efficiency, leveraging GCP's robust cloud infrastructure.

## Getting Started

### Prerequisites

- Python 3.11+
- Docker (for containerization)
- GCP Account

## Installation

1. Clone the repository: git clone [repository-url]
2. Follow the setup instructions in each component's directory (frontend, backend, serverless).

## Development Guidelines

- **Code Style**: Follow PEP 8 guidelines for Python code.
- **Commit Messages**: Use clear, concise commit messages, describing the changes made.
  **Branching Strategy**: Feature branching workflow (create a new branch for each feature).

## Testing

- **Backend**: Write unit and integration tests using pytest.
- **Frontend**: Conduct manual testing and consider using a framework like Playwright for automated UI tests.

## Deployment

- Deployment processes are automated via GitHub Actions.
- Pushing code (approved PR) to the main branch triggers deployment to the test environment.
- After testing, code can be deployed to the production environment.

## Contributing

Contributors are welcome! Please read the contributing guidelines for the process of submitting pull requests to us.

## Versioning

We use [SemVer](https://semver.org) for versioning. For the versions available, see the tags on this repository.

## Authors and Acknowledgment

- Juuso, Tero - Initial work
- Acknowledgments to YLE text-tv page 235.

## License

This project is licensed under the [MIT License](./LICENSE).
