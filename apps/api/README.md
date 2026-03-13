### Starting the Application using nx (Recommended)

To start the application using nx, follow the steps below:

1. Open the project in the DevContainer.
2. Run the command `nx start api` from the workspace root.

This will automatically install dependencies and start the API on the selected port.

### Starting the Application using uv

To start the application using uv, follow the steps below:

1. Open the project in the DevContainer.
2. Change the directory to the `api` directory by running the command `cd apps/api`.
3. Create and activate a virtual environment:

   ```bash
   uv venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

   Or using standard `venv`:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

4. Install all the necessary packages by running the command `uv sync`. This will ensure that all
   the required dependencies are installed.
5. Start the application by running the command `uv run api`. This will start the API on the
   selected port.

### Starting the Application using Python and pip

To start the application using Python and pip, follow the steps below:

1. Open the project in the DevContainer.

2. Change the directory to the `api` directory by running the command `cd apps/api`.

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use: .venv\Scripts\activate
   ```

4. Install all the necessary packages by running the command `pip install -r requirements.txt`. This
   will install all the required dependencies.

5. Start the application by running the command `python -m src.main`. This will start the API on the
   selected port.

6. To auto reload on file change set the following env variable UVICORN_RELOAD to true, this is
   enabled by default in devcontainer.

#### Running Unit Tests

To run the unit tests, follow the steps below:

1. The unit test files are stored with the suffix `*_test.py`.

2. Change the directory to the `api` directory.

3. If you are using uv, you can execute the tests by running the command `uv run pytest`.

4. If you are using Python and pip, you can run the tests by running the command
   `python3 -m pytest`.

5. To get a test coverage report, you can run the `pytest` with options
   `--cov=src --cov-report=html --cov-fail-under=80`. Open `htmlcov/index.html` to view the report.

Regarding loading and retrieving secrets in OSS2 or DevContainer, please consider the following
guidelines:

1. Polaris based apps uses python-dotenv, it is recommended to follow the approach mentioned in the
   documentation [here](../../README.md#sensitive-values) to store secrets securely during local
   development.
2. For storing secrets in an OSS2-based environment, it is advisable to use a secure vault solution
   like Vault. This ensures that sensitive information is protected and can be accessed securely
   when needed.
3. In your code, use the `os.environ.get("Env_secret")` method to retrieve the secret value. Replace
   "Env_secret" with the actual key corresponding to the secret you want to access. It is crucial to
   avoid hardcoding your secrets directly into your code, especially if you plan to commit it to a
   repository on GitHub.

### Code Formatting with Ruff

Ruff is used for both formatting and linting Python code in this project. To format your code, from
your `api` directory run:

```bash
uv run ruff format src
```

To check formatting without making changes:

```bash
uv run ruff format src --check
```

### Linting with Ruff

To check your code for linting issues, from your `api` directory run:

```bash
uv run ruff check .
```

To automatically fix linting issues, run:

```bash
uv run ruff check . --fix
```

You can configure Ruff's rules by editing the `[tool.ruff]` section in `pyproject.toml`. For more
information on available rules and configuration, see the
[Ruff documentation](https://docs.astral.sh/ruff/).
