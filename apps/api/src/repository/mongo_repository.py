import json
import os
import subprocess
import time
from datetime import datetime, timedelta

import certifi
from pymongo import MongoClient
import requests
from urllib.parse import urlparse


class MongoDbCredentials:
    def __init__(self, username: str, password: str, expiration: datetime):
        self.username = username
        self.password = password
        self.expiration = expiration


class MongoRepository:
    MONGO_CERTIFICATE_PATH = "./MongoCert.pem"

    def __init__(self, config_service, logger):
        self.config_service = config_service
        self.logger = logger
        self.mongo_instance_url = self.config_service.get("API_MONGODB_API_DB_URL")
        self.vault_credentials_path = os.getenv(
            "MONGODB_ATLAS_VAULT_CREDENTIALS_PATH", "/v1/database/static-creds/"
        )
        self.mongo_db_atlas_vault_role = os.getenv("MONGODB_ATLAS_VAULT_ROLE")
        self.is_mongo_db_atlas = (
            self.mongo_instance_url is not None
            and "mongodb.net" in self.mongo_instance_url
        )
        self.database = None
        self.mongo_db_atlas_credentials = None
        self.mongo_client = None

    async def create_certificate_file(self, certificate: str):
        self.logger.info(
            f"Attempting to write Mongo certificate to [{self.MONGO_CERTIFICATE_PATH}] with certificate of length [{len(certificate)}]."
        )
        try:
            with open(self.MONGO_CERTIFICATE_PATH, "w") as cert_file:
                cert_file.write(certificate)
            self.logger.info(
                f"Mongo certificate was successfully written to [{self.MONGO_CERTIFICATE_PATH}]."
            )
        except Exception as error:
            self.logger.error(
                f"There was an error writing the Mongo certificate to [{self.MONGO_CERTIFICATE_PATH}]."
            )
            raise

    @staticmethod
    def replace_mongo_db_credentials_in_url(
        old_url: str, new_username: str, new_password: str
    ) -> str:
        if "@" in old_url:
            # URL has existing credentials
            head, tail = old_url.split("@")
            scheme = head.split("://")[0]
            return f"{scheme}://{new_username}:{new_password}@{tail}"
        else:
            # URL has no credentials
            scheme_and_rest = old_url.split("://")
            scheme = scheme_and_rest[0]
            host_part = scheme_and_rest[1]
            return f"{scheme}://{new_username}:{new_password}@{host_part}"

    @staticmethod
    def set_credentials_expiration_date(
        expiration_in_seconds: int,
        percentage_of_lease_until_expiration: int = 90,
        current_date: datetime = None,
    ) -> datetime:
        if current_date is None:
            current_date = datetime.now()
        return current_date + timedelta(
            seconds=expiration_in_seconds * (percentage_of_lease_until_expiration / 100)
        )

    @staticmethod
    def are_mongo_db_atlas_credentials_expired(
        credentials: MongoDbCredentials, current_date: datetime = None
    ) -> bool:
        if current_date is None:
            current_date = datetime.now()
        return credentials is None or current_date >= credentials.expiration

    async def get_vault_token_using_kubernetes_jwt(self):
        vault_namespace = self.config_service.get("VAULT_NAMESPACE")
        vault_url = self.config_service.get("VAULT_URL")

        parameters = {
            "vaultNamespace": vault_namespace,
            "vaultUrl": vault_url,
        }
        jwt_file_location = parameters.get(
            "jwtFileLocation", "/var/run/secrets/kubernetes.io/serviceaccount/token"
        )
        with open(jwt_file_location, "r") as jwt_file:
            kubernetes_jwt = jwt_file.read()
        self.logger.info(
            f"JWT retrieved successfully starting with {kubernetes_jwt[:4]}"
        )
        self.logger.info(
            f"Vault config passed from entrypoint: namespace {parameters['vaultNamespace']}; url {parameters['vaultUrl']}"
        )

        vault_role = self.config_service.get("VAULT_ROLE_NAME")
        response = requests.post(
            parameters["vaultUrl"],
            json={
                "role": vault_role,
                "jwt": kubernetes_jwt,
            },
            headers={
                "X-Vault-Namespace": parameters["vaultNamespace"],
                "Content-Type": "application/json",
            },
        )
        vault_token = response.json().get("auth", {}).get("client_token")
        self.logger.info(
            f"Vault token {'not ' if not vault_token else ''}retrieved successfully{' starting with ' + vault_token[:4] if vault_token else '.'}"
        )
        return vault_token

    async def get_vault_token_using_aws_auth(self):
        jwt_file_location = self.config_service.get(
            "AWS_WEB_IDENTITY_TOKEN_FILE",
            "/var/run/secrets/eks.amazonaws.com/serviceaccount/token",
        )
        with open(jwt_file_location, "r") as jwt_file:
            aws_token = jwt_file.read()
        self.logger.info(f"AWS service account token retrieved: {aws_token[:4]}")
        self.logger.info(
            "Getting Vault token using MPC CLI command: mpc vault perform-aws-auth"
        )
        token_result = subprocess.run(
            ["/usr/bin/mpc", "vault", "perform-aws-auth"],
            stdout=subprocess.PIPE,
            check=True,
        )
        vault_token = token_result.stdout.decode("utf-8").strip()
        self.logger.info(
            f"Vault token {'not ' if not vault_token else ''}retrieved successfully{' starting with ' + vault_token[:4] if vault_token else '.'}"
        )
        return vault_token

    @staticmethod
    def wait(ms: int):
        time.sleep(ms / 1000)

    def retry_with_backoff(self, func, max_retries: int = 4, backoff: int = 4000):
        for attempt in range(max_retries):
            self.logger.info(f"Attempt {attempt} for {func}")
            try:
                response = func()
                self.logger.info(f"Attempt {attempt} response : {response}")
                return response
            except Exception as e:
                self.logger.exception(
                    f"Attempt {attempt} for function ${func} failed with {e}"
                )
                if attempt == max_retries - 1:
                    raise
                self.wait(backoff)
                backoff *= 2

    async def get_mongo_db_credentials(self):
        # Vault URL has domain plus cluster and namespace details,
        # get vault server from the full URL
        vault_url = self.config_service.get("VAULT_URL")
        parsed_url = urlparse(vault_url)
        server_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        role_url = (
            f"{server_url}{self.vault_credentials_path}{self.mongo_db_atlas_vault_role}"
        )

        vault_namespace = self.config_service.get("VAULT_NAMESPACE")
        if self.config_service.get("VAULT_USE_AWS_AUTH", False) == "true":
            vault_token = await self.get_vault_token_using_aws_auth()
        else:
            vault_token = await self.get_vault_token_using_kubernetes_jwt()
        vault_resp = requests.get(
            role_url,
            headers={
                "X-Vault-Token": vault_token,
                "X-Vault-Namespace": vault_namespace,
            },
        )
        self.logger.info(
            f"Vault DB credentials response status code: {vault_resp.status_code} response"
        )
        self.logger.info(f"Vault namespace  {vault_namespace}")
        return vault_resp.json()

    async def get_database(self):
        if self.is_mongo_db_atlas and self.are_mongo_db_atlas_credentials_expired(
            self.mongo_db_atlas_credentials
        ):
            self.logger.info(
                f"Renewing credentials due to [{self.mongo_db_atlas_credentials.expiration if self.mongo_db_atlas_credentials else 'no credentials available'}]"
            )
            try:
                # Reset the connection before updating credentials
                await self.reset_connection()

                mongo_db_credentials_response = await self.get_mongo_db_credentials()

                is_using_static_role = self.vault_credentials_path.endswith(
                    "/static-creds/"
                ) and self.mongo_db_atlas_vault_role.endswith("static-role")
                lease = (
                    mongo_db_credentials_response["data"]["ttl"]
                    if is_using_static_role
                    else mongo_db_credentials_response["lease_duration"]
                )
                expiration_datetime = self.set_credentials_expiration_date(lease)
                self.logger.info(
                    f"Retrieved dynamic dev credentials, lease: {lease}, expiration_datetime[{expiration_datetime}]"
                )

                self.mongo_db_atlas_credentials = MongoDbCredentials(
                    username=mongo_db_credentials_response["data"]["username"],
                    password=mongo_db_credentials_response["data"]["password"],
                    expiration=expiration_datetime,
                )
                self.logger.info(
                    f"MongoDB credentials {'not ' if not self.mongo_db_atlas_credentials else ''}retrieved successfully with username {self.mongo_db_atlas_credentials.username} and expiration {self.mongo_db_atlas_credentials.expiration}"
                )

                # Update the URL with new credentials
                old_url = self.mongo_instance_url

                self.mongo_instance_url = self.replace_mongo_db_credentials_in_url(
                    old_url,
                    self.mongo_db_atlas_credentials.username,
                    self.mongo_db_atlas_credentials.password,
                )

                self.logger.info(
                    f"MongoDB URL updated with username {self.mongo_db_atlas_credentials.username}"
                )

            except Exception as error:
                self.logger.exception(
                    f"Error encountered while getting MongoDB Atlas credentials from Vault. {error}"
                )
                raise Exception(
                    f"Error encountered while getting MongoDB Atlas credentials from Vault. {error}"
                )

        try:
            if self.database is None:
                certificate = self.config_service.get("API_MONGO_DB_CERTIFICATE", False)
                if certificate and not self.is_mongo_db_atlas:
                    await self.create_certificate_file(certificate)

                tlsCAFile = (
                    self.MONGO_CERTIFICATE_PATH
                    if certificate and not self.is_mongo_db_atlas
                    else None
                )

                self.mongo_client = MongoClient(self.mongo_instance_url, tlsCAFile)

                self.logger.info("Mongo client successfully created.")

                self.retry_with_backoff(lambda: self.mongo_client.admin.command("ping"))

                self.logger.info("Connected to MongoDB Server.")

                self.database = self.mongo_client.get_database()

                self.logger.info("Connected to MongoDB database.")

                await self.init_db()

                return self.database
            return self.database
        except Exception as error:
            self.logger.exception(
                f"Error encountered while establishing connection to the database. {error}"
            )
            raise Exception(f"Unable to establish connection to the database. {error}")

    async def init_db(self):
        pass

    async def get_collection(self, collection_name: str):
        self.logger.info("Getting collection: %s", collection_name)

        return (await self.get_database()).get_collection(collection_name)

    def closeConnection(self):
        self.mongo_client.close()
        self.logger.info("Mongo client connection closed.")

    async def reset_connection(self):
        """Reset the database connection by closing the current connection and clearing references."""
        try:
            if self.mongo_client:
                self.mongo_client.close()
                self.logger.info(
                    "Existing Mongo client connection closed during reset."
                )

            self.mongo_client = None
            self.database = None
            self.logger.info("Database connection reset successfully.")
        except Exception as error:
            self.logger.exception(
                f"Error encountered while resetting database connection. {error}"
            )
            raise Exception(f"Unable to reset database connection. {error}")
