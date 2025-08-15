# NFL Scores and Standings

This project aims to provide real-time NFL scores and standings through a user-friendly interface. It utilizes a Python-centric technology stack, featuring a Flask frontend, FastAPI backend, and DynamoDB database, all hosted on Amazon Web Services.

## Technology Stack

- **Frontend**: Flask - see [frontend/README.md](./frontend/README.md)
- **Backend**: FastAPI - see [backend/README.md](./backend/README.md)
- **Database**: DynamoDB (Amazon DynamoDB)
- **Serverless Function**: AWS Lambda
- **CI/CD**: GitHub Actions
- **Cloud Services**: Amazon Web Services (AWS) - including EC2, ECS, Lambda, and CloudWatch

## Architecture Overview

The project consists of a Flask application for the frontend, communicating with a FastAPI backend. DynamoDB serves as the database, storing NFL scores and standings. AWS Lambda functions are used to fetch data from an external NFL API. The architecture is designed for scalability and efficiency, leveraging AWS's robust cloud infrastructure.

## Getting Started

### Prerequisites

- Python 3.13+
- Docker (for containerization)
- AWS Account

## Installation

1. Clone the repository: git clone https://github.com/juusoi/light-score
2. Follow the setup instructions in each component's directory (frontend, backend, functions).

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

- juusoi, firekki - Initial work
- Lemminkyinen - Collaborator
- Acknowledgments to YLE text-tv page 235.

## License

This project is licensed under the [MIT License](./LICENSE).
