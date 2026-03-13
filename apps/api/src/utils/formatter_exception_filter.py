from fastapi import FastAPI, Request, Response
from typing import Dict
import logging as logger
from fastapi.exceptions import HTTPException
from starlette.responses import JSONResponse


class FormattedExceptionFilter:
    exception_templates: Dict[int, Dict[str, str]] = {}

    def __init__(self):
        self.exception_templates[500] = {
            "type": "/probs/ApplicationException",
            "title": "Application error occurred",
            "status": str(500),
        }

        self.exception_templates[400] = {
            "type": "/probs/BadRequest",
            "title": "Bad request submitted by client",
            "status": str(400),
        }

        self.exception_templates[401] = {
            "type": "/probs/Unauthorized",
            "title": "Credentials required but not received or invalid",
            "status": str(401),
        }

        self.exception_templates[403] = {
            "type": "/probs/Forbidden",
            "title": "Credentials received but not appropriate for this action",
            "status": str(403),
        }

        self.exception_templates[404] = {
            "type": "/probs/NotFound",
            "title": "The requested resource was not found",
            "status": str(404),
        }

        self.exception_templates[409] = {
            "type": "/probs/Conflict",
            "title": "The request could not be completed due to a conflict with the current state of the target resource.",
            "status": str(409),
        }

    def catch(self, exception: HTTPException, request: Request, response: Response):
        logger.error(exception.status_code)
        logger.error(exception.detail)

        err_message = self.get_error_payload(exception, request.url.path)
        response.status_code = err_message["status"]
        return JSONResponse(status_code=int(err_message["status"]), content=err_message)

    def get_error_payload(self, exception: HTTPException, path: str):
        response = self.exception_templates.get(
            exception.status_code, self.exception_templates[500]
        )

        error_response = {
            "detail": exception.detail,
            "instance": path,
            **response,
        }

        return error_response
