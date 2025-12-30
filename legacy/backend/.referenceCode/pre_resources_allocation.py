from flask import Flask, jsonify, request
from pass_infra.app.utils.logging import LoggerUtils
from pass_infra.app.data.data_access_layer import CustomError
from pass_infra.app.data.resource_manager_queries import (
    get_server_capacity,
    get_used_resources,
)

class ResourceAllocation:
    def validate_input_data(self, data):
        required_fields = ["server_name", "vcpu", "storage", "gpu"]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"Missing fields: {', '.join(missing)}")

    def get_available_resources(self, server_name):

        server_details = get_server_capacity(server_name)
        if not server_details:
            raise CustomError("Server not found", code=404)
        server_id = server_details.get("server_id")

        used = get_used_resources(server_id)

        return {
            "vcpu": server_details["vcpus"] - used["used_vcpu"],
            "storage": server_details["storage"] - used["used_storage"],
            "gpu": server_details["gpu"] - used["used_gpu"],
        }

    def execute(self,payload):
        is_avail_only = request.args.get("available") == "true"
        payload = request.get_json()

        server_name = payload.get("server_name")
        if not server_name:
            raise CustomError("Server name is required")

        available = self.get_available_resources(server_name)

        if is_avail_only:
            return {
                "message": "Available resources fetched successfully",
                "data": {"available": available},
            }

        # Validate inputs for allocation check
        self.validate_input_data(payload)

        requested = {
            "vcpu": float(payload["vcpu"]),
            "storage": float(payload["storage"]),
            "gpu": float(payload["gpu"]),
        }

        LoggerUtils.debug(f"Requested resources: {requested}")
    
        is_quota_ok = all(float(requested[key]) <= float(available[key]) for key in requested)

        if not is_quota_ok:
            LoggerUtils.error(
            f"Resource allocation failed for server {server_name}. "
            f"Requested: {requested}, Available: {available}"
            )
            raise CustomError(
            f"Insufficient resources: Requested more than available. Available: {available}",
            400,
            )

        LoggerUtils.info(f"Resource allocation possible for server {server_name}. ")
        return {
            "message": "Quota check complete , allocation possible.",
            "data": {
                "available": available,
                "requested": requested,
            },
        }
