from dotenv import load_dotenv
load_dotenv()

from agent.graph import app

png = app.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png)

print("저장 완료: graph.png")
