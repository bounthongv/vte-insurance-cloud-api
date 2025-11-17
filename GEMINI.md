# Project Overview

This project is a Flask-based Python API that provides a comprehensive set of endpoints for managing invoices and expenses. It is designed to interact with a Microsoft SQL Server database and includes features like token-based authentication, signature validation, and data conversion.

## Key Technologies

- **Backend:** Python, Flask
- **Database:** Microsoft SQL Server
- **Libraries:**
  - `pyodbc`: For connecting to the SQL Server database.
  - `python-dotenv`: For managing environment variables.
  - `waitress`: As a production-ready WSGI server.

## Architecture

The application is structured into the following key components:

- **`api.py`:** The main Flask application file that defines the API endpoints for managing invoices. It also includes features like token-based authentication, signature validation, and data conversion from numbers to Laotian words.
- **`expenses_api.py`:** A Flask blueprint that provides a set of endpoints for managing expenses. This includes features for uploading, retrieving, and canceling expenses, as well as tracking their status.
- **`shared_utils.py`:** A collection of helper functions that are used throughout the application. This includes functions for database connection, authentication, signature generation, and string cleaning.
- **`dbConnect.py`:** A script for establishing and testing the connection to the Microsoft SQL Server database.

# Building and Running

To run the application, you will need to have Python and the required libraries installed. You can install the libraries using pip:

```bash
pip install -r requirements.txt
```

You will also need to set up the following environment variables:

- `DB_HOST`: The hostname of the database server.
- `DB_PORT`: The port number for the database server.
- `DB_USER`: The username for the database.
- `DB_PASSWORD`: The password for the database.
- `DB_NAME`: The name of the database.
- `API_TOKEN`: The bearer token for authenticating API requests.

Once the environment variables are set, you can run the application using the following command:

```bash
python api.py
```

The API will be available at `http://localhost:5000`.

# Development Conventions

- **Authentication:** The API uses a token-based authentication system to protect the endpoints. All requests must include a valid bearer token in the `Authorization` header.
- **Signature Validation:** The API uses a signature validation mechanism to ensure the integrity and authenticity of the requests. The client must generate a signature using a secret key and include it in the request.
- **Database Interaction:** The application uses the `pyodbc` library to connect to the Microsoft SQL Server database. All database operations are performed using SQL queries.
- **Error Handling:** The API includes comprehensive error handling to provide informative error messages to the client.
- **Code Style:** The code follows the standard Python conventions and includes docstrings to explain the purpose of each function.
