from pydantic import BaseModel, Field
from typing import Any


class ErrorDetail(BaseModel):
    detail: Any = Field(..., examples=["Resource not found"])


# Predefined response dicts — spread into route decorators' responses= arg
HTTP_400 = {400: {"model": ErrorDetail, "description": "Bad request — validation or constraint error."}}
HTTP_401 = {401: {"model": ErrorDetail, "description": "Not authenticated or token expired."}}
HTTP_403 = {403: {"model": ErrorDetail, "description": "Authenticated but not authorized for this resource."}}
HTTP_404 = {404: {"model": ErrorDetail, "description": "Requested resource not found."}}
HTTP_409 = {409: {"model": ErrorDetail, "description": "Conflict — e.g., duplicate member, email taken."}}
HTTP_422 = {422: {"model": ErrorDetail, "description": "Unprocessable entity — request body or query param validation failed."}}
HTTP_502 = {502: {"model": ErrorDetail, "description": "Upstream service unavailable (LLM, Maps, payment provider)."}}
