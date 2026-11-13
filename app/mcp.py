from fastmcp import FastMCP
from starlette.responses import PlainTextResponse

mcp = FastMCP("Simplifica Conquista")


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return PlainTextResponse("ok")


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
