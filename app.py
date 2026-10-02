import os, json, asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import httpx
app=FastAPI(title='AI Swarm')
OLLAMA_URL=os.getenv('OLLAMA_URL','http://127.0.0.1:11434'); OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','qwen3:8b')
PAGE='''<!doctype html><html lang="ru"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Swarm</title><style>body{font-family:-apple-system;background:#0b0d10;color:#fff;max-width:760px;margin:auto;padding:24px 16px}textarea{width:100%;height:180px;background:#15171c;color:#fff;border:1px solid #333;border-radius:16px;padding:15px;font-size:17px;box-sizing:border-box}button{width:100%;margin-top:12px;padding:16px;border:0;border-radius:14px;font-size:17px;font-weight:bold}#s{color:#aaa;margin:16px 0}.a{white-space:pre-wrap;background:#15171c;padding:18px;border-radius:16px;line-height:1.5}</style><h1>🧠 AI Swarm</h1><p>ИИ-оркестратор управляет роем агентов.</p><textarea id=p placeholder="Например: Создай бизнес-план..."></textarea><button onclick=run()>Запустить рой</button><div id=s></div><div id=a class=a>Результат появится здесь.</div><script>async function run(){let p=document.getElementById("p").value.trim(),s=document.getElementById("s"),a=document.getElementById("a");if(!p)return;s.textContent="🤖 Рой работает...";try{let r=await fetch("/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt:p})});let x=await r.json();a.textContent=x.answer;s.textContent="✅ Готово"}catch(e){s.textContent="❌ "+e}}</script>'''
class Task(BaseModel): prompt:str
async def llm(prompt):
 async with httpx.AsyncClient(timeout=300) as c:
  r=await c.post(OLLAMA_URL+'/api/generate',json={'model':OLLAMA_MODEL,'prompt':prompt,'stream':False}); r.raise_for_status(); return r.json().get('response','')
@app.get('/',response_class=HTMLResponse)
async def home(): return PAGE
@app.get('/health')
async def health():
 try:
  async with httpx.AsyncClient(timeout=4) as c:
   r=await c.get(OLLAMA_URL+'/api/tags'); return {'ok':r.is_success,'model':OLLAMA_MODEL}
 except Exception as e: return {'ok':False,'error':str(e)}
@app.post('/run')
async def run(t:Task):
 raw=await llm('''You are the AI ORCHESTRATOR. Split the user task into 2-4 independent jobs. Available agents: researcher, coder, analyst. Return ONLY JSON: {"jobs":[{"agent":"researcher|coder|analyst","task":"..."}]}\nUSER TASK:\n'''+t.prompt)
 try: plan=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
 except: plan={'jobs':[{'agent':'analyst','task':t.prompt}]}
 async def work(j): return await llm(f"You are the {j.get('agent','analyst')} agent. Solve this assignment accurately:\n{j.get('task',t.prompt)}")
 results=await asyncio.gather(*[work(j) for j in plan.get('jobs',[])])
 final=await llm(f"You are the final reviewer of an AI swarm.\nOriginal task:\n{t.prompt}\nAgent results:\n{json.dumps(results,ensure_ascii=False)}\nSynthesize the best final answer. Correct errors and contradictions.")
 return {'answer':final,'jobs':plan.get('jobs',[])}
if __name__=='__main__':
 import uvicorn; uvicorn.run(app,host='0.0.0.0',port=int(os.getenv('PORT','8000')))
