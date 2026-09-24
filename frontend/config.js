// "static": le os JSONs de ./data (gerados por database/export_static.py) - nao precisa de servidor.
// "api": chama a API FastAPI (API_BASE vazio = mesma origem, como no docker-compose local).
window.DATA_MODE = "static";
window.API_BASE = "";
