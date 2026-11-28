class Client:
    def __init__(self, config: dict):
        self.base_url = config["base_url"]
        self.timeout = config["timeout"]

    def request_args(self, path: str) -> dict:
        return {"url": f"{self.base_url}/{path.lstrip('/')}", "timeout": self.timeout}
